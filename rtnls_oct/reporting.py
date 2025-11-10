import os
import shutil
from rtnls_oct.segmentations import ContoursData
from rtnls_oct.analysis.pca import PCAThicknessMap
from rtnls_oct.oct3d import OCT3DVolume
from rtnls_oct.analysis import quality_metrics
from rtnls_oct import utils, plotting
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image

class RetinalThicknessReportData:
    def __init__(self, boundary_bottom: str, boundary_top: str, pcamap: PCAThicknessMap=None, vmin: float=0, vmax: float=None):
        self.boundary_bottom = boundary_bottom
        self.boundary_top = boundary_top
        self.pcamap = pcamap

        self.vmin = vmin
        self.vmax = vmax
    

class RetinalThicknessReport:
    def __init__(self, oct_volume: OCT3DVolume, segmentation: ContoursData,laterality: str, 
                 fovea_x: float, fovea_y: float):
        self.oct_volume = oct_volume
        self.segmentation = segmentation
        self.laterality = laterality
        self.fovea_x = fovea_x
        self.fovea_y = fovea_y
        self.resolution_mm = oct_volume.res_depth_mm, oct_volume.res_height_mm, oct_volume.res_width_mm
        self.thickness_maps = {}

    def add_thickness_map(self, name: str, boundary_bottom: str, boundary_top: str, pcamap: PCAThicknessMap=None, vmin: float=0, vmax: float=None):
        self.thickness_maps[name] = RetinalThicknessReportData(boundary_bottom, boundary_top, pcamap, vmin, vmax)

    def process_thickness_map(self, name: str):
        mapdata = self.thickness_maps[name]
        mapdata.thickness = self.segmentation.get_thickness_map(mapdata.boundary_top, mapdata.boundary_bottom) * self.resolution_mm[1]
        mapdata.thickness = np.where(mapdata.thickness < 0, 0, mapdata.thickness)
        mapdata.fluctuation_map = quality_metrics.get_thickness_fluctuation_map(mapdata.thickness)
        mapdata.etdrs_grid = utils.get_etdrs_grid_on_image(image_shape=mapdata.thickness.shape, 
                               resolution_mm=(self.resolution_mm[0], self.resolution_mm[2]), 
                               center=(self.fovea_y, self.fovea_x), laterality=self.laterality)
        if mapdata.pcamap is not None:
            mapdata.pca_error, mapdata.pca_reconstruction = mapdata.pcamap.get_reconstruction_error(
                mapdata.thickness, self.laterality, (self.resolution_mm[0], self.resolution_mm[2]), (self.fovea_y, self.fovea_x))
            mapdata.pca_map_fields = mapdata.pcamap.interpolation_map.get_masks()
        else:
            mapdata.pca_error = None
            mapdata.pca_map_fields = None

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
        if enface is not None:
            enface_image = np.array(Image.open(enface))
        if bscan is not None:
            bscan_image = np.array(Image.open(bscan))
        fig, axes = plt.subplots(1, 2, figsize=(12, 3))
        central_bscan_index = self.oct_volume.n_bscans//2
        if bscan_image is not None:
            axes[0].imshow(bscan_image, cmap='gray', aspect='auto')
        else:
            self.oct_volume.plot_bscan(central_bscan_index, ax=axes[0])
        # plot contours
        contours = self.segmentation.get_contours_on_bscan(central_bscan_index)
        for name, contour in contours.items():
            height = self.oct_volume.image.shape[1] - contour
            height = np.where(height < 0, 0, height)
            height = np.where(height > self.oct_volume.image.shape[1], self.oct_volume.image.shape[1], height)
            axes[0].plot(height, label=name)
        if enface_image is not None:
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

    