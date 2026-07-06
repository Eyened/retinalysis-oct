# Loading OCT Data from eyened_orm

This module provides utilities for loading 3D OCT volumes and layer segmentations from the `eyened_orm` database into Retinalysis-OCT data structures.

## Overview

The `rtnls_oct.eyened.dataloading` module bridges the gap between the `eyened_orm` database ORM and the Retinalysis-OCT analysis tools. It converts `ImageInstance` and `Segmentation` records into `OCT3DVolume` and `PixelWiseSegmentation` objects that can be used with the rest of the Retinalysis-OCT package.

Install with:

```bash
pip install rtnls-oct[eyened]
```

## Prerequisites

- `eyened_orm` package installed and configured
- Database connection set up
- Access to OCT `ImageInstance` and `Segmentation` records

## Basic Usage

### 1. Setting Up Database Connection

```python
from eyened_orm import Database

database = Database()
```

### 2. Querying OCT Images and Segmentations

```python
from eyened_orm import ImageInstance, Modality, ETDRSField, ModelSegmentation, Feature, Scan, SegmentationModel

with database.get_session() as session:
    query = session.query(ImageInstance, ModelSegmentation)\
        .filter(ImageInstance.Modality == Modality.OCT)\
        .filter(ImageInstance.ETDRSField == ETDRSField.F2)\
        .join(Scan).filter(Scan.ScanMode == '3D-Scan')\
        .join(ModelSegmentation, ModelSegmentation.ImageInstanceID == ImageInstance.ImageInstanceID)\
        .join(SegmentationModel).join(Feature)\
        .where(Feature.FeatureName == 'Macular Layers NEW')

    import random
    random_instance = random.choice(query.all())
    instance_id = random_instance[0].ImageInstanceID
    segmentation_id = random_instance[1].ModelSegmentationID
```

### 3. Loading OCT Volume

```python
from rtnls_oct.eyened import dataloading

with database.get_session() as session:
    instance = session.query(ImageInstance)\
        .filter(ImageInstance.ImageInstanceID == instance_id).first()

    oct_volume = dataloading.load_oct_volume_from_orm(instance)

    print(f"OCT volume shape: {oct_volume.image.shape}")
    print(f"Laterality: {oct_volume.laterality}")
    print(f"Resolution: {oct_volume.res_depth_mm} x {oct_volume.res_height_mm} x {oct_volume.res_width_mm} mm")
```

### 4. Loading Segmentation with OCT Volume

```python
from rtnls_oct.eyened import dataloading

with database.get_session() as session:
    segmentation, oct_volume = dataloading.load_model_segmentation_with_oct_by_id(
        session,
        segmentation_id,
    )

    print(f"Segmentation data shape: {segmentation.data.shape}")
    print(f"Segmentation labels: {segmentation.LABELS}")
```

All `load_*_by_id` functions take the database session as the first argument.

### 5. Visualizing Data

```python
import matplotlib.pyplot as plt

bscan_index = oct_volume.n_bscans // 2

fig, axes = plt.subplots(1, 2, figsize=(12, 6))
oct_volume.plot_bscan(bscan_index, ax=axes[0])
segmentation.plot_bscan(bscan_index, ax=axes[0])
oct_volume.plot_enface_image(ax=axes[1])
plt.show()
```

## Available Functions

### Loading OCT Volumes

#### `load_oct_volume_from_orm(imageinstance) -> OCT3DVolume`

Loads a 3D OCT volume from an `ImageInstance` record.

**Parameters:**
- `imageinstance`: An `eyened_orm.ImageInstance` record object

**Returns:**
- `OCT3DVolume`

**Example:**
```python
with database.get_session() as session:
    instance = session.query(ImageInstance).filter_by(ImageInstanceID=123).first()
    oct_volume = dataloading.load_oct_volume_from_orm(instance)
```

#### `load_oct_by_id(session, imageinstance_id) -> OCT3DVolume`

Loads an OCT volume by `ImageInstanceID`.

**Parameters:**
- `session`: ORM database session
- `imageinstance_id`: ID of the ImageInstance record

**Example:**
```python
with database.get_session() as session:
    oct_volume = dataloading.load_oct_by_id(session, 123)
```

### Loading Segmentations

#### `load_segmentation_from_orm(segmentation) -> PixelWiseSegmentation`

Loads a layer segmentation from a segmentation record.

**Parameters:**
- `segmentation`: An `eyened_orm` `ModelSegmentation` or `Segmentation` record

**Returns:**
- `PixelWiseSegmentation` with layer names in `LABELS`

#### `load_model_segmentation_by_id(session, model_segmentation_id) -> PixelWiseSegmentation`

Loads a `ModelSegmentation` by ID.

**Example:**
```python
with database.get_session() as session:
    segmentation = dataloading.load_model_segmentation_by_id(session, 456)
```

#### `load_segmentation_by_id(session, segmentation_id) -> PixelWiseSegmentation`

Loads a manual `Segmentation` by ID.

### Loading Both Together

#### `load_model_segmentation_with_oct_by_id(session, model_segmentation_id) -> tuple[PixelWiseSegmentation, OCT3DVolume]`

Loads both a `ModelSegmentation` and its associated OCT volume.

**Example:**
```python
with database.get_session() as session:
    segmentation, oct_volume = dataloading.load_model_segmentation_with_oct_by_id(session, 456)
```

