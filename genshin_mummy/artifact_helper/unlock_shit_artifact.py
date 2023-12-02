import ctypes
import os
import platform
import time
from datetime import datetime
from pathlib import Path
from typing import List

import cv2
import iolite
import numpy as np
import pyautogui
from paddleocr import PaddleOCR

from genshin_mummy.artifact_helper.page_manager import ArtifactPage
from genshin_mummy.artifact_helper.judge import ArtifactJudge, Conclusion
from genshin_mummy.artifact_helper.type import (
    Artifact,
    ArtifactType,
    EntryType,
)
from genshin_mummy.ocr.opt import are_text_chunks_aligned_vertically
from genshin_mummy.ocr.type import (
    Alignment,
    TextChunk,
    TextChunkCollection,
    build_text_chunks_from_paddle_ocr,
)
from genshin_mummy.tools.logger import create_logger
from genshin_mummy.type import Box, Direction, Point

# TODO: 视PADDLE OCR结果可能要归一化
SPACE_CHAR = ' '
STAR_CHAR = '★'
PLUS_CHAR = '+'
DOT_CHAR = '·'
PERCENT_CHAR = '%'
SUBENTRY_PATTERN = f'{DOT_CHAR}.*?\{PLUS_CHAR}[\d.]*[{PERCENT_CHAR}]?'  # noqa


def get_entry_type(entry_key: str, entry_value: str):
    entry_type = None
    if entry_value.endswith(PERCENT_CHAR):
        if entry_key == EntryType.HP.value:
            entry_type = EntryType.HP_PERCENTAGE
        if entry_key == EntryType.ATK.value:
            entry_type = EntryType.ATK_PERCENTAGE
        if entry_key == EntryType.DEF.value:
            entry_type = EntryType.DEF_PERCENTAGE

    if entry_type is None:
        for cand_entry_type in EntryType:
            if entry_key == cand_entry_type.value:
                entry_type = cand_entry_type
                break
        # TODO: 近似匹配
    return entry_type


def recognize_artifact_informations(ocr, screen: np.ndarray):
    # TODO: 移到ArtifactDescription里去

    # 移除显著游离余左对齐的文本，规避OCR噪声字符
    sigma = 3
    ocr_items = ocr.ocr(screen, cls=False)
    text_chunks = build_text_chunks_from_paddle_ocr(ocr_items)
    lefts = [tc.left for tc in text_chunks]
    left_std = np.std(lefts)
    left_mean = np.mean(lefts)
    valid_text_chunks = []
    for chunk in text_chunks:
        if abs(chunk.left - left_mean) > sigma * left_std:
            continue
        valid_text_chunks.append(chunk)
    # if not valid_text_chunks:
    #     cv2.imshow('img', screen)
    #     cv2.waitKey(0)
    #     breakpoint()
    chunk_clct = TextChunkCollection(valid_text_chunks)

    _chunks = []
    for artifact_type in ArtifactType:
        _chunks = chunk_clct.find(artifact_type.value, conf=0.65)
        break
    if _chunks:
        type_chunk = _chunks[0]
    else:
        type_chunk = chunk_clct.find_by_index(direction=Direction.VERT, idx=1)

    name_chunk = type_chunk.top_text_chunk

    entry_chunk = type_chunk.bottom_text_chunk
    entry_value_chunk = entry_chunk.bottom_text_chunk
    stars_chunk = entry_value_chunk.bottom_text_chunk

    if not stars_chunk.text.startswith(STAR_CHAR):
        _chunks = chunk_clct.find_startswith(STAR_CHAR)
        stars_chunk = _chunks[0]

    level_chunk = stars_chunk.bottom_text_chunk
    if level_chunk.text.startswith(PLUS_CHAR):
        _chunks = chunk_clct.find_startswith(PLUS_CHAR)
        level_chunk = _chunks[0]

    subentry_chunks: List[TextChunk] = []
    subentry_chunk = level_chunk.bottom_text_chunk
    while True:
        if subentry_chunk.text.startswith(DOT_CHAR):
            subentry_chunks.append(subentry_chunk)
        else:
            break
        subentry_chunk = subentry_chunk.bottom_text_chunk

    if len(subentry_chunks) > 5 or not are_text_chunks_aligned_vertically(
            subentry_chunks, Alignment.LEFT):
        subentry_chunks = chunk_clct.find_pattern(SUBENTRY_PATTERN)
        # TODO: 校验值正确性，若不正确切换模板策略抽取

    entry_type = get_entry_type(entry_chunk.text, entry_value_chunk.text)

    # TODO
    assert entry_type

    subentries = {}
    for chunk in subentry_chunks:
        # TODO: 想办法规避下OCR稳定性影响, 目前好像没问题
        text = chunk.text.strip(f'{DOT_CHAR}{SPACE_CHAR}')
        subentry_key, subentry_value = text.split(PLUS_CHAR)
        subentry_type = get_entry_type(subentry_key, subentry_value)
        subentries[subentry_type] = subentry_value

    artifact_type = None
    for _item in ArtifactType:
        if _item.value == type_chunk.text:
            artifact_type = _item
            break
    assert artifact_type

    artifact = Artifact(
        name=name_chunk.text,
        type=artifact_type,
        entry={entry_type: entry_value_chunk.text},
        stars=stars_chunk.text.count(STAR_CHAR),
        level=int(level_chunk.text.lstrip(PLUS_CHAR)),
        subentries=subentries,
    )
    assert isinstance(level_chunk, TextChunk)
    return artifact, level_chunk


