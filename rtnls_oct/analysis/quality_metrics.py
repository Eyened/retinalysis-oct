import numpy as np

def get_thickness_fluctuation_map(thickness_map: np.ndarray) -> np.ndarray:
    diff_y = np.gradient(thickness_map, axis=0)
    return np.abs(diff_y)


def thickness_fluctuation_across_scanlines(thickness_map: np.ndarray, masks: dict[str, np.ndarray]= None) -> dict[str, float]:
    diff_y = get_thickness_fluctuation_map(thickness_map)
    results = {
        'image_mean': np.mean(diff_y),
    }
    if masks is not None:
        for name, mask in masks.items():
            results[name] = np.mean(diff_y[mask])
    return results
