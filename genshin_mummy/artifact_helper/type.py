import time
from enum import Enum, unique
from typing import Dict, List, Optional, Tuple

import attrs
import cv2
import numpy as np
import pyautogui
from genshin_mummy.ocr.type import TextChunkCollection
from genshin_mummy.opt import (
    diff_two_images,
    ensure_mouse_in_safe_location,
    locate_roi_location_from_diffs,
)
from genshin_mummy.type import Box, Direction, Point


@unique
class EntryType(Enum):
    HP = '生命值'
    HP_PERCENTAGE = '生命值百分比'
    ATK = '攻击力'
    ATK_PERCENTAGE = '攻击力百分比'
    DEF = '防御力'
    DEF_PERCENTAGE = '防御力百分比'

    CRIT_DMG = '暴击伤害'
    CRIT_RATE = '暴击率'

    ELEMENTAL_MASTERY = '元素精通'
    ENERGY_RECHARGE = '元素充能效率'

    PYRO_DMG_BONUS = '火元素伤害加成'
    HYDRO_DMG_BONUS = '水元素伤害加成'
    CRYO_DMG_BONUS = '冰元素伤害加成'
    ELECTRO_DMG_BONUS = '雷元素伤害加成'
    DENDRO_DMG_BONUS = '草元素伤害加成'
    ANEMO_DMG_BONUS = '风元素伤害加成'
    GEO_DMG_BONUS = '岩元素伤害加成'
    PHYSICAL_DMG_BONUS = '物理伤害加成'
    HEALING_BONUS = '治疗加成'


@unique
class ArtifactType(Enum):
    FLOWER_OF_LIFE = '生之花'
    PLUME_OF_DEATH = '死之羽'
    SANDS_OF_EON = '时之沙'
    GOBLETS_OF_EONOTHEM = '空之杯'
    CERCLETS_OF_LOGOS = '理之冠'


@attrs.define
class Artifact:
    name: str = attrs.field()
    type: ArtifactType = attrs.field()
    entry: Dict[EntryType, str] = attrs.field()
    stars: int = attrs.field()
    level: int = attrs.field()
    subentries: Dict[EntryType, str] = attrs.field()

    def to_dict(self):
        main_entry_key, main_entry_value = list(self.entry.items())[0]
        result = {
            '圣遗物名称': self.name,
            '类型': self.type.value,
            '主词条': f'{main_entry_key.value}={main_entry_value}',
            '星级': self.stars,
            '等级': self.level,
        }
        for idx, (subentry_key, subentry_value) in enumerate(self.subentries.items(), start=1):
            result[f'副词条{idx}'] = f'{subentry_key.value}={subentry_value}'
        return result


@attrs.define
class ArtifactDescription:
    # TODO:
    image: np.ndarray = attrs.field()
    text_chunk_collection: TextChunkCollection = attrs.field()


