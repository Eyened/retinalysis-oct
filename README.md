# Retinalysis-OCT

A Python package for the analysis of Optical Coherence Tomography (OCT) volumes with layer segmentations. This package provides tools for processing 3D OCT data, analyzing retinal thickness maps, generating ETDRS grid measurements, and creating comprehensive reports.

## Features

- **3D OCT Volume Processing**: Load and process OCT volumes from DICOM files
- **Segmentation Support**: Work with contour-based and pixel-wise segmentations
- **Thickness Analysis**: Calculate retinal thickness maps
- **ETDRS Grid Analysis**: Generate Early Treatment Diabetic Retinopathy Study (ETDRS) grid measurements
- **Fovea Localization**: Automatically detect fovea location from layer data
- **PCA Analysis**: Principal Component Analysis for thickness map analysis and quality assessment
- **Quality Metrics**: Calculate thickness fluctuation and other quality indicators
- **Report Generation**: Create HTML reports with visualizations
- **Visualization Tools**: Plot B-scans, enface images, thickness maps, and grids

## Installation

```bash
pip install rtnls-oct
```

Or install from source:

```bash
git clone https://github.com/eyened/retinalysis-oct
cd retinalysis-oct
pip install -e .
```

## Quick Start

### Loading an OCT Volume

```python
from rtnls_oct import OCT3DVolume

# Load from DICOM
oct_volume = OCT3DVolume.from_dicom("path/to/oct.dcm")

# Or create manually
import numpy as np
image = np.random.rand(100, 512, 512)  # (n_bscans, height, width)
oct_volume = OCT3DVolume(
    image=image,
    res_width_mm=0.012,
    res_height_mm=0.003,
    res_depth_mm=0.047,
    laterality='R'
)
```

### Working with Segmentations

```python
from rtnls_oct import ContoursData

# Load segmentation from NPZ file
segmentation = ContoursData.from_npz("path/to/segmentation.npz")

# Calculate thickness map
thickness_map = segmentation.get_thickness_map("ILM", "RPE")
```

### Generating a Thickness Report

```python
from rtnls_oct import RetinalThicknessReport
from rtnls_oct import utils

# Find fovea location
fovea_y, fovea_x = utils.find_fovea(
    height_map=segmentation.get_height_map("ILM"),
    res_depth_mm=oct_volume.res_depth_mm,
    res_width_mm=oct_volume.res_width_mm
)

# Create report
report = RetinalThicknessReport(
    oct_volume=oct_volume,
    segmentation=segmentation,
    laterality='R',
    fovea_x=fovea_x,
    fovea_y=fovea_y
)

# Add thickness maps
report.add_thickness_map("RNFL", boundary_bottom="RNFL", boundary_top="ILM")
report.add_thickness_map("Total", boundary_bottom="RPE", boundary_top="ILM")

# Process and generate results
report.process()
results = report.get_result_dict()

# Generate HTML report
report.write_report_html("output/report", id="patient_001")
```

## Core Components

### OCT3DVolume

Represents a 3D OCT volume with metadata.

```python
oct_volume = OCT3DVolume(
    image=np.ndarray,  # Shape: (n_bscans, height, width)
    res_width_mm=float,
    res_height_mm=float,
    res_depth_mm=float,
    laterality='L' or 'R',
    orientation='Horizontal' or 'Vertical',
    direction_bscan='Left' or 'Right',
    axial_direction='Up' or 'Down'
)

# Methods
oct_volume.plot_enface_image()  # Plot enface projection
oct_volume.plot_bscan(index)    # Plot specific B-scan
oct_volume.enface_projection()  # Get enface projection array
```

### ContoursData

Manages contour-based segmentations (height maps).

```python
segmentation = ContoursData(width=512, n_bscans=100)

# Add surfaces
segmentation.add_surface("ILM", height_map_array)
segmentation.add_surface("RPE", height_map_array)

# Get thickness between boundaries
thickness = segmentation.get_thickness_map("ILM", "RPE")

# Get contours for specific B-scan
contours = segmentation.get_contours_on_bscan(bscan_index=50)
```

### OCTBScan

Represents a single B-scan with optional circular scan support.

