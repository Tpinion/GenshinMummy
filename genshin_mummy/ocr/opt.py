from typing import Optional, Sequence

import numpy as np

from genshin_mummy.ocr.type import Alignment, TextChunk


def are_text_chunks_aligned_vertically(
    text_chunks: Sequence[TextChunk],
    alignment: Optional[Alignment] = None,
):
    if alignment == Alignment.LEFT:
        mean_left = np.mean([ck.left for ck in text_chunks])
        avg_char_width = np.mean(
            [ck.width / len(ck.text) for ck in text_chunks])
        for ck in text_chunks:
            if abs(ck.left - mean_left) > avg_char_width:
                return False
        return True
    else:
        raise NotImplementedError()
