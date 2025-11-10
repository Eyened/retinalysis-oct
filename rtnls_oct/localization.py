import pydicom
import numpy as np
from dataclasses import dataclass
from abc import abstractmethod

@dataclass
class RegistrationCoordinatesSquare:
    """
    Coordinates of an OCT volume on the enface image.
    """
    top_left: tuple[float, float] = None
    bottom_right: tuple[float, float] = None

    def __init__(self, top_left: tuple[float, float], bottom_right: tuple[float, float]):
        self.top_left = top_left
        self.bottom_right = bottom_right

    @classmethod
    def from_dicom(cls, dicom_file: str) -> 'RegistrationCoordinatesSquare':
        dcmfile = pydicom.dcmread(dicom_file)
        coordinates = [c[0x22,0x31][0][0x22,0x32].value for c in dcmfile[0x5200,0x9230]]
        coordinates = np.array(coordinates)
        top_left = [int(coordinates[0][1]), int(coordinates[0][0])]
        bottom_right = [int(coordinates[-1][3]), int(coordinates[-1][2])]
        return cls(top_left, bottom_right)
    


@dataclass
class RegistrationCoordinatesBScan:

    n_points: int

    @abstractmethod
    def get_coordinates(self) -> tuple[np.ndarray, np.ndarray]:
        pass


@dataclass
class RegistrationCoordinatesBScanLine(RegistrationCoordinatesBScan):
    """
    Coordinates of a b-scan line on the enface image
    """
    start: tuple[float, float]
    end: tuple[float, float]

    def get_coordinates(self) -> tuple[np.ndarray, np.ndarray]:
        y_vals = np.linspace(self.start[0], self.end[0], self.n_points)
        x_vals = np.linspace(self.start[1], self.end[1], self.n_points)
        return y_vals, x_vals

@dataclass
class RegistrationCoordinatesBscanCircle(RegistrationCoordinatesBScan):
    """
    Coordinates of the b-scan circle on the enface image
    """
    start: tuple[float, float]
    radius: float
    center: tuple[float, float]

    def get_coordinates(self) -> tuple[np.ndarray, np.ndarray]:
        pi_vals = np.linspace(0, 2*np.pi, self.n_points)
        x_vals = self.center[1] + self.radius * np.cos(pi_vals)
        y_vals = self.center[0] + self.radius * np.sin(pi_vals)
        return y_vals, x_vals
    

@dataclass
class RegistrationCoordinates:
    """
    Coordinates of the b-scan lines on the enface image
    """
    bscan_coordinates: list[RegistrationCoordinatesBScan]

    @classmethod
    def from_dicom(cls, dicom_file: str) -> 'RegistrationCoordinates':
        dcmfile = pydicom.dcmread(dicom_file)
        n_points = dcmfile.Columns
        coordinates = []
        for functional_group in dcmfile[0x5200,0x9230]:
            orientation = functional_group[0x0022,0x31][0][0x0022,0x39].value   
            if orientation == 'LINEAR':
                values = functional_group[0x0022,0x31][0][0x0022,0x32]
                coordinates.append(RegistrationCoordinatesBScanLine(start=(values[0], values[1]), end=(values[2], values[3]), n_points=n_points))
            else:
                raise ValueError(f"Unsupported b-scan type: {orientation}")

        return cls(bscan_coordinates=coordinates)
    
    def get_coordinates(self) -> tuple[np.ndarray, np.ndarray]:
        xvals = []
        yvals = []
        for bscan_coordinate in self.bscan_coordinates:
            xvals.append(bscan_coordinate.get_coordinates()[0])
            yvals.append(bscan_coordinate.get_coordinates()[1])
        return np.array(yvals), np.array(xvals)
    
    @classmethod
    def from_cube(cls, top_left: tuple[float, float], bottom_right: tuple[float, float], n_points: int, n_bscans: int) -> 'RegistrationCoordinates':
        coordinates = []
        for i in range(n_bscans):
            coordinates.append(RegistrationCoordinatesBScanLine(start=(top_left[0], top_left[1] + i*((bottom_right[1] - top_left[1])/n_bscans)), end=(bottom_right[0], top_left[1] + i*((bottom_right[1] - top_left[1])/n_bscans)), n_points=n_points))
        return cls(bscan_coordinates=coordinates)
    
    @property
    def top_left(self) -> tuple[float, float]:
        return self.bscan_coordinates[0].start
    
    @property
    def bottom_right(self) -> tuple[float, float]:
        return self.bscan_coordinates[-1].end
    
    def is_square(self) -> bool:
        return self.bscan_coordinates[0].start[0] == self.bscan_coordinates[1].start[0] and \
            self.bscan_coordinates[0].end[0] == self.bscan_coordinates[1].end[0]