def locate_lock_icon(
    top_limit: int,
    bottom_limit: int,
    left_limit: int,
    screen: np.ndarray,
    desc_loc_mask: np.ndarray,
):
    desc_loc_mask[:, :left_limit] = 0
    desc_loc_mask[:top_limit, :] = 0
    desc_loc_mask[bottom_limit:, :] = 0
    gray = cv2.cvtColor(screen, cv2.COLOR_RGB2GRAY)
    thres = cv2.adaptiveThreshold(
        src=gray,
        maxValue=255,
        adaptiveMethod=cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        thresholdType=cv2.THRESH_BINARY_INV,
        blockSize=11,
        C=2,
    )
    thres = cv2.bitwise_and(thres, thres, mask=desc_loc_mask)
    roi_left, roi_top, roi_width, roi_height = cv2.boundingRect(thres)
    center_point = Box(roi_left, roi_top, roi_width, roi_height)
    roi = screen[roi_top:roi_top + roi_height, roi_left:roi_left + roi_width]
    channel_red_roi = roi[:, :, 0]
    # TODO: 经验值有效但不太保险
    THRESH = 20
    if np.mean(channel_red_roi) - np.mean(roi[:, :, 1:]) > THRESH:
        lock_status = Conclusion.LOCK
    else:
        lock_status = Conclusion.UNLOCK
    center_point = Point(
        x=roi_left + roi_width // 2,
        y=roi_top + roi_height // 2,
    )
    return lock_status, center_point


def scan_strategy_file(app_folder: Path):
    for fp in app_folder.glob('*.xlsx'):
        return str(fp.resolve())
    return None


def run_pipeline(max_num: int, app_fd: str):
    app_folder = Path(app_fd)
    strategy_fp = scan_strategy_file(app_folder)

    logger_folder = app_folder / datetime.now().strftime('%Y%m%d_%H%M%S')
    logger_folder.mkdir(parents=True, exist_ok=True)

    artifact_infos = []

    logger = create_logger('unlock_those_shit', logger_folder)

    delay_seconds = 10
    logger.notify(
        message=f'你有{delay_seconds}秒钟的时间切换到圣遗物页面\n记得选择左上角圣遗物哦~',
        destory_ms=3000,
    )
    logger.notify_countdown(delay_seconds)

    ocr = PaddleOCR(use_angle_cls=False, lang="ch")

    artifact_page = ArtifactPage(logger=logger)
    artifact_judge = ArtifactJudge(config_fp=strategy_fp, logger=logger)

    try:
        for idx, _ in enumerate(artifact_page.iter_artifacts(max_num)):
            logger.info(f'正在处理第{idx + 1}个圣遗物...')
            screen = pyautogui.screenshot()
            screen = np.asarray(screen)
            screen = cv2.bitwise_and(
                screen,
                screen,
                mask=artifact_page.desc_loc_mask,
            )
            try:
                artifact, level_chunk = recognize_artifact_informations(
                    ocr,
                    screen,
                )
                logger.info(f'圣遗物信息：{str(artifact)}')
            except Exception as error:
                logger.error(f'识别圣遗物信息失败：{error}')
                continue

            expect_status = artifact_judge.judge(artifact)

            info = list(artifact.to_dict().values())
            padding_col = 9 - len(info)
            for _ in range(padding_col):
                info.append('')
            info.append(expect_status.value)
            artifact_infos.append(info)

            if expect_status == Conclusion.UNKNOWN:
                continue

            lock_status, icon_center = locate_lock_icon(
                top_limit=int(level_chunk.top),
                bottom_limit=int(level_chunk.bottom),
                left_limit=int(artifact_page.desc_loc.left +
                               artifact_page.desc_loc.width // 2),
                screen=screen,
                desc_loc_mask=artifact_page.desc_loc_mask.copy(),
            )

            logger.info(f'当前圣遗物状态为{lock_status}，期望为{expect_status}')
            if lock_status != expect_status:
                logger.info(f'前往坐标x={icon_center.x}，y={icon_center.y}调整锁定状态')
                pyautogui.leftClick(
                    icon_center.x,
                    icon_center.y,
                    duration=artifact_page.mouse_move_time,
                )

            artifact_page.move_to_artifact_list()
    except Exception as error:
        logger.error(f'意外结束程序：{error}')
    finally:
        if artifact_infos:
            headers = list(artifact.to_dict().keys())[:5]
            headers += [
                '副词条1',
                '副词条2',
                '副词条3',
                '副词条4',
                '当前是否锁',
            ]
            artifact_infos.insert(0, headers)
            iolite.write_csv_lines(
                logger_folder / 'artifacts.csv',
                artifact_infos,
                encoding='utf-8',
                newline='',
            )

            logger.info('当前页面圣遗物判断结束, 程序将在10秒后退出')


def main():
    app_folder = os.path.join(
        os.path.expanduser("~"),
        'Desktop',
        'GenshinMummy',
    )

    system = platform.system()
    is_admin = False

    if system == 'Windows':
        if ctypes.windll.shell32.IsUserAnAdmin():
            is_admin = True
    else:
        is_admin = os.getuid() == 0

    if is_admin:
        run_pipeline(1800, app_folder)
    else:
        print("需要管理员权限打开终端哦~")


if __name__ == '__main__':
    main()
