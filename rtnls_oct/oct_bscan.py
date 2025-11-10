from dataclasses import dataclass
import numpy as np

from rtnls_oct.segmentations import ContoursData
import matplotlib.pyplot as plt

@dataclass
class OCTBScan:

    image: np.ndarray
    res_width_mm: float
    res_height_mm: float
    laterality: str = None
    fixation: str = None
    contour_lines: ContoursData = None

@dataclass
class OCTBScanCircular(OCTBScan):

    image: np.ndarray
    res_width_mm: float
    res_height_mm: float
    start_angle: float = None
    laterality: str = None
    fixation: str = None
    contour_lines: ContoursData = None

    def get_thickness_map(self, top_name, bottom_name):
        if self.contour_lines.has_contour(top_name) and self.contour_lines.has_contour(bottom_name):
            return self.contour_lines.get_thickness_map(top_name, bottom_name) * self.res_height_mm
        else:
            raise ValueError("Contours not found")
        
    def add_contour_line(self, bscan_index:int, name: str, contour: np.ndarray):
        if self.contour_lines is None:
            self.contour_lines = ContoursData(1)
        self.contour_lines.add_contour_line(bscan_index, name, contour)

    def get_angles_in_degrees_from_temporal(self):
        degrees = np.linspace(0, 360, self.image.shape[1])
        angle_temporal = 0 if self.laterality == 'L' else 180
        start_angle = self.start_angle * 180 / np.pi
        degrees = (degrees + start_angle - angle_temporal + 360) % 360
        return degrees


    def extract_thickness_tsnit(self, top_name, bottom_name):
        thickness = self.get_thickness_map(top_name, bottom_name)[0]
        results = {}
        degrees = self.get_angles_in_degrees_from_temporal()
        for area, start, end in zip(
                        ['T', 'TS', 'NS', 'N', 'NI', 'TI'],
                        [310, 40, 80, 120, 230, 270],
                        [40, 80, 120, 230, 270, 310]
                    ):
            if start > end:
                        indices = np.logical_or(
                            degrees > start, degrees <= end)
            else:
                indices = np.logical_and(
                    degrees > start, degrees <= end)
            measurements = thickness[indices]
            results[area] =\
                np.mean(measurements)
        results['total'] = np.mean(thickness)
        return results
    
    def extract_thickness_tsnit_straight(self, top_name, bottom_name):
        thickness = self.get_thickness_map(top_name, bottom_name)[0]
        results = {}
        degrees = self.get_angles_in_degrees_from_temporal()
        for area, start, end in zip(
                        ['T', 'TS', 'NS', 'N', 'NI', 'TI'],
                        [315, 45, 90, 135, 225, 270],
                        [45, 90, 135, 225, 270, 315]
                    ):
            if start > end:
                        indices = np.logical_or(
                            degrees > start, degrees <= end)
            else:
                indices = np.logical_and(
                    degrees > start, degrees <= end)
            measurements = thickness[indices]
            results[area] =\
                np.mean(measurements)
        results['total'] = np.mean(thickness)
        return results
    
    def plot_thickness_map(self, top_name, bottom_name):
        thickness = self.get_thickness_map(top_name, bottom_name)[0]
        degrees = self.get_angles_in_degrees_from_temporal()
        plt.plot(degrees, thickness)

    def plot_bscan(self, contours=False, ax=None):
        if ax is None:
             _, ax = plt.subplots()
        ax.imshow(self.image, cmap='gray')
        if contours:
            for name, c in self.contour_lines.contour_lines[0].items():
                ax.plot(self.image.shape[0] - c, label=name)
            ax.legend()
        ax.axis('off')

        