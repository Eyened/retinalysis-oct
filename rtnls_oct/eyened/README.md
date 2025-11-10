# Loading OCT Data from eyened_orm

This module provides utilities for loading 3D OCT volumes and layer segmentations from the `eyened_orm` database into Retinalysis-OCT data structures.

## Overview

The `rtnls_oct.eyened.dataloading` module bridges the gap between the `eyened_orm` database ORM and the Retinalysis-OCT analysis tools. It converts `ImageInstance` and `Segmentation` records into `OCT3DVolume` and `PixelWiseSegmentation` objects that can be used with the rest of the Retinalysis-OCT package.

## Prerequisites

- `eyened_orm` package installed and configured
- Database connection set up
- Access to OCT `ImageInstance` and `Segmentation` records

## Basic Usage

### 1. Setting Up Database Connection

First, establish a connection to the database:

```python
from eyened_orm import Database

database = Database()
```

### 2. Querying OCT Images and Segmentations

Query the database to find OCT images with segmentations:

```python
from eyened_orm import ImageInstance, Modality, ETDRSField, ModelSegmentation, Feature, Scan, SegmentationModel

with database.get_session() as session:
    # Query for OCT images with macular layer segmentations
    query = session.query(ImageInstance, ModelSegmentation)\
        .filter(ImageInstance.Modality == Modality.OCT)\
        .filter(ImageInstance.ETDRSField == ETDRSField.F2)\
        .join(Scan).filter(Scan.ScanMode == '3D-Scan')\
        .join(ModelSegmentation, ModelSegmentation.ImageInstanceID == ImageInstance.ImageInstanceID)\
        .join(SegmentationModel).join(Feature)\
        .where(Feature.FeatureName == 'Macular Layers NEW')
    
    # Get a random instance for demonstration
    import random
    random_instance = random.choice(query.all())
    instance_id = random_instance[0].ImageInstanceID
    segmentation_id = random_instance[1].ModelSegmentationID
```

### 3. Loading OCT Volume

Load an OCT volume from an `ImageInstance`:

```python
from rtnls_oct.eyened import dataloading

with database.get_session() as session:
    instance = session.query(ImageInstance)\
        .filter(ImageInstance.ImageInstanceID == instance_id).first()
    
    oct_volume = dataloading.load_oct_volume_from_orm(instance)
    
    # Check the volume shape: (n_bscans, height, width)
    print(f"OCT volume shape: {oct_volume.image.shape}")
    print(f"Laterality: {oct_volume.laterality}")
    print(f"Resolution: {oct_volume.res_depth_mm} x {oct_volume.res_height_mm} x {oct_volume.res_width_mm} mm")
```

### 4. Loading Segmentation

Load a segmentation along with its associated OCT volume:

```python
from rtnls_oct.eyened import dataloading

with database.get_session() as session:
    # Load both segmentation and OCT volume together
    segmentation, oct_volume = dataloading.load_model_segmentation_with_oct_by_id(
        segmentation_id, 
        session
    )
    
    # Check available labels
    print(f"Segmentation labels: {segmentation.LABELS}")
    print(f"Custom labels: {segmentation.labels}")
```

### 5. Visualizing Data

Visualize the loaded data:

```python
import matplotlib.pyplot as plt

# Plot a specific B-scan with segmentation overlay
segmentation.plot_bscan(bscan_index=10)

# Or plot a specific layer
segmentation.plot_bscan(bscan_index=10, label='RNFL')

# Plot the OCT volume enface image
fig, ax = plt.subplots(figsize=(8, 8))
oct_volume.plot_enface_image(ax=ax)
plt.show()

# Plot a specific B-scan from the OCT volume
fig, ax = plt.subplots(figsize=(10, 6))
oct_volume.plot_bscan(bscan_index=10, ax=ax)
plt.show()
```

## Available Functions

### Loading OCT Volumes

#### `load_oct_volume_from_orm(imageinstance: ImageInstance) -> OCT3DVolume`

Loads a 3D OCT volume from an `ImageInstance` record.

**Parameters:**
- `imageinstance`: An `eyened_orm.ImageInstance` record object

**Returns:**
- `OCT3DVolume`: A 3D OCT volume object with image data and metadata

**Example:**
```python
with database.get_session() as session:
    instance = session.query(ImageInstance).filter_by(ImageInstanceID=123).first()
    oct_volume = dataloading.load_oct_volume_from_orm(instance)
```

#### `load_oct_by_id(imageinstance_id: int, session) -> OCT3DVolume`

Loads an OCT volume by `ImageInstanceID`.