```python
from rtnls_oct import OCTBScan, OCTBScanCircular

# Linear B-scan
bscan = OCTBScan(
    image=np.ndarray,  # Shape: (height, width)
    res_width_mm=0.012,
    res_height_mm=0.003,
    laterality='R'
)

# Circular B-scan
circular_bscan = OCTBScanCircular(
    image=np.ndarray,
    res_width_mm=0.012,
    res_height_mm=0.003,
    start_angle=0.0,
    laterality='R'
)

# Extract thickness in TSNIT sectors
thickness_results = circular_bscan.extract_thickness_tsnit("ILM", "RPE")
```

### RetinalThicknessReport

Generates comprehensive thickness analysis reports with ETDRS grid measurements.

```python
report = RetinalThicknessReport(
    oct_volume=OCT3DVolume,
    segmentation=ContoursData,
    laterality='R',
    fovea_x=float,
    fovea_y=float
)

# Add thickness maps to analyze
report.add_thickness_map(
    name="RNFL",
    boundary_bottom="RNFL",
    boundary_top="ILM",
    pcamap=PCAThicknessMap,  # Optional
    vmin=0,
    vmax=500
)

# Process all maps
report.process()

# Get quantitative results
results = report.get_result_dict()
# Returns dict with keys like: 'RNFL_C0_mean', 'RNFL_S1_mean', etc.

# Visualize
fig, axes = report.plot_results("RNFL")

# Generate HTML report
report.write_report_html("output/path", id="patient_id")
```

## Utilities

### ETDRS Grid

Generate ETDRS grid masks for thickness analysis:

```python
from rtnls_oct import utils

# Get ETDRS grid on image
grid = utils.get_etdrs_grid_on_image(
    image_shape=(100, 512),
    resolution_mm=(0.047, 0.012),
    laterality='R',
    direction_bscan="Right",
    axial_direction="Down",
    center=(fovea_y, fovea_x)  # Optional
)

# Grid contains masks for: 'C0', 'S1', 'I1', 'N1', 'T1', 'S2', 'I2', 'N2', 'T2', 'GRID'
```

### Fovea Localization

Automatically detect fovea location:

```python
from rtnls_oct import utils

fovea_y, fovea_x = utils.find_fovea(
    height_map=segmentation.get_height_map("ILM"),
    res_depth_mm=0.047,
    res_width_mm=0.012,
    exclude_mask=None  # Optional mask to exclude regions
)
```

## Analysis Tools

### PCA Analysis

Perform Principal Component Analysis on thickness maps:

```python
from rtnls_oct.analysis import PCAThicknessMap
from rtnls_oct.analysis.interpolation import InterpolationMap

# Create interpolation map
interp_map = InterpolationMap(...)

# Create PCA model
pca_model = PCAThicknessMap(n_components=5, interpolation_map=interp_map)

# Fit on training data
pca_model.fit(training_thickness_maps)

# Transform new data
pca_features = pca_model.transform_from_map(
    thickness_map,
    laterality='R',
    resolution_mm=(0.047, 0.012),
    center=(fovea_y, fovea_x)
)

# Get reconstruction error
error_map, reconstruction = pca_model.get_reconstruction_error(
    thickness_map,
    laterality='R',
    resolution_mm=(0.047, 0.012),
    center=(fovea_y, fovea_x)
)
```

### Quality Metrics

Calculate thickness fluctuation:

```python
from rtnls_oct.analysis import quality_metrics

fluctuation_map = quality_metrics.get_thickness_fluctuation_map(thickness_map)
```

## Visualization

```python
from rtnls_oct import plotting

# Plot B-scan
plotting.plot_image(bscan_image)

# Plot thickness map
plotting.plot_thickness(thickness_map, alpha=0.5, vmin=0)

# Plot ETDRS grid masks
plotting.plot_grid_masks(etdrs_grid, ax=ax)
```

## Conventions

Coordinates and resolutions are in the order of `[z, y, x]` / `[depth, height, width]`, where:
- `z / depth` is the slow axis, so across the b-scans. Regardless of the real-world direction of the OCT image.
- `y / height` is in the direction of the OCT beam, so in the height of a b-scan. 
- `x / width` is the fast axis or the width of the b-scan.

Resolutions are in millimetres unless otherwise stated. Preferably it is stated with the variable by prefixing `_mm`. A size is in pixels unless otherwise stated, e.g. by prefixing with `_mm`.

## License

This project is licensed under the GPL-3.0 License.

## Authors

Eyened Team (k.vangarderen@erasmusmc.nl; eyened@erasmusmc.nl)

## References

- [ETDRS Grid](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC1311780/)

