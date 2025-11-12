import os
import shutil
from typing import Union
from rtnls_oct.segmentations import ContoursData, PixelWiseSegmentation
from rtnls_oct.analysis.pca import PCAThicknessMap
from rtnls_oct.oct3d import OCT3DVolume
from rtnls_oct.analysis import quality_metrics
from rtnls_oct import utils, plotting
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image

class RetinalThicknessReportData:
    """Base class for thickness report data."""
    def __init__(self, pcamap: PCAThicknessMap = None, vmin: float = 0, vmax: float = None):
        self.pcamap = pcamap
        self.vmin = vmin
        self.vmax = vmax
        # These will be set during processing
        self.thickness = None
        self.fluctuation_map = None
        self.etdrs_grid = None
        self.pca_error = None
        self.pca_reconstruction = None
        self.pca_map_fields = None
    
    def calculate_thickness(self, segmentation, resolution_mm):
        """
        Calculate thickness map. Must be implemented by subclasses.
        
        Args:
            segmentation: The segmentation object
            resolution_mm: Resolution tuple (depth, height, width) in mm
        
        Returns:
            Thickness map in pixels
        """
        raise NotImplementedError("Subclasses must implement calculate_thickness")
    
    def process(self, segmentation, resolution_mm, fovea_y, fovea_x, laterality):
        """
        Process the thickness map: calculate thickness, fluctuation, ETDRS grid, and PCA.
        
        Args:
            segmentation: The segmentation object
            resolution_mm: Resolution tuple (depth, height, width) in mm
            fovea_y: Fovea y coordinate
            fovea_x: Fovea x coordinate
            laterality: Eye laterality ('L' or 'R')
        """
        from rtnls_oct.analysis import quality_metrics
        from rtnls_oct import utils
        
        # Calculate thickness
        thickness_pixels = self.calculate_thickness(segmentation, resolution_mm)
        
        # Convert to mm and ensure non-negative
        self.thickness = thickness_pixels * resolution_mm[1]  # Convert to mm
        self.thickness = np.where(self.thickness < 0, 0, self.thickness)
        
        # Calculate fluctuation map
        self.fluctuation_map = quality_metrics.get_thickness_fluctuation_map(self.thickness)
        
        # Generate ETDRS grid
        self.etdrs_grid = utils.get_etdrs_grid_on_image(
            image_shape=self.thickness.shape,
            resolution_mm=(resolution_mm[0], resolution_mm[2]),
            center=(fovea_y, fovea_x),
            laterality=laterality
        )
        
        # PCA analysis if provided
        if self.pcamap is not None:
            self.pca_error, self.pca_reconstruction = self.pcamap.get_reconstruction_error(
                self.thickness, laterality, (resolution_mm[0], resolution_mm[2]), (fovea_y, fovea_x))
            self.pca_map_fields = self.pcamap.interpolation_map.get_masks()
        else:
            self.pca_error = None
            self.pca_map_fields = None


class ContoursThicknessReportData(RetinalThicknessReportData):
    """Thickness report data for ContoursData segmentation."""
    def __init__(self, boundary_top: str, boundary_bottom: str, pcamap: PCAThicknessMap = None, 
                 vmin: float = 0, vmax: float = None):
        super().__init__(pcamap, vmin, vmax)
        self.boundary_top = boundary_top
        self.boundary_bottom = boundary_bottom
    
    def calculate_thickness(self, segmentation, resolution_mm):
        """
        Calculate thickness using boundary subtraction.
        
        Args:
            segmentation: ContoursData object
            resolution_mm: Resolution tuple (unused, kept for interface consistency)
        
        Returns:
            Thickness map in pixels
        """
        thickness_pixels = segmentation.get_thickness_map(self.boundary_top, self.boundary_bottom)
        # Convert to numpy array if masked array
        if isinstance(thickness_pixels, np.ma.MaskedArray):
            thickness_pixels = thickness_pixels.filled(0)
        return thickness_pixels


