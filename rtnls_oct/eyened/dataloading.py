"""
Data loading utilities for OCT volumes and segmentations from eyened_orm.

Note: This module requires the EyeNED Platform to be installed.
"""
import numpy as np
from typing import Optional
from rtnls_oct.oct3d import OCT3DVolume
from rtnls_oct.segmentations import ContoursData, PixelWiseSegmentation

try:
    from eyened_orm import ImageInstance, Segmentation, ModelSegmentation, SegmentationBase
except ImportError:
    ImageInstance = None
    Segmentation = None
    ModelSegmentation = None
    SegmentationBase = None
    _EYENED_ORM_AVAILABLE = False
else:
    _EYENED_ORM_AVAILABLE = True


def _check_eyened_orm_available():
    """Check if eyened_orm is available, raise ImportError if not."""
    if not _EYENED_ORM_AVAILABLE:
        raise ImportError(
            "eyened_orm is not installed. "
            "Find it in the EyeNED Platform: github.com/eyened/eyened-platform"
        )


def load_oct_volume_from_orm(imageinstance) -> OCT3DVolume:
    """
    Load a 3D OCT volume from an eyened_orm ImageInstance record.
    
    Args:
        imageinstance: An eyened_orm ImageInstance record object
    
    Returns:
        OCT3DVolume: A 3D OCT volume object
    """
    _check_eyened_orm_available()
    # Load image data
    if hasattr(imageinstance, 'pixel_array'):
        image = imageinstance.pixel_array
    else:
        raise ValueError("ImageInstance must have a 'pixel_array' attribute")
    
    # Get resolution data
    res_height_mm = getattr(imageinstance, 'ResolutionAxial', None)
    res_width_mm = getattr(imageinstance, 'ResolutionHorizontal', None)
    res_depth_mm = getattr(imageinstance, 'ResolutionVertical', None)

    # Get metadata
    laterality = imageinstance.Laterality.value
    
    return OCT3DVolume(
        image=image,
        res_width_mm=res_width_mm,
        res_height_mm=res_height_mm,
        res_depth_mm=res_depth_mm,
        laterality=laterality,
    )


def load_segmentation_from_orm(segmentation) -> PixelWiseSegmentation:
    """
    Load layer segmentation from an eyened_orm segmentation record.
    
    Args:
        segmentation: An eyened_orm Segmentation record object
    
    Returns:
        PixelWiseSegmentation: A PixelWiseSegmentation object with the segmentation
    """
    _check_eyened_orm_available()

    seg_object = PixelWiseSegmentation(segmentation.read_data())
    if isinstance(segmentation, ModelSegmentation):
        feature = segmentation.Model.Feature
    elif isinstance(segmentation, Segmentation):
        feature = segmentation.Feature
    else:
        raise ValueError(f"Segmentation must be an instance of ModelSegmentation or Segmentation, found {type(segmentation)} instead")
    if feature.subfeatures:
        print(f"Subfeatures: {feature.subfeatures}")
        labels = {subfeature: i for i, subfeature in feature.subfeatures.items()}
    else:
        labels = {'Background': 0, feature.FeatureName: 1}
    seg_object.LABELS = labels
    return seg_object

def load_oct_by_id(session, imageinstance_id: int) -> OCT3DVolume:
    """
    Load OCT volume by ID from eyened_orm.
    
    Args:
        imageinstance_id: ID of the ImageInstance record
        session: ORM database session
    
    Returns:
        OCT3DVolume
    """
    _check_eyened_orm_available()
    imageinstance = session.query(ImageInstance).filter(ImageInstance.ImageInstanceID==imageinstance_id).first()
    if imageinstance is None:
        raise ValueError(f"ImageInstance record with id {imageinstance_id} not found")
    return load_oct_volume_from_orm(imageinstance)


def load_model_segmentation_by_id(session, model_segmentation_id: int) -> PixelWiseSegmentation:
    """
    Load segmentation associated with an ImageInstance by ImageInstance ID.
    
    Args:
        imageinstance_id: ID of the ImageInstance record
        session: ORM database session
    
    Returns:
        PixelWiseSegmentation
    """
    _check_eyened_orm_available()
    model_segmentation = session.query(ModelSegmentation).filter(ModelSegmentation.ModelSegmentationID==model_segmentation_id).first()

    if model_segmentation is None:
        raise ValueError(f"ModelSegmentation record with id {model_segmentation_id} not found")
    return load_segmentation_from_orm(model_segmentation)

def load_segmentation_by_id(session, segmentation_id: int) -> PixelWiseSegmentation:
    """
    Load segmentation by ID from eyened_orm.
    
    Args:
        segmentation_id: ID of the Segmentation record
        session: ORM database session
    
    Returns:
        PixelWiseSegmentation
    """
    _check_eyened_orm_available()
    segmentation = session.query(Segmentation).filter(Segmentation.SegmentationID==segmentation_id).first()
    return load_segmentation_from_orm(segmentation)

def load_model_segmentation_with_oct_by_id(session, model_segmentation_id: int) -> tuple[PixelWiseSegmentation, OCT3DVolume]:
    """
    Load ModelSegmentation and OCT volume by ID from eyened_orm.
    
    Args:
        model_segmentation_id: ID of the ModelSegmentation record
        session: ORM database session
    
    Returns:
        tuple: (PixelWiseSegmentation, OCT3DVolume)
    """
    _check_eyened_orm_available()
    model_segmentation = session.query(ModelSegmentation).filter(ModelSegmentation.ModelSegmentationID==model_segmentation_id).first()
    if model_segmentation is None:
        raise ValueError(f"ModelSegmentation record with id {model_segmentation_id} not found")
    oct_volume = load_oct_volume_from_orm(model_segmentation.ImageInstance)
    segmentation = load_segmentation_from_orm(model_segmentation)
    return segmentation, oct_volume

def load_segmentation_with_oct_by_id(session, segmentation_id: int) -> tuple[PixelWiseSegmentation, OCT3DVolume]:
    """
    Load segmentation and OCT volume by ID from eyened_orm.
    
    Args:
        session: ORM database session
        segmentation_id: ID of the Segmentation record
    
    Returns:
        tuple: (PixelWiseSegmentation, OCT3DVolume)
    """
    _check_eyened_orm_available()
    segmentation = session.query(Segmentation).filter_by(SegmentationID=segmentation_id).first()
    if segmentation is None:
        raise ValueError(f"Segmentation record with id {segmentation_id} not found")
    oct_volume = load_oct_volume_from_orm(segmentation.ImageInstance)
    return load_segmentation_from_orm(segmentation), oct_volume