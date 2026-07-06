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
- **eyened_orm Integration**: Load OCT volumes and segmentations from the EyeNED database (optional)

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

### Optional dependencies

```bash
# eyened_orm database integration
pip install rtnls-oct[eyened]

# Celery worker (see worker/README.md)
pip install rtnls-oct[worker]
```

Requires Python 3.10+.

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

### Working with Contour Segmentations

```python
from rtnls_oct import ContoursData

# Load segmentation from NPZ file
segmentation = ContoursData.from_npz("path/to/segmentation.npz")

# Calculate thickness map between boundaries
thickness_map = segmentation.get_thickness_map("ILM", "RPE")
```

### Generating a Thickness Report (ContoursData)

```python
from rtnls_oct import RetinalThicknessReport, utils

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

# Add thickness maps using boundary names
report.add_thickness_map("RNFL", boundary_bottom="RNFL", boundary_top="ILM")
report.add_thickness_map("Total", boundary_bottom="RPE", boundary_top="ILM")

# Process and generate results
report.process()
results = report.get_result_dict()

# Generate HTML report
report.write_report_html("output/report", id="patient_001")
```

### Generating a Thickness Report (PixelWiseSegmentation)

For pixel-wise segmentations (e.g. from `eyened_orm`), use `from_pixelwise()` and `layer_names`:

```python
from rtnls_oct import RetinalThicknessReport

report = RetinalThicknessReport.from_pixelwise(
    oct_volume=oct_volume,
    pixel_seg=segmentation,
    laterality=oct_volume.laterality,
    auto_find_fovea=True,
)

report.add_thickness_map(
    name="RNFL",
    layer_names=["Retinal Nerve Fiber Layer (RNFL)"],
    vmin=0,
    vmax=0.2,
)
report.add_thickness_map(
    name="Total",
    layer_names=[
        "Retinal Nerve Fiber Layer (RNFL)",
        "Ganglion cell layer (GCL)",
        "Inner plexiform layer (IPL)",
        # ... additional layers ...
        "Retinal pigment epithelium (RPE)",
    ],
    vmin=0,
    vmax=0.5,
)

report.process()
results = report.get_result_dict()
report.write_report_html("output/report", id="patient_001")
```

See [rtnls_oct/eyened/README.md](rtnls_oct/eyened/README.md) for loading data from `eyened_orm`.

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
    direction_bscan='Left' or 'Right',  # default: 'Right'
    axial_direction='Up' or 'Down',      # default: 'Down'
)

# Methods and properties
oct_volume.plot_enface_image(ax=ax)
oct_volume.plot_bscan(index, ax=ax)
oct_volume.plot_central_bscan(ax=ax)
oct_volume.enface_projection()
oct_volume.resolution_mm  # (res_depth_mm, res_height_mm, res_width_mm)
```

### OCTVolumeWithEnface

Links an OCT volume to an enface image with registration coordinates for overlay visualization.

```python
from rtnls_oct import OCTVolumeWithEnface

volume = OCTVolumeWithEnface.from_dicom_files("oct.dcm", "enface.dcm")
volume.plot_oct_on_enface()
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

### PixelWiseSegmentation

Manages pixel-wise label segmentations. Layer names are stored in `LABELS` (mapping name to label value).

```python
from rtnls_oct import PixelWiseSegmentation

# Thickness by summing pixels along depth for named layers
thickness_map = segmentation.get_thickness_map(["RNFL", "GCL"])

# Visualize a B-scan
segmentation.plot_bscan(bscan_index=10)
segmentation.get_bscan(bscan_index=10)
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

Generates comprehensive thickness analysis reports with ETDRS grid measurements. Supports both `ContoursData` and `PixelWiseSegmentation`.

**Contour-based segmentation:**

```python
report = RetinalThicknessReport(
    oct_volume=oct_volume,
    segmentation=contours_segmentation,
    laterality='R',
    fovea_x=fovea_x,
    fovea_y=fovea_y,
)

