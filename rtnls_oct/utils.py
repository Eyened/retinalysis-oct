import numpy as np
from scipy.ndimage import gaussian_filter
from scipy.ndimage import label
from typing import Tuple

def get_etdrs_grid_on_image(image_shape: tuple[int], resolution_mm: tuple[float], laterality, direction_bscan="Right", axial_direction="Down", center=None) -> dict:
        if center is None:
            print("No fovea location provided, using image center")
            center = [image_shape[0] // 2, image_shape[1] // 2]
        if not laterality in ['L', 'R']:
            raise ValueError(f"Invalid laterality: {laterality}. Must be 'L' or 'R'.")
        if not (direction_bscan in ['Left', 'Right'] and axial_direction in ['Up', 'Down']) or\
                (direction_bscan in ['Up', 'Down'] and axial_direction in ['Left', 'Right']):
            raise ValueError(f"Invalid direction_bscan or axial_direction: {direction_bscan}, {axial_direction}. Must be a combination of 'Left'/'Right' and 'Up'/'Down'.")
        
        dx, dy = np.meshgrid(range(image_shape[1]), range(image_shape[0]))
        distance_y = (center[0] - dy) * resolution_mm[0]
        distance_x = (center[1] - dx) * resolution_mm[1]
        return get_etdrs_fields(distance_x, distance_y, laterality=laterality, direction_x=direction_bscan, direction_y=axial_direction)

def get_etdrs_fields(x_locs_mm: np.ndarray, y_locs_mm: np.ndarray,
                     laterality: str,
                     direction_x: str='Right', 
                     direction_y: str='Down'):
    if not (direction_x in ['Left', 'Right'] and direction_y in ['Up', 'Down']) or\
                (direction_x in ['Up', 'Down'] and direction_y in ['Left', 'Right']):
            raise ValueError(f"Invalid direction_x or direction_y: {direction_x}, {direction_y}. Must be a combination of 'Left'/'Right' and 'Up'/'Down'.")
    
    if not laterality in ['L', 'R']:
        raise ValueError(f"Invalid laterality: {laterality}. Must be 'L' or 'R'.")
    distance_radial = np.sqrt(x_locs_mm**2 + y_locs_mm**2)
    th = np.arctan2(y_locs_mm, x_locs_mm) / (2 * np.pi)

    top = (1/8 < th) & (th <= 3/8)
    right = (3/8 < th) | (th <= -3/8)
    bottom = (- 3/8 < th) & (th <= -1/8)
    left = (-1/8 < th) & (th <= 1/8)
    central_circle = distance_radial < 0.5
    inner = (distance_radial > 0.5) * (distance_radial <= 1.5)
    outer = (distance_radial > 1.5) * (distance_radial <= 3)
    full = (distance_radial <= 3)

    fields = {
        'C0': central_circle,
        'GRID': full
    }

    rings = {
        '1': inner,
        '2': outer
    }

    quadrants = {}
    if direction_x == 'Up':
        quadrants['I'] = left
        quadrants['S'] = right
    elif direction_x == 'Down':
        quadrants['I'] = right
        quadrants['S'] = left
    elif (direction_x == 'Left' and laterality == 'R') or\
            (direction_x == 'Right' and laterality == 'L'):
        quadrants['T'] = right
        quadrants['N'] = left
    elif (direction_x == 'Right' and laterality == 'R') or\
            (direction_x == 'Left' and laterality == 'L'):
        quadrants['N'] = right
        quadrants['T'] = left

    if direction_y == 'Up':
        quadrants['S'] = bottom
        quadrants['I'] = top
    elif direction_y == 'Down':
        quadrants['S'] = top
        quadrants['I'] = bottom
    elif (direction_y == 'Left' and laterality == 'R') or\
            (direction_y == 'Right' and laterality == 'L'):
        quadrants['T'] = bottom
        quadrants['N'] = top
    elif (direction_y == 'Right' and laterality == 'R') or\
            (direction_y == 'Left' and laterality == 'L'):
        quadrants['T'] = top
        quadrants['N'] = bottom

    for name, mask in rings.items():
        for quadrant_name in ['S', 'I', 'N', 'T']:
            fields[f'{quadrant_name}{name}'] = quadrants[quadrant_name] * mask

    return fields


def find_fovea(height_map: np.ndarray, res_depth_mm, res_width_mm, exclude_mask=None) -> Tuple[int,int]:
    height_map = height_map.astype(np.float64)
    height_map[height_map < 0] = 0 ## filter out missing data
    blurred = gaussian_filter(height_map, sigma=[0.1/res_depth_mm, 0.1/res_width_mm])
    ## Find derivatives
    first_derivative_x = np.gradient(blurred)[0]
    second_derivative_x = np.gradient(first_derivative_x)[0]
    first_derivative_y = np.gradient(blurred)[1]
    second_derivative_y = np.gradient(first_derivative_y)[1]
    second_derivative = second_derivative_x + second_derivative_y
    
    ## mask ROI
    roi = np.zeros(height_map.shape)
    if exclude_mask is not None:
        roi[exclude_mask > 0] = 1
    roi[height_map == 0] = 1
    masked_second_derivative = np.ma.masked_array(second_derivative, mask=roi)
    
    ## select based on threshold
    select_second_derivative = masked_second_derivative > np.nanquantile(second_derivative[roi==0], 0.97)
    selection = select_second_derivative
    selection[roi > 0] = 0
    if np.sum(selection) == 0:
        return (0,0)

    ## find largest CC
    labels, _ = label(selection)
    largest_cc = labels == np.argmax(np.bincount(labels[selection]))
    center = [np.average(indices) for indices in np.where(largest_cc > 0)]
    
    return tuple(center)