class PixelWiseThicknessReportData(RetinalThicknessReportData):
    """Thickness report data for PixelWiseSegmentation."""
    def __init__(self, layer_names: list, layer_mapping: dict = None, 
                 pcamap: PCAThicknessMap = None, vmin: float = 0, vmax: float = None):
        super().__init__(pcamap, vmin, vmax)
        self.layer_names = layer_names
        self.layer_mapping = layer_mapping
    
    def calculate_thickness(self, segmentation, resolution_mm):
        """
        Calculate thickness by summing pixels along depth axis.
        
        Args:
            segmentation: PixelWiseSegmentation object
            resolution_mm: Resolution tuple (unused, kept for interface consistency)
        
        Returns:
            Thickness map in pixels
        """
        # Apply layer mapping if provided
        layer_names = self.layer_names.copy()
        if self.layer_mapping:
            # Reverse mapping: standard name -> original name
            reverse_mapping = {v: k for k, v in self.layer_mapping.items() if v is not None}
            # Map layer names to original names
            mapped_layer_names = []
            for layer_name in layer_names:
                if layer_name in reverse_mapping:
                    mapped_layer_names.append(reverse_mapping[layer_name])
                else:
                    mapped_layer_names.append(layer_name)
            layer_names = mapped_layer_names
        
        # Use get_thickness_map() method
        thickness = segmentation.get_thickness_map(layer_names)
        
        # Convert masked array to regular array (fill masked values with 0)
        if isinstance(thickness, np.ma.MaskedArray):
            thickness = thickness.filled(0)
        
        return thickness