**Parameters:**
- `imageinstance_id`: ID of the ImageInstance record
- `session`: ORM database session

**Returns:**
- `OCT3DVolume`: A 3D OCT volume object

**Example:**
```python
with database.get_session() as session:
    oct_volume = dataloading.load_oct_by_id(123, session)
```

### Loading Segmentations

#### `load_segmentation_from_orm(segmentation: SegmentationBase) -> PixelWiseSegmentation`

Loads a layer segmentation from a segmentation record.

**Parameters:**
- `segmentation`: An `eyened_orm.SegmentationBase` record (either `ModelSegmentation` or `Segmentation`)

**Returns:**
- `PixelWiseSegmentation`: A pixel-wise segmentation object

**Example:**
```python
with database.get_session() as session:
    model_seg = session.query(ModelSegmentation).filter_by(ModelSegmentationID=456).first()
    segmentation = dataloading.load_segmentation_from_orm(model_seg)
```

#### `load_model_segmentation_by_id(model_segmentation_id: int, session) -> PixelWiseSegmentation`

Loads a `ModelSegmentation` by ID.

**Parameters:**
- `model_segmentation_id`: ID of the ModelSegmentation record
- `session`: ORM database session

**Returns:**
- `PixelWiseSegmentation`: A pixel-wise segmentation object

**Example:**
```python
with database.get_session() as session:
    segmentation = dataloading.load_model_segmentation_by_id(456, session)
```

#### `load_segmentation_by_id(segmentation_id: int, session) -> PixelWiseSegmentation`

Loads a `Segmentation` by ID.

**Parameters:**
- `segmentation_id`: ID of the Segmentation record
- `session`: ORM database session

**Returns:**
- `PixelWiseSegmentation`: A pixel-wise segmentation object

### Loading Both Together

#### `load_model_segmentation_with_oct_by_id(model_segmentation_id: int, session) -> tuple[PixelWiseSegmentation, OCT3DVolume]`

Loads both a `ModelSegmentation` and its associated OCT volume.

**Parameters:**
- `model_segmentation_id`: ID of the ModelSegmentation record
- `session`: ORM database session

**Returns:**
- `tuple`: A tuple containing `(PixelWiseSegmentation, OCT3DVolume)`

**Example:**
```python
with database.get_session() as session:
    segmentation, oct_volume = dataloading.load_model_segmentation_with_oct_by_id(456, session)
```

#### `load_segmentation_with_oct_by_id(segmentation_id: int, session) -> tuple[PixelWiseSegmentation, OCT3DVolume]`

Loads both a `Segmentation` and its associated OCT volume.

**Parameters:**
- `segmentation_id`: ID of the Segmentation record
- `session`: ORM database session

**Returns:**
- `tuple`: A tuple containing `(PixelWiseSegmentation, OCT3DVolume)`

## Complete Example

Here's a complete example that loads data and performs basic analysis:

```python
from eyened_orm import Database, ImageInstance, Modality, ETDRSField, ModelSegmentation, Feature, Scan, SegmentationModel
from rtnls_oct.eyened import dataloading
from rtnls_oct import utils
import matplotlib.pyplot as plt

# Set up database
database = Database()

with database.get_session() as session:
    # Query for OCT with macular layers
    query = session.query(ImageInstance, ModelSegmentation)\
        .filter(ImageInstance.Modality == Modality.OCT)\
        .join(Scan).filter(Scan.ScanMode == '3D-Scan')\
        .join(ModelSegmentation, ModelSegmentation.ImageInstanceID == ImageInstance.ImageInstanceID)\
        .join(SegmentationModel).join(Feature)\
        .where(Feature.FeatureName == 'Macular Layers NEW')
    
    # Get first result
    result = query.first()
    if result:
        instance_id = result[0].ImageInstanceID
        segmentation_id = result[1].ModelSegmentationID
        
        # Load both segmentation and OCT volume
        segmentation, oct_volume = dataloading.load_model_segmentation_with_oct_by_id(
            segmentation_id, 
            session
        )
        
        # Display information
        print(f"OCT Volume Shape: {oct_volume.image.shape}")
        print(f"Laterality: {oct_volume.laterality}")
        print(f"Available Labels: {segmentation.labels}")
        
        # Visualize
        fig, axes = plt.subplots(1, 2, figsize=(12, 6))
        
        # Plot enface image
        oct_volume.plot_enface_image(ax=axes[0])
        axes[0].set_title('Enface Image')
        
        # Plot B-scan with segmentation
        oct_volume.plot_bscan(oct_volume.n_bscans // 2, ax=axes[1])
        axes[1].set_title('Central B-scan')
        
        plt.tight_layout()
        plt.show()
```

