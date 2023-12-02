import time
from typing import List, Optional, Tuple

import attrs
import cv2
import numpy as np
import pyautogui

from genshin_mummy.opt import (
    diff_two_images,
    ensure_mouse_in_safe_location,
    locate_roi_location_from_diffs,
)
from genshin_mummy.type import Box, Direction, Point
from genshin_mummy.tools.logger import ExLogger, ScreenHandler


@attrs.define
class ArtifactPage:
    logger: ExLogger = attrs.field()

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
            height=self.screen_height * self.rough_desc_loc_ratio[3],
        )
        self.rough_list_loc = Box(
            left=self.screen_width * self.rough_list_loc_ratio[0],
            top=self.screen_height * self.rough_list_loc_ratio[1],
            width=self.screen_width * self.rough_list_loc_ratio[2],
            height=self.screen_height * self.rough_list_loc_ratio[3],
        )

        self.locate_artifact_description()
        self.locate_artifact_list()

        # 标定前不要添加屏幕日志，不然影响CV的差分算法
        self.logger.addHandler(ScreenHandler())

        # TODO: 双向校验圣遗物列表区域和描述区域的坐标位置准确性
        self.first_artifact_loc = self.locate_selected_artifact()
        self.logger.show_bbox(self.first_artifact_loc, '首行首个圣遗物')
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
            self.logger.show_bbox(down_artifact_loc, '次行圣遗物')
            self.y_offset = down_artifact_loc.center_y - self.first_artifact_loc.center_y  # noqa
        else:
            # TODO
            self.logger.warning('圣遗物行间距标定一样！这可能导致换行错误。')
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
            self.logger.info(f'圣遗物列间距：{str(x_offsets)}')
            self.x_offset = int(sum(x_offsets) / len(x_offsets))
        else:
            # TODO
            self.logger.warning('首行圣遗物的X轴坐标标定异常！')
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
            ensure_mouse_in_safe_location(
                loc=self.rough_list_loc,
                duration=self.mouse_move_time,
                use_box_center=True,
            )

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
        self.logger.info('正在移动圣遗物列表页至顶...')
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
                self.logger.info(f'当前圣遗物：{str(loc.to_tuple())}')
                if row_head_loc:
                    self.logger.info(f'下一行：{str(row_head_loc.to_tuple())}')
                else:
                    self.logger.warning('未能正确定位出下一行圣遗物。')
            else:
                row_head_loc = None

            reach_end = False
            while row_head_loc is None:
                self.logger.info('超过圣遗物列表区域，开始滚动下移...')
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
                self.logger.info('已到达圣遗物列表底部，结束当前任务。')
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
        self.logger.info('正在标定圣遗物详情区...')
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
        else:
            self.logger.show_bbox(roi, '圣遗物详情区')
        self.desc_loc = roi
        self.desc_loc_mask = self.generate_roi_mask(roi)

    def locate_artifact_list(self):
        self.logger.info('正在标定圣遗物列表区...')
        self.move_to_artifact_list()
        prev_screen = pyautogui.screenshot()
        reach_end = self.scroll_artifact_list(
            direction=Direction.DOWN,
            times=1,
            only_scrolling=False,
        )
        after_screen = pyautogui.screenshot()
        self.scroll_artifact_list(direction=Direction.UP, times=3)
        diffs = diff_two_images(prev_screen, after_screen)

        roi = locate_roi_location_from_diffs(diffs, self.diff_thres_ratio)
        self.logger.show_bbox(roi, '圣遗物列表区')

        if roi and not reach_end:
            self.list_loc = roi
        elif roi and reach_end:
            # TODO:
            raise NotImplementedError()
        else:
            # TODO:
            raise NotImplementedError()

        self.list_loc_mask = self.generate_roi_mask(roi)

    def locate_selected_artifact(self, delay: float = 0):
        # 基于被选中圣遗物有闪烁效果，获取选中圣遗物外边框
        self.logger.info('正在定位当前选中的圣遗物...')
        prev_screen = pyautogui.screenshot()
        prev_screen = np.asarray(prev_screen)
        if delay > 0:
            time.sleep(delay)
        after_screen = pyautogui.screenshot()
        after_screen = np.asarray(after_screen)
        diffs = diff_two_images(prev_screen, after_screen)
        diffs = cv2.bitwise_and(diffs, diffs, mask=self.list_loc_mask)
        diffs = cv2.morphologyEx(diffs, cv2.MORPH_OPEN, kernel=(3, 3))
        x, y, w, h = cv2.boundingRect(diffs)

        if x + y + w + h == 0:
            # 可能是CPU性能过好，导致前后两次截图时差过小，未能得到差分图
            return self.locate_selected_artifact(delay=0.1)
        else:
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
        self.logger.warning(f"目标点{aim_point} 不在 {selected_loc.to_tuple()}中！")
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
