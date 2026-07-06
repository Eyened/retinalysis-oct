import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass
from rtnls_oct.plotting import plot_image, plot_mask, plot_enface
from rtnls_oct.localization import RegistrationCoordinatesSquare, RegistrationCoordinates
import pydicom

@dataclass
class OCT3DVolume:

    image: np.ndarray
    res_width_mm: float = None
    res_height_mm: float = None
    res_depth_mm: float = None
    laterality: str = None
    orientation: str = None
    direction_bscan: str = 'Right'
    axial_direction: str = 'Down'
    fixation: str = None
    pe_result = None

    @classmethod
    def from_dicom(cls, dicom_file: str) -> 'OCT3DVolume':
        dcmfile = pydicom.dcmread(dicom_file)
        image = dcmfile.pixel_array
        functional_group = dcmfile[0x5200,0x9229][0]
        res_z = functional_group[0x0028,0x9110][0].SliceThickness
        res_y, res_x = functional_group[0x0028,0x9110][0].PixelSpacing
        laterality = functional_group[0x0020,0x9071][0].FrameLaterality
        return cls(image, res_width_mm=res_x, res_height_mm=res_y, res_depth_mm=res_z, laterality=laterality)
    
    def plot_enface_image(self, ax=None, flip_vertical=False):
        if ax is None:
            _, ax = plt.subplots()
        if flip_vertical:
            plot_enface(np.flip(self.image, axis=0), ax=ax)
        else:
            plot_enface(self.image, ax=ax)

    @property
    def resolution_mm(self) -> tuple[float, float, float]:
        return self.res_depth_mm, self.res_height_mm, self.res_width_mm

    def plot_central_bscan(self, ax=None):
        if ax is None:
            fig, ax = plt.subplots()
        index = len(self.image) // 2
        plot_image(self.image[index], ax=ax)
        ax.axis('off')
        return ax
    
    @property
    def n_bscans(self) -> int:
        return len(self.image)
    
    def __len__(self) -> int:
        return self.n_bscans

    def plot_bscan(self, bscan: int, ax=None):
        if ax is None:
            fig, ax = plt.subplots()
        plot_image(self.image[bscan], ax=ax)
        ax.axis('off')
        return ax

    def plot_etdrs_grid(self, center=None, ax=None):
        if ax is None:
            _, ax = plt.subplots()
        from rtnls_oct.utils import get_etdrs_grid_on_image
        fields = get_etdrs_grid_on_image(self.image.shape, self.resolution_mm, self.laterality, self.direction_bscan, self.axial_direction, center)
        for name, mask in fields.items():
            self.plot_enface_image(ax=ax)
            if np.any(mask):
                plot_mask(mask, alpha=0.2, ax=ax)

    def rotate_to_standard_orientation(self, thickness_array: np.ndarray) -> np.ndarray:
        if self.orientation == 'Horizontal':
            if self.axial_direction == 'Up':
                thickness_array = np.flip(thickness_array, axis=0)
            if self.direction_bscan == 'Left':
                thickness_array = np.flip(thickness_array, axis=1)
        elif self.orientation == 'Vertical':
            if self.axial_direction == 'Left':
                thickness_array = np.rot90(thickness_array, k=3)
                if self.direction_bscan == 'Up':
                    thickness_array = np.flip(thickness_array, axis=0)
            elif self.axial_direction == 'Right':
                thickness_array = np.rot90(thickness_array, k=1)
                if self.direction_bscan == 'Down':
                    thickness_array = np.flip(thickness_array, axis=0)
        return thickness_array
    
    def enface_projection(self):
        return np.mean(self.image, axis=1)


    

@dataclass
class OCTVolumeWithEnface:
    """
    Representing an OCT volume linked to an enface image with localization.
    """

    oct_volume: OCT3DVolume
    enface_image: np.ndarray
    registration_coordinates: RegistrationCoordinates
    enface_resolution_mm: tuple[float, float] = None  # (width_mm, height_mm)

    @classmethod
    def from_dicom_files(cls, oct_dicom_file: str, enface_dicom_file: str) -> 'OCTVolumeWithEnface':
        oct_volume = OCT3DVolume.from_dicom(oct_dicom_file)
        enface_image = pydicom.dcmread(enface_dicom_file).pixel_array
        registration_coordinates = RegistrationCoordinates.from_dicom(oct_dicom_file)
        return cls(oct_volume, enface_image, registration_coordinates)
    
    def create_enface_projection(self):
        if len(self.enface_image.shape) == 3:
            projected_enface = np.zeros_like(self.enface_image[:,:,0])
        else:
            projected_enface = np.zeros_like(self.enface_image)

        top_left = self.registration_coordinates.top_left
        bottom_right = self.registration_coordinates.bottom_right
        top_left = (int(top_left[0]), int(top_left[1]))
        bottom_right = (int(bottom_right[0]), int(bottom_right[1]))
        size_x = bottom_right[0] - top_left[0]
        size_z = bottom_right[1] - top_left[1]

        from skimage.transform import resize

        enface_oct = self.oct_volume.enface_projection()

        # Resize to match the registration region size
        enface_resized = resize(enface_oct, (size_x, size_z), order=1, preserve_range=True, anti_aliasing=True)


        # Insert the resized enface into the correct region
        projected_enface[top_left[0]:bottom_right[0], top_left[1]:bottom_right[1]] = enface_resized

        return projected_enface
    
    def plot_oct_on_enface(self, ax=None):
        if ax is None:
            fig, ax = plt.subplots()
        enface_projection = self.create_enface_projection()
        ax.imshow(self.enface_image)
        ax.imshow(enface_projection, cmap='gray', alpha=1.0*(enface_projection>0))
        ax.axis('off')
        return ax

    
