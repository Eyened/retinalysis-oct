import numpy as np
from rtnls_oct import plotting
import matplotlib.pyplot as plt

class ContoursData:

    width: int
    n_bscans: int
    height_maps: dict[str, np.ndarray]

    def __init__(self, width: int, n_bscans: int, contour_lines=None):
        self.width = width
        self.n_bscans = n_bscans
        self.height_maps = {}
        if contour_lines is not None:
            for bscan_index, bscan_contour_lines in enumerate(contour_lines):
                for name, contour in bscan_contour_lines.items():
                    self.add_contour_line(bscan_index, name, contour)

    @classmethod
    def from_npz(cls, file_path: str):
        with np.load(file_path) as height_maps:
            ## check if empty
            if len(height_maps) == 0:
                raise ValueError("No height maps found in the file")
            first_contour = height_maps[next(iter(height_maps))]
            obj = cls(first_contour.shape[0], first_contour.shape[1])
            for k, v in height_maps.items():
                obj.add_surface(k, v)
        return obj

    def add_surface(self, name: str, contour: np.ndarray):
        if not name in self.height_maps:
            self.height_maps[name] = np.full((self.n_bscans, self.width), np.nan)
        self.height_maps[name] = contour

    def add_contour_line(self, bscan_index:int, name: str, contour: np.ndarray):
        if not name in self.height_maps:
            self.height_maps[name] = np.nan(self.n_bscans, self.width)
        self.contour_lines[name][bscan_index] = contour

    def get_unique_names(self):
        return list(self.height_maps.keys())

    def __repr__(self):
        contours = ', '.join(self.get_unique_names())
        return f"<ContourData: {contours}>"
    
    def has_contour(self, name):
        names = self.get_unique_names()
        return name in names
    
    def get_height_map(self, name):
        if not self.has_contour(name):
            raise ValueError("Contour not found")
        return self.height_maps[name]
    
    def get_mask(self, top_name, bottom_name, total_height):
        if not self.has_contour(top_name) or not self.has_contour(bottom_name):
            raise ValueError("Contour not found")
        top_heights = self.get_height_map(top_name)
        bottom_heights = self.get_height_map(bottom_name)
        mask = np.zeros((*top_heights.shape, total_height), dtype=bool)
        for i, (top_line, bottomline) in enumerate(zip(top_heights, bottom_heights)):
            for j, (top, bottom) in enumerate(zip(top_line, bottomline)):
                if top == 0 or bottom == 0:
                    continue
                top_int = int(np.round(top))
                bottom_int = int(np.round(bottom))
                mask[i, j, top_int:bottom_int] = True
        return mask
    
    def get_contours_on_bscan(self, bscan: int):
        contours = {}
        for name, contour in self.height_maps.items():
            contours[name] = contour[bscan, :]
        return contours
    
    def get_thickness_map(self, top_name: str, bottom_name: str):
        top_heights = self.get_height_map(top_name)
        bottom_heights = self.get_height_map(bottom_name)
        thickness = top_heights - bottom_heights
        mask = np.logical_or(top_heights == 0, bottom_heights == 0)
        return np.ma.masked_array(thickness, mask=mask)


class PixelWiseSegmentation:

    LABELS = {
        'Background': [0],
        'Foreground': [1]
    }

    def __init__(self, data: np.ndarray) -> None:
        self.data = data.astype(np.uint8)

    def get_height_map(self, label: str) -> np.ndarray:
        label = self.LABELS[label]
        return np.argmax(self.data == label, axis=1)
    
    def get_mask(self, label: str):
        label = self.LABELS[label]
        return self.data == label
    
    def plot_bscan(self, bscan: int, label=None, ax=None):
        if ax is None:
            fig, ax = plt.subplots()
        if label is None:
            plotting.plot_mask(self.data[bscan, :, :], ax=ax)
        else:
            plotting.plot_mask(self.data[bscan, :, :] == self.LABELS[label][0], ax=ax)
        return ax

    def get_bscan(self, bscan: int):
        return self.data[bscan, :, :]
    
    def get_thickness_map(self, label: str):
        thickness = np.sum(self.get_mask(label), axis=1)
        return thickness


class MacularLayers(PixelWiseSegmentation):

    LABELS = {
        'Background': [0],
        'RNFL': [1],
        'GCL': [2],
        'IPL': [3],
        'INL': [4],
        'OPL': [5],
        'ONL': [6],
        'ELM': [7],
        'MZ': [8],
        'EZ': [9],
        'OS': [10],
        'IDZ': [11],
        'RPE': [12],
        'CHOROID': [13],
        'OTHER': [14]
    }