## Integration with RetinalThicknessReport

Once you've loaded the data, you can use it with other Retinalysis-OCT tools. Note that `RetinalThicknessReport` expects `ContoursData` (height maps), while the eyened_orm loader returns `PixelWiseSegmentation` (pixel-wise labels).

### Converting PixelWiseSegmentation to ContoursData

To convert a pixel-wise segmentation to height maps for use with `RetinalThicknessReport`:

```python
from rtnls_oct.segmentations import ContoursData
import numpy as np

# Extract height maps from pixel-wise segmentation
# For each layer, find the topmost pixel (argmax along depth axis)
n_bscans, height, width = segmentation.data.shape

# Create ContoursData object
contours_data = ContoursData(width=width, n_bscans=n_bscans)

# Extract height maps for each layer in the labels
# Note: segmentation.labels maps layer names to label values
for layer_name, label_value in segmentation.labels.items():
    if layer_name == 'Background':
        continue
    
    # Get mask for this layer (data shape is n_bscans x height x width)
    layer_mask = (segmentation.data == label_value)
    
    # Find topmost pixel (minimum depth index) for each position using argmax
    # argmax returns first True value along depth axis (axis=1)
    # Shape: (n_bscans, width)
    height_map = np.argmax(layer_mask, axis=1)
    
    # Set to 0 where layer is not present (no True values found)
    # argmax returns 0 if no True value found, so we need to check if layer exists
    has_layer = np.any(layer_mask, axis=1)
    height_map[~has_layer] = 0
    
    contours_data.add_surface(layer_name, height_map)

# Now you can use it with RetinalThicknessReport
from rtnls_oct import RetinalThicknessReport
from rtnls_oct import utils

fovea_y, fovea_x = utils.find_fovea(
    height_map=contours_data.get_height_map("ILM"),
    res_depth_mm=oct_volume.res_depth_mm,
    res_width_mm=oct_volume.res_width_mm
)

report = RetinalThicknessReport(
    oct_volume=oct_volume,
    segmentation=contours_data,
    laterality=oct_volume.laterality,
    fovea_x=fovea_x,
    fovea_y=fovea_y
)
```

### Using PixelWiseSegmentation Directly

For pixel-wise analysis, you can use the segmentation methods directly. Note that some methods may require the layer name to match the `LABELS` class attribute, while custom labels are stored in the instance `labels` attribute:

```python
# Get mask for a layer using the label value directly
label_value = segmentation.labels.get('RNFL', None)
if label_value is not None:
    layer_mask = (segmentation.data == label_value)

# Get thickness map (sum along depth axis)
# Note: This requires the layer to be in LABELS, or use manual calculation
if 'RNFL' in segmentation.labels:
    label_value = segmentation.labels['RNFL']
    thickness_map = np.sum(segmentation.data == label_value, axis=1)

# Visualize a specific B-scan
# Note: plot_bscan uses LABELS class attribute, so custom labels may not work directly
# You may need to access the data directly:
import matplotlib.pyplot as plt
bscan_data = segmentation.get_bscan(bscan_index=10)
plt.imshow(bscan_data, cmap='gray')
plt.show()
```

## Notes

- **Session Management**: Always use database sessions within a context manager (`with database.get_session() as session:`) to ensure proper cleanup.

- **Segmentation Types**: The module supports both `ModelSegmentation` and `Segmentation` types from `eyened_orm`.

- **Label Mapping**: Segmentation labels are automatically extracted from the `Feature` and `subfeatures_list` in the database. Custom labels are stored in the `labels` attribute of the `PixelWiseSegmentation` object.

- **Data Format**: The loaded `OCT3DVolume` follows the Retinalysis-OCT conventions: image shape is `(n_bscans, height, width)` and resolutions are in millimeters.

## Troubleshooting

### Common Issues

1. **"ImageInstance must have a 'pixel_array' attribute"**
   - Ensure the `ImageInstance` has been properly loaded with its pixel data
   - Check that the image data is accessible via `imageinstance.pixel_array`

2. **"Segmentation record not found"**
   - Verify the segmentation ID exists in the database
   - Check that you're using the correct session

3. **Label mapping issues**
   - Check that the `Feature` has the expected structure
   - Verify `subfeatures_list` is populated for multi-layer segmentations

4. **Dimension mismatches**
   - Ensure the segmentation dimensions match the OCT volume
   - Check that both are from the same `ImageInstance`