report.add_thickness_map(
    name="RNFL",
    boundary_bottom="RNFL",
    boundary_top="ILM",
    pcamap=pca_model,  # Optional
    vmin=0,
    vmax=0.2,
)
```

**Pixel-wise segmentation:**

```python
report = RetinalThicknessReport.from_pixelwise(
    oct_volume=oct_volume,
    pixel_seg=pixel_segmentation,
    laterality='R',
    auto_find_fovea=True,
)

report.add_thickness_map(
    name="RNFL",
    layer_names=["Retinal Nerve Fiber Layer (RNFL)"],
    vmin=0,
    vmax=0.2,
)
```

**Common workflow:**

```python
report.process()
results = report.get_result_dict()
# Returns dict with keys like: 'RNFL_C0_mean', 'RNFL_S1_mean', etc.

fig, axes = report.plot_results("RNFL")
report.write_report_html("output/path", id="patient_id")
```

## Utilities

### ETDRS Grid

Generate ETDRS grid masks for thickness analysis:

```python
from rtnls_oct import utils

grid = utils.get_etdrs_grid_on_image(
    image_shape=(100, 512),
    resolution_mm=(0.047, 0.012),
    laterality='R',
    direction_bscan="Right",
    axial_direction="Down",
    center=(fovea_y, fovea_x),  # Optional
)

# Grid contains masks for: 'C0', 'S1', 'I1', 'N1', 'T1', 'S2', 'I2', 'N2', 'T2',
# 'S_hemifield', 'I_hemifield', 'GRID'
```

### Fovea Localization

Automatically detect fovea location:

```python
from rtnls_oct import utils

fovea_y, fovea_x = utils.find_fovea(
    height_map=segmentation.get_height_map("ILM"),
    res_depth_mm=0.047,
    res_width_mm=0.012,
    exclude_mask=None,  # Optional mask to exclude regions
)
```

## Analysis Tools

### PCA Analysis

Perform Principal Component Analysis on thickness maps:

```python
from rtnls_oct.analysis import PCAThicknessMap, ETDRSInterpolationMap

# ETDRS-shaped sampling grid (3 mm radius)
interp_map = ETDRSInterpolationMap(points_per_mm=10, reference_laterality='R')

pca_model = PCAThicknessMap(n_components=5, interpolation_map=interp_map)
pca_model.fit(training_thickness_maps)

pca_features = pca_model.transform_from_map(
    thickness_map,
    laterality='R',
    resolution_mm=(0.047, 0.012),
    center=(fovea_y, fovea_x),
)

error_map, reconstruction = pca_model.get_reconstruction_error(
    thickness_map,
    laterality='R',
    resolution_mm=(0.047, 0.012),
    center=(fovea_y, fovea_x),
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

plotting.plot_image(bscan_image)
plotting.plot_thickness(thickness_map, alpha=0.5, vmin=0)

# ETDRS grid overlays with optional styling
plotting.plot_grid_masks(
    etdrs_grid,
    ax=ax,
    line_color="r",
    show_labels=True,
    linewidths=0.5,
)
```

## Conventions

Coordinates and resolutions are in the order of `[z, y, x]` / `[depth, height, width]`, where:
- `z / depth` is the slow axis, so across the b-scans. Regardless of the real-world direction of the OCT image.
- `y / height` is in the direction of the OCT beam, so in the height of a b-scan.
- `x / width` is the fast axis or the width of the b-scan.

Resolutions are in millimetres unless otherwise stated. Preferably it is stated with the variable by prefixing `_mm`. A size is in pixels unless otherwise stated, e.g. by prefixing with `_mm`.

## Further Reading

- [Loading data from eyened_orm](rtnls_oct/eyened/README.md)
- [Celery worker setup](worker/README.md)
- [Docker deployment](DOCKER.md)

## License

This project is licensed under the GPL-3.0 License.

## Authors

Eyened Team (k.vangarderen@erasmusmc.nl; eyened@erasmusmc.nl)

## References

- [ETDRS Grid](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC1311780/)
