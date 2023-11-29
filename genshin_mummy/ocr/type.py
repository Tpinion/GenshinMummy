import re
from collections import defaultdict
from difflib import SequenceMatcher
from enum import Enum, unique
from typing import DefaultDict, List, Optional, Sequence

import attrs
from genshin_mummy.type import Box, Direction


@attrs.define
class TextChunk(Box):
    text: str = attrs.field()

    left_text_chunk: Optional['TextChunk'] = attrs.field(default=None)
    right_text_chunk: Optional['TextChunk'] = attrs.field(default=None)
    top_text_chunk: Optional['TextChunk'] = attrs.field(default=None)
    bottom_text_chunk: Optional['TextChunk'] = attrs.field(default=None)


@attrs.define
class TextChunkCollection:
    text_chunks: Sequence[TextChunk] = attrs.field()
    top_sorted_text_chunks: DefaultDict[str, List[TextChunk]] = attrs.field(
        init=False)
    text_to_text_chunks: DefaultDict[str,
                                     List[TextChunk]] = attrs.field(init=False)

    def __attrs_post_init__(self):
        self.text_to_text_chunks = defaultdict(list)
        for ck in self.text_chunks:
            self.text_to_text_chunks[ck.text].append(ck)
        top_sorted_chunks = sorted(self.text_chunks, key=lambda ck: ck.top)
        self.top_sorted_text_chunks = top_sorted_chunks
        for outer_idx, outer_ck in enumerate(top_sorted_chunks):
            for inner_idx, inner_ck in enumerate(top_sorted_chunks):
                if inner_idx <= outer_idx:
                    continue
                overlap = outer_ck.horizontal_edge_overlap(inner_ck)
                if overlap > 0:
                    outer_ck.bottom_text_chunk = inner_ck
                    inner_ck.top_text_chunk = outer_ck
                    break
        for outer_idx, outer_ck in enumerate(top_sorted_chunks[::-1]):
            if outer_ck.top_text_chunk:
                continue
            for inner_idx, inner_ck in enumerate(top_sorted_chunks[::-1]):
                if inner_idx <= outer_idx:
                    continue
                overlap = outer_ck.horizontal_edge_overlap(inner_ck)
                if overlap > 0:
                    outer_ck.top_text_chunk = inner_ck
                    if inner_ck.bottom_text_chunk is None:
                        inner_ck.bottom_text_chunk = outer_ck

    def find(self, text: str, conf: Optional[float] = None):
        if text in self.text_to_text_chunks:
            return self.text_to_text_chunks[text]
        elif conf:
            matched_chunks: List[TextChunk] = []
            for key, chunks in self.text_to_text_chunks.items():
                matcher = SequenceMatcher(a=text, b=key)
                if matcher.ratio() > conf:
                    matched_chunks.extend(chunks)
            matched_chunks.sort(key=lambda ck: ck.top)
            return matched_chunks
        return []

    def find_pattern(self, pattern: str):
        matched_chunks: List[TextChunk] = []
        for text, chunks in self.text_to_text_chunks.items():
            result = re.match(pattern, text)
            if result and result.group():
                matched_chunks.extend(chunks)
        matched_chunks.sort(key=lambda ck: ck.top)
        return matched_chunks

    def find_startswith(self, prefix: str):
        matched_chunks: List[TextChunk] = []
        for text, chunks in self.text_to_text_chunks.items():
            if text.startswith(prefix):
                matched_chunks.extend(chunks)
        matched_chunks.sort(key=lambda ck: ck.top)
        return matched_chunks

    def find_by_index(self, direction: Direction, idx: int):
        if direction == Direction.VERT:
            return self.top_sorted_text_chunks[idx]
        raise NotImplementedError()


def build_text_chunks_from_paddle_ocr(ocr_items):
    text_chunks = []
    # NOTE: 结构变了，暂时不太明白为什么多了一级，暂时先简单处理下
    # TODO：定义下结构，对PADDLE结果结构校验下
    ocr_items = ocr_items[0]
    for box_item, text_item in ocr_items:
        left = (box_item[0][0] + box_item[3][0]) // 2
        top = (box_item[0][1] + box_item[1][1]) // 2
        right = (box_item[1][0] + box_item[2][0]) // 2
        bottom = (box_item[2][1] + box_item[3][1]) // 2
        text = text_item[0]
        text_chunks.append(
            TextChunk(left, top, right - left, bottom - top, text))
    return text_chunks


@unique
class Alignment(Enum):
    LEFT = 'left'
    CENTER = 'center'
    RIGHT = 'right'
    UNKNOWN = 'unkown'