class RetinalThicknessReport:
    def __init__(
        self,
        oct_volume: OCT3DVolume,
        segmentation: Union[ContoursData, PixelWiseSegmentation],
        laterality: str,
        fovea_x: float,
        fovea_y: float,
        layer_mapping: dict = None,
        ilm_proxy: str = None
    ):
        """
        Initialize RetinalThicknessReport.
        
        Args:
            oct_volume: OCT3DVolume object
            segmentation: Either ContoursData or PixelWiseSegmentation
            laterality: Eye laterality ('L' or 'R')
            fovea_x: Fovea x coordinate in pixels
            fovea_y: Fovea y coordinate in pixels
            layer_mapping: Optional dictionary for mapping layer names when converting
                PixelWiseSegmentation to ContoursData. Only used if segmentation is PixelWiseSegmentation.
            ilm_proxy: Optional layer name to use as ILM proxy when converting PixelWiseSegmentation.
                Only used if segmentation is PixelWiseSegmentation and ILM is not present.
        """
        self.oct_volume = oct_volume
        self.laterality = laterality
        self.fovea_x = fovea_x
        self.fovea_y = fovea_y
        self.resolution_mm = oct_volume.res_depth_mm, oct_volume.res_height_mm, oct_volume.res_width_mm
        self.thickness_maps = {}
        
        # Store segmentation natively without conversion
        if isinstance(segmentation, PixelWiseSegmentation):
            self._original_segmentation_type = 'PixelWiseSegmentation'
            self.segmentation = segmentation
            # Store layer mapping for reference
            self._layer_mapping = layer_mapping
        elif isinstance(segmentation, ContoursData):
            self._original_segmentation_type = 'ContoursData'
            self.segmentation = segmentation
            self._layer_mapping = None
        else:
            raise TypeError(
                f"segmentation must be ContoursData or PixelWiseSegmentation, "
                f"got {type(segmentation)}"
            )

    def add_thickness_map(
        self,
        name: str,
        boundary_bottom: str = None,
        boundary_top: str = None,
        layer_names: list = None,
        pcamap: PCAThicknessMap = None,
        vmin: float = 0,
        vmax: float = None
    ):
        """
        Add a thickness map to analyze.
        
        For ContoursData segmentation:
            - Use boundary_top and boundary_bottom (layer names)
        
        For PixelWiseSegmentation:
            - Use layer_names (list of layer names to sum for thickness)
            - Thickness is calculated by summing pixels along depth axis
        
        Args:
            name: Name of the thickness map
            boundary_top: Top boundary name (for ContoursData)
            boundary_bottom: Bottom boundary name (for ContoursData)
            layer_names: List of layer names to include (for PixelWiseSegmentation)
            pcamap: Optional PCA thickness map for quality assessment
            vmin: Minimum value for visualization
            vmax: Maximum value for visualization
        """
        if isinstance(self.segmentation, ContoursData):
            if boundary_top is None or boundary_bottom is None:
                raise ValueError("For ContoursData, both boundary_top and boundary_bottom must be provided")
            self.thickness_maps[name] = ContoursThicknessReportData(
                boundary_top=boundary_top,
                boundary_bottom=boundary_bottom,
                pcamap=pcamap,
                vmin=vmin,
                vmax=vmax
            )
        elif isinstance(self.segmentation, PixelWiseSegmentation):
            if layer_names is None or len(layer_names) == 0:
                raise ValueError("For PixelWiseSegmentation, layer_names must be provided")
            self.thickness_maps[name] = PixelWiseThicknessReportData(
                layer_names=layer_names,
                layer_mapping=self._layer_mapping,
                pcamap=pcamap,
                vmin=vmin,
                vmax=vmax
            )

    def process_thickness_map(self, name: str):
        """Process a thickness map by delegating to the appropriate data class."""
        mapdata = self.thickness_maps[name]
        mapdata.process(
            segmentation=self.segmentation,
            resolution_mm=self.resolution_mm,
            fovea_y=self.fovea_y,
            fovea_x=self.fovea_x,
            laterality=self.laterality
        )

    def get_result_dict(self):
        result_dict = {}
        for mapname, mapdata in self.thickness_maps.items():
            for field, mask in mapdata.etdrs_grid.items():
                try:
                    result_dict[f'{mapname}_{field}_mean'] = np.mean(mapdata.thickness[mask])
                    result_dict[f'{mapname}_{field}_min'] = np.min(mapdata.thickness[mask])
                    result_dict[f'{mapname}_{field}_max'] = np.max(mapdata.thickness[mask])
                    result_dict[f'{mapname}_{field}_fluctuation'] = np.mean(mapdata.fluctuation_map[mask])
                except:
                    result_dict[f'{mapname}_{field}_mean'] = None
            if mapdata.pca_error is not None:
                for field, mask in mapdata.pca_map_fields.items():
                    result_dict[f'{mapname}_{field}_pca_error'] = np.mean(mapdata.pca_error[mask])
        return result_dict
    
    def plot_results(self, mapname: str):
        mapdata = self.thickness_maps[mapname]
        fig, axes = plt.subplots(1, 2, figsize=(12,3))
        vmax_thickness = np.quantile(mapdata.thickness, 0.95) if mapdata.vmax is None else mapdata.vmax

        cb = axes[0].imshow(mapdata.thickness, cmap='viridis', vmin=0, vmax=vmax_thickness, aspect='auto')
        cbar = fig.colorbar(cb, ax=axes[0])
        cbar.set_label('[mm]', rotation=270)
        cb = axes[1].imshow(mapdata.fluctuation_map, cmap='viridis', vmin=0, vmax=0.3*vmax_thickness, aspect='auto')
        cbar = fig.colorbar(cb, ax=axes[1])
        cbar.set_label('[mm]', rotation=270)
        plotting.plot_grid_masks(mapdata.etdrs_grid, ax=axes[0])
        plotting.plot_grid_masks(mapdata.etdrs_grid, ax=axes[1])
        axes[0].set_title('Thickness')
        axes[1].set_title('Fluctuation')
        for ax in axes:
            ax.axis('off')
        return fig, axes
    
    def plot_pca_error(self, mapname: str, enface_image=None, bscan_image=None):
        mapdata = self.thickness_maps[mapname]
        center = (self.fovea_y, self.fovea_x)
        resolution_mm = (self.resolution_mm[0], self.resolution_mm[2])
        fig, axes = plt.subplots(1, 2, figsize=(12, 3))
        if enface_image is not None:
            axes[1].imshow(enface_image, cmap='gray', aspect='auto')
            axes[0].imshow(enface_image, cmap='gray', aspect='auto')
        else:
            self.oct_volume.plot_enface_image(ax=axes[1])
            self.oct_volume.plot_enface_image(ax=axes[0])
        mapdata.pcamap.interpolation_map.plot_with_values(mapdata.pca_error, ax=axes[1], center=center, resolution_mm=resolution_mm, laterality=self.laterality, s=4)
        # axes[1].scatter(mapdata.pcamap.interpolation_map.x_locs/resolution_mm[1] + center[1], mapdata.pcamap.interpolation_map.y_locs/resolution_mm[0] + center[0], s=4, c=mapdata.pca_error)
        axes[1].set_title('PCA Error')
        mapdata.pcamap.interpolation_map.plot_with_values(mapdata.pca_reconstruction, ax=axes[0], center=center, resolution_mm=resolution_mm, laterality=self.laterality, s=4)
        axes[0].set_title('PCA Reconstruction')
        for ax in axes:
            ax.axis('off')
        return fig, axes
    
    def write_report_html(self, file_path: str, id=None, enface=None, bscan=None):
        os.makedirs(f'{file_path}', exist_ok=True)
        html = '<html><body>'
        html += f'<h1>OCT Report {id}</h1><br>'
        fig, axes = plt.subplots(1, 2, figsize=(12, 3))
        central_bscan_index = self.oct_volume.n_bscans//2
        if bscan is not None:
            bscan_image = np.array(Image.open(bscan))
            axes[0].imshow(bscan_image, cmap='gray', aspect='auto')
        else:
            self.oct_volume.plot_bscan(central_bscan_index, ax=axes[0])
        # plot contours or segmentation
        if isinstance(self.segmentation, ContoursData):
            contours = self.segmentation.get_contours_on_bscan(central_bscan_index)
            for name, contour in contours.items():
                height = self.oct_volume.image.shape[1] - contour
                height = np.where(height < 0, 0, height)
                height = np.where(height > self.oct_volume.image.shape[1], self.oct_volume.image.shape[1], height)
                axes[0].plot(height, label=name)
        elif isinstance(self.segmentation, PixelWiseSegmentation):
            # Plot pixel-wise segmentation overlay
            self.segmentation.plot_bscan(central_bscan_index, ax=axes[0])
        if enface is not None:
            enface_image = np.array(Image.open(enface))
            axes[1].imshow(enface_image, cmap='gray', aspect='auto')
        else:
            self.oct_volume.plot_enface_image(ax=axes[1])
        axes[0].set_title('Central Bscan')
        axes[1].set_title('Enface')
        for ax in axes:
            ax.axis('off')
        fig.savefig(f'{file_path}/oct_image.png', bbox_inches='tight')
        plt.close(fig)
        html += f'<img src="oct_image.png" alt="OCT Enface" />'
        for mapname, mapdata in self.thickness_maps.items():
            fig, axes = self.plot_results(mapname)
            fig.savefig(f'{file_path}/{mapname}.png', bbox_inches='tight')
            plt.close(fig)
            html += f'<h2>{mapname}</h2><br>'
            html += f'<img src="{mapname}.png" alt="{mapname}" />'
            if mapdata.pca_error is not None:
                fig, axes = self.plot_pca_error(mapname, enface_image, bscan_image)
                fig.savefig(f'{file_path}/{mapname}_pca_error.png', bbox_inches='tight')
                plt.close(fig)
                html += f'<br><img src="{mapname}_pca_error.png" alt="{mapname}_pca_error" />'
        html += '</body></html>'
        with open(f'{file_path}/report.html', 'w') as f:
            f.write(html)
        

    def process(self):
        for name in self.thickness_maps.keys():
            self.process_thickness_map(name)
    
    @classmethod
    def from_pixelwise(
        cls,
        oct_volume: OCT3DVolume,
        pixel_seg: PixelWiseSegmentation,
        laterality: str,
        fovea_x: float = None,
        fovea_y: float = None,
        layer_mapping: dict = None,
        auto_find_fovea: bool = True
    ):
        """
        Create RetinalThicknessReport from PixelWiseSegmentation.
        
        This is a convenience method that uses PixelWiseSegmentation natively (without conversion)
        and optionally finds the fovea.
        
        Args:
            oct_volume: OCT3DVolume object
            pixel_seg: PixelWiseSegmentation object
            laterality: Eye laterality ('L' or 'R')
            fovea_x: Optional fovea x coordinate in pixels. If None and auto_find_fovea=True, will be detected.
            fovea_y: Optional fovea y coordinate in pixels. If None and auto_find_fovea=True, will be detected.
            layer_mapping: Optional dictionary for mapping layer names (for reference, not conversion)
            auto_find_fovea: If True and fovea coordinates are not provided, automatically detect fovea
        
        Returns:
            RetinalThicknessReport: Initialized report object
        """
        # Find fovea if needed
        if (fovea_x is None or fovea_y is None) and auto_find_fovea:
            # Get labels to find topmost layer for fovea detection
            if hasattr(pixel_seg, 'labels') and isinstance(pixel_seg.LABELS, dict):
                labels_dict = pixel_seg.LABELS
            else:
                labels_dict = {name: val[0] if isinstance(val, list) else val 
                                for name, val in pixel_seg.LABELS.items()}
            
            # Select all layers except 'background' and 'Choroid' to extract thickness map
            ignore_layers = {'background', 'BG', 'choroid', 'Choroid'}
            # Find all valid layer names
            valid_layers = [name for name in labels_dict.keys() if name not in ignore_layers and name.lower() not in ignore_layers]
            print("Using layers for fovea detection: ", valid_layers)
            if not valid_layers:
                raise ValueError("No layers found for fovea detection after filtering background and Choroid.")
            # Sum all layers into thickness map 
            thickness_map = pixel_seg.get_thickness_map(labels=valid_layers)
            fovea_y, fovea_x = utils.find_fovea(
                height_map=thickness_map,
                res_depth_mm=oct_volume.res_depth_mm,
                res_width_mm=oct_volume.res_width_mm
            )
            print(f"Fovea found at: {fovea_y}, {fovea_x}")
    
        if fovea_x is None or fovea_y is None:
            raise ValueError("fovea_x and fovea_y must be provided or auto_find_fovea must be True")
        
        return cls(
            oct_volume=oct_volume,
            segmentation=pixel_seg,  # Use natively, no conversion
            laterality=laterality,
            fovea_x=fovea_x,
            fovea_y=fovea_y,
            layer_mapping=layer_mapping
        )

    