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

def plot_grid_masks(
    masks: dict[str, np.ndarray],
    ax=None,
    *,
    line_color: str = "r",
    label_color: str | None = None,
    linewidths: float = 0.5,
    show_labels: bool = True,
):
    """Draw ETDRS (or other) region outlines from boolean masks on the current image.

    Parameters
    ----------
    line_color
        Matplotlib color for contour lines (default red, matching previous behavior).
    label_color
        Color for region name annotations; defaults to ``line_color`` if ``show_labels``.
    linewidths
        Contour line width in points.
    show_labels
        If False, contours only (no region text).
    """
    if ax is None:
        _, ax = plt.subplots()
    if label_color is None:
        label_color = line_color
    for name, mask in masks.items():
        ax.contour(mask, colors=[line_color], linewidths=linewidths)
        if not show_labels:
            continue
        ys, xs = np.where(mask)
        if len(xs) > 0 and len(ys) > 0:
            x_center = xs.mean()
            y_center = ys.mean()
            ax.annotate(
                name,
                (x_center, y_center),
                color=label_color,
                ha="center",
                va="center",
                fontsize=5,
            )