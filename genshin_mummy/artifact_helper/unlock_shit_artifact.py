from typing import Optional

import cv2
import numpy as np
import pyautogui
import iolite
from paddleocr import PaddleOCR
from PIL import Image as PILImage


from genshin_mummy.artifact_helper.type import (
    Artifact,
    ArtifactPage,
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

from genshin_mummy.type import Box, Direction, Point
from genshin_mummy.tools.notifier import notify, notify_countdown


# TODO: 视PADDLE OCR结果可能要归一化
SPACE_CHAR = ' '
STAR_CHAR = '★'
PLUS_CHAR = '+'
DOT_CHAR = '·'
PERCENT_CHAR = '%'
SUBENTRY_PATTERN = f'{DOT_CHAR}.*?\{PLUS_CHAR}[\d.]*[{PERCENT_CHAR}]?'


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

    subentry_chunks = []
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


def whether_or_not_to_lock(artifact):
    # TODO: 抽象出策略类
    # 算法参考
    # https://www.bilibili.com/video/BV1sZ4y1e7h8/?spm_id_from=333.1007.top_right_bar_window_history.content.click
    # https://www.bilibili.com/video/BV1mB4y177a6/?spm_id_from=333.1007.top_right_bar_window_history.content.click

    # 等级大于0=>锁
    if artifact.level > 0:
        return True

    # 非五星=>不锁
    if artifact.stars < 5:
        return False

    # 沙、杯、帽主词条为类别独有词条=>锁
    if (artifact.type
            not in {ArtifactType.FLOWER_OF_LIFE, ArtifactType.PLUME_OF_DEATH}
            and list(artifact.entry.keys())[0] not in {
                EntryType.HP_PERCENTAGE, EntryType.ATK_PERCENTAGE,
                EntryType.DEF_PERCENTAGE
            }):
        return True

    # 双暴词条=>锁
    subentry_types = set(artifact.subentries.keys())
    if {EntryType.CRIT_DMG, EntryType.CRIT_RATE}.issubset(subentry_types):
        return True

    # 初始四词条 且不要存在所有小攻防命都有=>锁
    if len(subentry_types) == 4 and not {
            EntryType.HP, EntryType.ATK, EntryType.DEF
    }.issubset(subentry_types):
        return True

    # 小攻击、小防御、小生命大于等于两个=>不锁
    if len({EntryType.HP, EntryType.ATK, EntryType.DEF} & subentry_types) >= 2:
        return False

    return True


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
    THRESH = 30
    if np.mean(channel_red_roi) - np.mean(roi[:, :, 1:]) > THRESH:
        lock_status = True
    else:
        lock_status = False
    center_point = Point(
        x=roi_left + roi_width // 2,
        y=roi_top + roi_height // 2,
    )
    return lock_status, center_point


def run_pipeline(max_num: int, debug_root: Optional[str] = None):
    if debug_root:
        from pathlib import Path
        debug_root = Path(debug_root)
        debug_info = []
        notify(f'调试路径：{debug_root}')

    notify('你有10秒钟的时间切换到圣遗物页面，记得选择左上角圣遗物哦~')
    notify_countdown(10)

    ocr = PaddleOCR(use_angle_cls=False, lang="ch")
    artifact_page = ArtifactPage()

    for idx, _ in enumerate(artifact_page.iter_artifacts(max_num)):
        screen = pyautogui.screenshot()
        screen = np.asarray(screen)
        screen = cv2.bitwise_and(screen,
                                 screen,
                                 mask=artifact_page.desc_loc_mask)
        # PILImage.fromarray(screen).save(debug_root / f'{idx}_ocr.png')
        artifact, level_chunk = recognize_artifact_informations(ocr, screen)

        expect_status = whether_or_not_to_lock(artifact)
        lock_status, icon_center = locate_lock_icon(
            top_limit=int(level_chunk.top),
            bottom_limit=int(level_chunk.bottom),
            left_limit=int(artifact_page.desc_loc.left +
                           artifact_page.desc_loc.width // 2),
            screen=screen,
            desc_loc_mask=artifact_page.desc_loc_mask.copy(),
        )
        if debug_root:
            info = list(artifact.to_dict().values())
            padding_col = 9 - len(info)
            for _ in range(padding_col):
                info.append('')
            info.append(lock_status)
            debug_info.append(info)
        if lock_status != expect_status:
            pyautogui.leftClick(
                icon_center.x,
                icon_center.y,
                duration=artifact_page.mouse_move_time,
            )

        artifact_page.move_to_artifact_list()

    if debug_root and debug_info:
        headers = list(artifact.to_dict().keys())[:5]
        headers += [
            '副词条1',
            '副词条2',
            '副词条3',
            '副词条4',
            '当前是否锁',
        ]
        debug_info.insert(0, headers)
        iolite.write_csv_lines(
            debug_root / f'artifacts.csv',
            debug_info,
            encoding='utf-8',
            newline='',
        )


if __name__ == '__main__':
    run_pipeline(1600, './debug_folder')
