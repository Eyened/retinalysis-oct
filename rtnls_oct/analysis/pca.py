from sklearn.decomposition import PCA
import numpy as np
import joblib
import matplotlib.pyplot as plt
from rtnls_oct.analysis.interpolation import InterpolationMap

class PCAThicknessMap:

    def __init__(self, n_components: int, interpolation_map: InterpolationMap):
        self.n_components = n_components
        self.pca = PCA(n_components=n_components)
        self.interpolation_map = interpolation_map
        self.fill_values = None

    def to_file(self, path: str):
        save_data = {
            'n_components': self.n_components,
            'pca': self.pca,
            'interpolation_map': self.interpolation_map,
            'fill_values': getattr(self, 'fill_values', None),  # Safe attribute access
            }
        joblib.dump(save_data, path)

    @classmethod
    def from_file(cls, path: str):
        data = joblib.load(path)
        res = cls(n_components=data['n_components'], interpolation_map=data['interpolation_map'])
        res.pca = data['pca']
        res.fill_values = data['fill_values']
        return res

    def fit(self, thickness_maps: np.ndarray):
        self.fill_values = np.nanmean(thickness_maps, axis=0)
        filled = np.where(np.isnan(thickness_maps), self.fill_values, thickness_maps)
        self.pca.fit(filled)

    def transform_from_map(self, thickness_map: np.ndarray, laterality: str, resolution_mm: tuple[float, float], center: tuple[int, int] = None) -> np.ndarray:
        interpolated = self.interpolation_map.interpolate(thickness_map, laterality, resolution_mm, center)
        interp_array = np.array([interpolated])
        return self.pca.transform(interp_array)

    def transform(self, thickness_map: np.ndarray):
        thickness_filled = np.where(np.isnan(thickness_map), self.fill_values, thickness_map)
        return self.pca.transform(thickness_filled)
    
    def get_reconstruction_error(self, thickness_map: np.ndarray, laterality: str, resolution_mm: tuple[float, float], center: tuple[int, int] = None) -> dict[str, float]:
        interpolated = self.interpolation_map.interpolate(thickness_map, laterality, resolution_mm, center)
        interp_array = np.array([interpolated])
        reconstructed = self.pca.inverse_transform(self.transform(interp_array))
        error_map = (interp_array - reconstructed)**2
        return error_map[0], reconstructed[0]
    
    def reconstruct(self, thickness_map: np.ndarray) -> np.ndarray:
        return self.pca.inverse_transform(self.pca.transform(thickness_map))
    
    def plot_components(self, **kwargs):
        fig, axes = plt.subplots(self.n_components, 1,figsize=(3, 3*self.n_components))
        for i, component in enumerate(self.pca.components_):
            self.interpolation_map.plot_with_values(component, ax=axes[i], **kwargs)
        return fig, axes
    
    def plot_reconstruction_error(self, error_map: np.ndarray, ax=None, **kwargs):
        fig, ax = self.interpolation_map.plot_with_values(error_map, ax=ax, **kwargs)
        return fig, ax



    