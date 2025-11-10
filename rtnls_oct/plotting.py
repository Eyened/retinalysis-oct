import matplotlib.pyplot as plt
import numpy as np

def plot_image(data: np.ndarray, ax=None, **kwargs):
    if ax is None:
        _, ax = plt.subplots()
    ax.imshow(data, aspect='auto', cmap='gray', **kwargs)
    ax.axis('off')
    return ax

def plot_thickness(data: np.ndarray, alpha=0.5, vmin=0, ax=None, **kwargs):
    if ax is None:
        _, ax = plt.subplots()
    ax.imshow(data, aspect='auto', alpha=alpha, cmap='jet', vmin=vmin, **kwargs)
    ax.axis('off')
    return ax

def plot_mask(data: np.ndarray, alpha=0.5, ax=None):    
    if ax is None:
        _, ax = plt.subplots()
    ax.imshow(data, aspect='auto', alpha=alpha*(data > 0), cmap='jet')
    ax.axis('off')
    return ax

def plot_enface(data: np.ndarray, ax=None):    
    enface = np.mean(data, axis=1)
    ax = plot_image(enface, ax=ax)

    return ax

def plot_grid_masks(masks: dict[str, np.ndarray], ax=None):
    if ax is None:
        fig, ax = plt.subplots()
    for name, mask in masks.items():
        ax.contour(mask, colors=['r'], linewidths=0.5)
        ys, xs = np.where(mask)
        if len(xs) > 0 and len(ys) > 0:
            x_center = xs.mean()
            y_center = ys.mean()
            ax.annotate(name, (x_center, y_center), color='red', ha='center', va='center', fontsize=5)