#### `load_segmentation_with_oct_by_id(session, segmentation_id) -> tuple[PixelWiseSegmentation, OCT3DVolume]`

Loads both a manual `Segmentation` and its associated OCT volume.

**Example:**
```python
with database.get_session() as session:
    segmentation, oct_volume = dataloading.load_segmentation_with_oct_by_id(session, 789)
```

## Complete Example

```python
from eyened_orm import Database, ImageInstance, Modality, ModelSegmentation, Feature, Scan, SegmentationModel
from rtnls_oct.eyened import dataloading
import matplotlib.pyplot as plt

database = Database()

with database.get_session() as session:
    query = session.query(ImageInstance, ModelSegmentation)\
        .filter(ImageInstance.Modality == Modality.OCT)\
        .join(Scan).filter(Scan.ScanMode == '3D-Scan')\
        .join(ModelSegmentation, ModelSegmentation.ImageInstanceID == ImageInstance.ImageInstanceID)\
        .join(SegmentationModel).join(Feature)\
        .where(Feature.FeatureName == 'Macular Layers NEW')

    result = query.first()
    if result:
        segmentation_id = result[1].ModelSegmentationID

        segmentation, oct_volume = dataloading.load_model_segmentation_with_oct_by_id(
            session,
            segmentation_id,
        )

        print(f"OCT Volume Shape: {oct_volume.image.shape}")
        print(f"Laterality: {oct_volume.laterality}")
        print(f"Available Labels: {list(segmentation.LABELS.keys())}")

        fig, axes = plt.subplots(1, 2, figsize=(12, 6))
        oct_volume.plot_enface_image(ax=axes[0])
        axes[0].set_title('Enface Image')
        oct_volume.plot_bscan(oct_volume.n_bscans // 2, ax=axes[1])
        axes[1].set_title('Central B-scan')
        plt.tight_layout()
        plt.show()
```

## Integration with RetinalThicknessReport

`RetinalThicknessReport` supports `PixelWiseSegmentation` natively. Use `from_pixelwise()` for automatic fovea detection:

```python
from rtnls_oct import RetinalThicknessReport

report = RetinalThicknessReport.from_pixelwise(
    oct_volume=oct_volume,
    pixel_seg=segmentation,
    laterality=oct_volume.laterality,
    auto_find_fovea=True,
)

available_labels = segmentation.LABELS.keys()

report.add_thickness_map(
    name="RNFL",
    layer_names=["Retinal Nerve Fiber Layer (RNFL)"],
    vmin=0,
    vmax=0.2,
)

total_layers = [
    "Retinal Nerve Fiber Layer (RNFL)",
    "Ganglion cell layer (GCL)",
    "Inner plexiform layer (IPL)",
    "Inner nuclear layer (INL)",
    "Outer plexiform layer (OPL)",
    "Outer nuclear layer (ONL)",
    "External limiting membrane (ELM)",
    "Myoid zone (MZ)",
    "Ellipsoid zone (EZ)",
    "Outer Segments (OS)",
    "Inter Digitation Zone (IDZ)",
    "Retinal pigment epithelium (RPE)",
]
total_layers = [layer for layer in total_layers if layer in available_labels]

if total_layers:
    report.add_thickness_map(
        name="Total",
        layer_names=total_layers,
        vmin=0,
        vmax=0.5,
    )

report.process()
results = report.get_result_dict()
report.write_report_html("output/report", id="patient_001")
```

Layer names must match the keys in `segmentation.LABELS` as loaded from the database `Feature.subfeatures`.

### Using PixelWiseSegmentation Directly

```python
# Thickness map for specific layers (sum along depth axis)
thickness_map = segmentation.get_thickness_map(["Retinal Nerve Fiber Layer (RNFL)"])

# Mask for a single layer
label_value = segmentation.LABELS["Retinal Nerve Fiber Layer (RNFL)"]
layer_mask = segmentation.data == label_value

# Visualize a B-scan
segmentation.plot_bscan(bscan_index=10)
bscan_data = segmentation.get_bscan(bscan_index=10)
```

## Notes

- **Session management**: Always use database sessions within a context manager (`with database.get_session() as session:`).
- **Argument order**: All `load_*_by_id` functions take `session` as the first argument.
- **Segmentation types**: Supports both `ModelSegmentation` and `Segmentation` from `eyened_orm`.
- **Label mapping**: Labels are extracted from the `Feature` and its `subfeatures` dict. They are stored on `segmentation.LABELS` as `{layer_name: label_value}`.
- **Data format**: `OCT3DVolume.image` shape is `(n_bscans, height, width)`; resolutions are in millimeters.

## Troubleshooting

### Common Issues

1. **"ImageInstance must have a 'pixel_array' attribute"**
   - Ensure the `ImageInstance` has been properly loaded with its pixel data.

2. **"Segmentation record not found"**
   - Verify the segmentation ID exists in the database.
   - Check that you are using the correct session.

3. **Label mapping issues**
   - Check that the `Feature` has the expected structure.
   - Verify `subfeatures` is populated for multi-layer segmentations.
   - Print `segmentation.LABELS` to see available layer names.

4. **Dimension mismatches**
   - Ensure the segmentation dimensions match the OCT volume.
   - Check that both are from the same `ImageInstance`.

5. **Layer name not found in thickness report**
   - Use exact layer names from `segmentation.LABELS.keys()` when calling `add_thickness_map(layer_names=[...])`.