@attrs.define
class ArtifactPage:
    mouse_move_time: float = attrs.field(default=0.2)
    rendering_time: float = attrs.field(default=0.5)
    scroll_steps: int = attrs.field(default=5)
    first_artifact_loc: Box = attrs.field(default=None)
    x_offset: Optional[int] = attrs.field(default=None)
    y_offset: Optional[int] = attrs.field(default=None)
    loc_iou_thres: float = attrs.field(default=0.1)
    diff_thres_ratio: float = attrs.field(default=0.1)

    screen_width: int = attrs.field(init=False)
    screen_height: int = attrs.field(init=False)
    screen_area: int = attrs.field(init=False)

    desc_loc: Box = attrs.field(init=False)
    list_loc: Box = attrs.field(init=False)
    list_loc_mask: np.ndarray = attrs.field(init=False)
    desc_loc_mask: np.ndarray = attrs.field(init=False)

    rough_list_loc_ratio: Tuple[float, float, float,
                                float] = attrs.field(default=(0.1, 0.17, 0.6,
                                                              0.7))
    rough_list_loc: Box = attrs.field(init=False)
    rough_desc_loc_ratio: Tuple[float, float, float,
                                float] = attrs.field(default=(0.68, 0.17, 0.26,
                                                              0.7))
    rough_desc_loc: Box = attrs.field(init=False)

    col_points: List[int] = attrs.field(init=False, factory=list)

    def __attrs_post_init__(self):
        # 需处于切换圣遗物页签后的初始状态
        self.screen_width, self.screen_height = pyautogui.size()
        self.screen_area = self.screen_height * self.screen_width
        self.rough_desc_loc = Box(
            left=self.screen_width * self.rough_desc_loc_ratio[0],
            top=self.screen_height * self.rough_desc_loc_ratio[1],
            width=self.screen_width * self.rough_desc_loc_ratio[2],
            height=self.screen_height * self.rough_desc_loc_ratio[3],)
        self.rough_list_loc = Box(
            left=self.screen_width * self.rough_list_loc_ratio[0],
            top=self.screen_height * self.rough_list_loc_ratio[1],
            width=self.screen_width * self.rough_list_loc_ratio[2],
            height=self.screen_height * self.rough_list_loc_ratio[3],)
        self.locate_artifact_list()
        self.locate_artifact_description()
        # TODO: 双向校验圣遗物列表区域和描述区域的坐标位置准确性
        self.first_artifact_loc = self.locate_selected_artifact()
        self.locate_artifact_rows_and_columns()

    def is_same_artifact(self, loc_a: Box, loc_b: Box):
        iou = loc_a.overlap(loc_b)
        return iou > self.loc_iou_thres

    def locate_artifact_rows_and_columns(self):
        down_artifact_loc = self.locate_next_artifact(
            self.first_artifact_loc,
            direction=Direction.DOWN,
        )
        if down_artifact_loc:
            self.y_offset = down_artifact_loc.center_y - self.first_artifact_loc.center_y
        else:
            # TODO
            pass

        prev_loc = self.first_artifact_loc
        self.col_points.append(prev_loc.center_x)
        x_offsets = []
        while prev_loc:
            next_loc = self.locate_next_artifact(
                prev_loc,
                direction=Direction.RIGHT,
            )
            if next_loc:
                self.col_points.append(next_loc.center_x)
                x_offsets.append(next_loc.center_x - prev_loc.center_x)
            prev_loc = next_loc
        if x_offsets:
            self.x_offset = int(sum(x_offsets) / len(x_offsets))
        else:
            # TODO
            pass

    def scroll(
        self,
        direction: Direction,
        clicks: int = 1,
        times: int = 1,
    ):
        if direction == Direction.UP:
            clicks = abs(clicks)
        elif direction == Direction.DOWN:
            clicks = -abs(clicks)
        else:
            raise NotImplementedError()
        for _ in range(self.scroll_steps * times):
            pyautogui.scroll(clicks)
        self.wait_rendering()

    def move_to_artifact_list(self):
        if getattr(self, 'list_loc', None):
            ensure_mouse_in_safe_location(
                loc=self.list_loc,
                duration=self.mouse_move_time,
            )
        else:
            ensure_mouse_in_safe_location(loc=self.rough_list_loc,
                                          duration=self.mouse_move_time,
                                          use_box_center=True)

    def _scroll_artifact_list(
        self,
        direction: Direction,
        times: int = 5,
        only_scrolling: bool = True,
    ):
        self.move_to_artifact_list()
        if only_scrolling:
            self.scroll(direction=direction, clicks=1, times=times)
            self.wait_rendering()
            return False
        prev_screen = pyautogui.screenshot()
        self.scroll(direction=direction, clicks=1, times=times)
        self.wait_rendering()
        next_screen = pyautogui.screenshot()
        diff = diff_two_images(prev_screen, next_screen)
        diff_num = np.count_nonzero(diff)
        return diff_num / self.screen_area < self.diff_thres_ratio

    def scroll_artifact_list(
        self,
        direction: Direction,
        times: int = 4,
        until_boundary: bool = False,
        only_scrolling: bool = True,
    ):
        if until_boundary:
            only_scrolling = False
            reach_boundary = False
            while not reach_boundary:
                reach_boundary = self._scroll_artifact_list(
                    direction=direction,
                    times=times,
                    only_scrolling=only_scrolling,
                )
                # TODO: if timeout return false
            return True
        else:
            reach_boundary = self._scroll_artifact_list(
                direction=direction,
                times=times,
                only_scrolling=only_scrolling,
            )
            return reach_boundary

    def iter_artifacts(self, max_num: Optional[int] = None):
        count = 0
        self.scroll_artifact_list(
            direction=Direction.UP,
            times=1,
            until_boundary=True,
        )

        row_head_loc = self.first_artifact_loc
        excced_max_num = False
        while True:
            for x in self.col_points:
                count += 1
                if max_num and count > max_num:
                    excced_max_num = True
                    break
                pyautogui.leftClick(x=x, y=row_head_loc.center_y)
                yield

            if excced_max_num:
                break
            
            loc = self.locate_selected_artifact()

            if loc.bottom + self.y_offset < self.list_loc.bottom:
                row_head_loc = self.locate_aim_artifact_based_on_point(
                    aim_x=self.col_points[0],
                    aim_y=loc.center_y + self.y_offset,
                )
            else:
                row_head_loc = None

            reach_end = False
            while row_head_loc is None:
                reach_end = self.scroll_artifact_list(
                    direction=Direction.DOWN,
                    only_scrolling=False,
                )
                if reach_end:
                    break
                loc = self.locate_selected_artifact()
                row_head_loc = self.locate_aim_artifact_based_on_point(
                    aim_x=self.col_points[0],
                    aim_y=loc.center_y + self.y_offset,
                )
            if reach_end:
                break

    def wait_rendering(self, count: int = 1):
        time.sleep(count * self.rendering_time)

    def generate_roi_mask(self, roi: Box):
        mask = np.zeros(
            shape=(self.screen_height, self.screen_width),
            dtype=np.uint8,
        )
        mask[roi.top:roi.bottom, roi.left:roi.right] = 255
        return mask

    def locate_artifact_description(self):
        ensure_mouse_in_safe_location(
            loc=self.rough_desc_loc,
            use_box_center=True,
        )
        clicks = 5
        prev_screen = pyautogui.screenshot()
        self.scroll(direction=Direction.DOWN, clicks=clicks)
        after_screen = pyautogui.screenshot()
        self.scroll(direction=Direction.UP, clicks=2 * clicks)
        diffs = diff_two_images(prev_screen, after_screen)
        # 左半侧存在选中圣遗物的闪烁区域，不属于ROI
        diffs[:, :diffs.shape[1] // 2] = 0

        roi = locate_roi_location_from_diffs(
            diffs,
            self.diff_thres_ratio,
        )
        if roi is None:
            # TODO:
            pass
        self.desc_loc = roi
        self.desc_loc_mask = self.generate_roi_mask(roi)

    def locate_artifact_list(self):
        self.move_to_artifact_list()
        prev_screen = pyautogui.screenshot()
        reach_end = self.scroll_artifact_list(
            direction=Direction.DOWN,
            times=1,
            only_scrolling=False,
        )
        after_screen = pyautogui.screenshot()
        self.scroll_artifact_list(direction=Direction.UP, times=2)
        diffs = diff_two_images(prev_screen, after_screen)

        roi = locate_roi_location_from_diffs(diffs, self.diff_thres_ratio)

        if roi and not reach_end:
            self.list_loc = roi
        elif roi and reach_end:
            # TODO:
            raise NotImplementedError()
        else:
            # TODO:
            raise NotImplementedError()

        self.list_loc_mask = self.generate_roi_mask(roi)

    def locate_selected_artifact(self):
        # 基于被选中圣遗物有闪烁效果，获取选中圣遗物外边框
        prev_screen = pyautogui.screenshot()
        prev_screen = np.asarray(prev_screen)
        after_screen = pyautogui.screenshot()
        after_screen = np.asarray(after_screen)
        diffs = diff_two_images(prev_screen, after_screen)
        diffs = cv2.bitwise_and(diffs, diffs, mask=self.list_loc_mask)
        diffs = cv2.morphologyEx(diffs, cv2.MORPH_OPEN, kernel=(3, 3))
        x, y, w, h = cv2.boundingRect(diffs)
        # TODO: resolve find noting
        artifact_loc = Box(left=x, top=y, width=w, height=h)
        return artifact_loc

    def locate_aim_artifact_based_on_point(
        self,
        aim_x: int,
        aim_y: int,
    ):
        aim_point = Point(x=aim_x, y=aim_y)
        pyautogui.leftClick(aim_point.x, aim_point.y)
        selected_loc = self.locate_selected_artifact()
        if selected_loc.contain(aim_point):
            return selected_loc
        return None

    def locate_next_artifact(
        self,
        basic_artifact_loc: Box,
        direction: Direction,
    ):
        if self.x_offset is None:
            x_offset = basic_artifact_loc.width
        else:
            x_offset = self.x_offset
        if self.y_offset is None:
            y_offset = basic_artifact_loc.height
        else:
            y_offset = self.y_offset

        aim_x = basic_artifact_loc.center_x
        aim_y = basic_artifact_loc.center_y
        if direction == Direction.LEFT:
            aim_x = max(aim_x - x_offset, self.list_loc.left)
        elif direction == Direction.RIGHT:
            aim_x = min(aim_x + x_offset, self.list_loc.right)
        elif direction == Direction.UP:
            aim_y = max(aim_y - y_offset, self.list_loc.top)
        elif direction == Direction.DOWN:
            aim_y = min(aim_y + y_offset, self.list_loc.bottom)
        else:
            raise NotImplementedError()

        pyautogui.leftClick(aim_x, aim_y)
        next_artifact_loc = self.locate_selected_artifact()
        if not self.is_same_artifact(
                loc_a=basic_artifact_loc,
                loc_b=next_artifact_loc,
        ):
            return next_artifact_loc
        return None


if __name__ == '__main__':
    import time
    time.sleep(5)
    artifact_page = ArtifactPage()
    for _ in artifact_page.iter_artifacts(max_num=10):
        pass
