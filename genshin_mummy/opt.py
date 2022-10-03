from typing import Union

import numpy as np
import pyautogui
from PIL.Image import Image as PILImage

from .type import Box, Point


def ensure_mouse_in_safe_location(
    loc: Union[Box, Point],
    duration: float = 0.2,
    use_box_center: bool = False,
):
    x, y = pyautogui.position()
    if isinstance(loc, Box):
        if use_box_center:
            pyautogui.moveTo(loc.center_x, loc.center_y, duration)
            return
        safety_ratio = 0.1
        safety_offset = 5
        hori_safety_offset = min(int(loc.width * safety_ratio), safety_offset)
        vert_safety_offset = min(int(loc.height * safety_ratio), safety_offset)
        left = loc.left + hori_safety_offset
        right = loc.right - hori_safety_offset
        top = loc.top + vert_safety_offset
        bottom = loc.bottom - vert_safety_offset
        if left < x < right and top < y < bottom:
            return
        pyautogui.moveTo(loc.center_x, loc.center_y, duration)
    elif isinstance(loc, Point):
        if loc.x != x or loc.y != y:
            pyautogui.moveTo(loc.x, loc.y, duration)
    else:
        raise NotImplementedError()


def diff_two_images(
    im1: Union[np.ndarray, PILImage],
    im2: Union[np.ndarray, PILImage],
):
    if isinstance(im1, PILImage):
        im1 = np.asarray(im1)
    if isinstance(im2, PILImage):
        im2 = np.asarray(im2)
    assert im1.shape == im2.shape
    diff = np.sum(im1 - im2, axis=-1)
    mask = np.full(im1.shape[:2], 255, dtype=np.uint8)
    mask[diff == 0] = 0
    return mask


def locate_roi_location_from_diffs(
    diffs: np.ndarray,
    diff_thres_ratio: float,
):
    row_num, col_num = diffs.shape[0], diffs.shape[1]

    col_diff_thres = diff_thres_ratio * col_num
    col_diffs = np.count_nonzero(diffs, axis=0)
    roi_left = None
    for i, col_diff in enumerate(col_diffs):
        if col_diff > col_diff_thres:
            roi_left = i
            break
    if roi_left is None:
        return None

    roi_right = None
    for i, col_diff in enumerate(col_diffs[::-1]):
        if col_diff > col_diff_thres:
            roi_right = col_num - i
            break
    if roi_right is None:
        return None

    row_diff_thres = diff_thres_ratio * row_num
    row_diffs = np.count_nonzero(diffs, axis=1)
    roi_top = None
    for i, row_diff in enumerate(row_diffs):
        if row_diff > row_diff_thres:
            roi_top = i
            break
    if roi_top is None:
        return None

    roi_bottom = None
    for i, row_diff in enumerate(row_diffs[::-1]):
        if row_diff > row_diff_thres:
            roi_bottom = row_num - i
            break
    if roi_bottom is None:
        return None

    roi_loc = Box(
        left=roi_left,
        top=roi_top,
        width=roi_right - roi_left,
        height=roi_bottom - roi_top,
    )
    return roi_loc
