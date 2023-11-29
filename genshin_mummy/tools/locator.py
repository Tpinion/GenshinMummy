import logging
import pickle
from pathlib import Path
from typing import Optional, Tuple

import attrs
import cv2
import numpy as np
import pyautogui
from PIL.Image import Image as PILImage

from genshin_mummy.type import Box

logger = logging.getLogger(__name__)
logger.setLevel('NOTSET')

KEY_TO_PATH = {
    'exit_icon': '../materials/menu_page/exit_icon.jpg',
    'inventory_icon': '../materials/menu_page/inventory_icon.jpg',
    'artifact_icon': '../materials/inventory/artifact_icon.jpg',
    'weapon_icon': '../materials/inventory/weapon_icon.jpg',
    'lock_icon': '../materials/inventory/locked_icon.jpg',
    'unlock_icon': '../materials/inventory/unlocked_icon.jpg',
}

ICON_MATCHING_THRES = 0.8


def do_sift(image_or_path):
    if isinstance(image_or_path, str):
        src_image = cv2.imread(image_or_path)
        gray = cv2.cvtColor(src_image, cv2.COLOR_BGR2GRAY)
    elif isinstance(image_or_path, PILImage):
        src_image = np.array(image_or_path, dtype=np.uint8)
        gray = cv2.cvtColor(src_image, cv2.COLOR_RGB2GRAY)
    else:
        raise NotImplementedError()
    # 用线条特征规避图标被选中时的反色影响。
    canny = cv2.Canny(gray, cv2.THRESH_OTSU, 50, 200)
    sift = cv2.SIFT_create()
    kps, descriptors = sift.detectAndCompute(canny, None)
    return src_image, kps, descriptors


def load_descriptors(image_path):
    image_fp = Path(image_path)
    descriptors_fp = image_fp.parent / f"{image_fp.stem}.pkl"
    if descriptors_fp.exists():
        with open(descriptors_fp, 'rb') as fout:
            descriptors = pickle.load(fout)
        return descriptors
    return None


def locateOnScreen(
    image_path,
    confidence,
    grayscale: bool = True,
    debug: bool = False,
):
    src_des = load_descriptors(image_path)
    if src_des is None:
        _, _, src_des = do_sift(image_path)
        image_fp = Path(image_path)
        des_fp = image_fp.parent / f"{image_fp.stem}.pkl"
        with open(des_fp, 'wb') as fin:
            pickle.dump(src_des, fin)

    screen = pyautogui.screenshot()
    dst_im, dst_kps, dst_des = do_sift(screen)

    bf = cv2.BFMatcher()
    matches = bf.knnMatch(src_des, dst_des, k=2)

    reliable_matches = []
    reliable_points = []
    for src_match, dst_match in matches:
        if src_match.distance > 0.8 * dst_match.distance:
            continue
        reliable_matches.append([src_match])
        dst_keypoint = dst_kps[src_match.trainIdx]
        reliable_points.append(dst_keypoint.pt)

    if len(reliable_points) < 3:
        print('Match Failed.')
        return None

    # TODO: PCA and classify
    reliable_points = np.asarray(reliable_points)
    min_x, min_y = np.min(reliable_points, axis=0)
    max_x, max_y = np.max(reliable_points, axis=0)
    bbox = Box(left=min_x,
               top=min_y,
               width=min(1, max_x - min_x),
               height=max(1, max_y - min_y))

    if debug:
        src_im, src_kps, src_des = do_sift(image_path)
        dst_im = cv2.cvtColor(dst_im, cv2.COLOR_RGB2BGR)
        debug_image = cv2.drawMatchesKnn(
            src_im,
            src_kps,
            dst_im,
            dst_kps,
            reliable_matches,
            None,
            flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS,
        )
        cv2.imshow('IMG', debug_image)
        cv2.waitKey(0)
    return bbox.to_tuple()


def locate(key, extension_mode: bool = False):
    image_path = KEY_TO_PATH[key]
    if extension_mode:
        logger.info(f'locate {key} by sift')
        location = locateOnScreen(
            image_path,
            confidence=ICON_MATCHING_THRES,
            grayscale=True,
        )
    else:
        logger.info(f'locate {key} by pyautogui')
        location = pyautogui.locateOnScreen(
            image_path,
            confidence=ICON_MATCHING_THRES,
            grayscale=True,
        )
    if location:
        return pyautogui.center(location)
    return None


def is_menu_page(extension_mode: bool = False):
    center_point = locate('exit_icon')
    print(center_point)
    return True if center_point else False


@attrs.define
class InventoryLocator:
    image: PILImage = attrs.field()
    weapon_icon_pos: Optional[Tuple[int, int]] = attrs.field(init=False)
    artifact_icon_pos: Optional[Tuple[int, int]] = attrs.field(init=False)
    development_items_icon_pos: Optional[Tuple[int,
                                               int]] = attrs.field(init=False)
    food_icon_pos: Optional[Tuple[int, int]] = attrs.field(default=None)
    materials_icon_pos: Optional[Tuple[int, int]] = attrs.field(default=None)
    gadget_icon_pos: Optional[Tuple[int, int]] = attrs.field(default=None)
    quest_icon_pos: Optional[Tuple[int, int]] = attrs.field(default=None)
    previous_items_icon_pos: Optional[Tuple[int,
                                            int]] = attrs.field(default=None)
    furnishings_icon_pos: Optional[Tuple[int, int]] = attrs.field(default=None)

    def __init__(self):
        pass
