import numpy as np
from scipy.interpolate import RegularGridInterpolator
import matplotlib.pyplot as plt
from rtnls_oct import utils

class InterpolationMap:

    x_locs: np.ndarray
    y_locs: np.ndarray

    def __init__(self, x_locs: np.ndarray, y_locs: np.ndarray, reference_laterality='R'):
        self.x_locs = x_locs
        self.y_locs = y_locs
        self.reference_laterality = reference_laterality

    def interpolate(self, thickness_map: np.ndarray, laterality: str, 
                    resolution_mm: tuple[float, float], 
                    center: tuple[int, int]=(0, 0), fill_value=np.nan) -> np.ndarray:
        interpolator = RegularGridInterpolator(
            (range(thickness_map.shape[0]),range(thickness_map.shape[1])), thickness_map,
            fill_value=fill_value, bounds_error=False)
        if laterality == self.reference_laterality:
            xvals = center[1] + self.x_locs/resolution_mm[1]
        else:
            xvals = center[1] - self.x_locs/resolution_mm[1]

        yvals = center[0] + self.y_locs/resolution_mm[0]
        return interpolator((yvals, xvals))
    
    def get_masks(self):
        return {
            'all': np.ones(self.x_locs.shape),
        }
       
    def plot_with_values(
        self,
        values: np.ndarray,
        ax=None,
        center=(0, 0),
        resolution_mm=(1, 1),
        laterality: str | None = None,
        **kwargs,
    ):
        """Scatter sample locations in image pixel space, colored by ``values``.

        Uses the same x/y convention as :meth:`interpolate`. If ``laterality`` is
        omitted, ``reference_laterality`` is assumed (matches sampling that eye).
        """
        if ax is None:
            _, ax = plt.subplots()
        if laterality is None:
            laterality = self.reference_laterality
        if laterality == self.reference_laterality:
            xvals = center[1] + self.x_locs / resolution_mm[1]
        else:
            xvals = center[1] - self.x_locs / resolution_mm[1]
        yvals = center[0] + self.y_locs / resolution_mm[0]
        ax.scatter(xvals, yvals, c=values, **kwargs)
        return ax
    


class CircularInterpolationMap(InterpolationMap):

    def __init__(self, radius_mm: float, points_per_mm: int, reference_laterality='R'):
        extent = radius_mm + 2 / points_per_mm
        n_points = int(points_per_mm * radius_mm * 2 + 2)
        x_range = np.linspace(-extent, extent, n_points)
        y_range = np.linspace(-extent, extent, n_points)
        xval, yval = np.meshgrid(x_range, y_range)
        dist = np.sqrt(xval**2 + yval**2)

        self.y_locs=xval[dist <= radius_mm].flatten()
        self.x_locs=yval[dist <= radius_mm].flatten()
        super().__init__(self.x_locs, self.y_locs, reference_laterality)
        
    def plot(self, ax=None, center=(0, 0)):
        if ax is None:
            fig, ax = plt.subplots()
        ax.scatter(self.x_locs + center[1], self.y_locs + center[0], s=1, c='r')
        return ax
 

class ETDRSInterpolationMap(CircularInterpolationMap):

    def __init__(self, points_per_mm=10, reference_laterality='R'):
        super().__init__(radius_mm=3, points_per_mm=points_per_mm, reference_laterality=reference_laterality)

    def get_masks(self):
        return utils.get_etdrs_fields(self.x_locs, self.y_locs, self.reference_laterality)

