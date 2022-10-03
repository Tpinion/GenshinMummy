from pyscreeze import (
    Box as ScreezeBox,
    Point as ScreezePoint,
)
import attrs
from enum import unique, Enum
from typing import Union


@unique
class Direction(Enum):
    UP = 'up'
    DOWN = 'down'
    LEFT = 'left'
    RIGHT = 'right'
    VERT = 'vert'
    HORI = 'hori'


Point = ScreezePoint


@attrs.define
class Box:
    left: int = attrs.field()
    top: int = attrs.field()
    width: int = attrs.field()
    height: int = attrs.field()

    @property
    def right(self):
        return self.left + self.width

    @property
    def bottom(self):
        return self.top + self.height

    @property
    def center_x(self):
        return self.left + self.width // 2

    @property
    def center_y(self):
        return self.top + self.height // 2

    @property
    def center(self):
        return (self.center_x, self.center_y)

    @property
    def area(self):
        return self.width * self.height

    def overlap(self, other_box: 'Box'):
        vert_overlap = self.vertical_edge_overlap(other_box)
        hori_overlap = self.horizontal_edge_overlap(other_box)
        overlap_area = hori_overlap * vert_overlap
        union_area = self.area + other_box.area - overlap_area
        iou = overlap_area / union_area
        assert 0 <= iou <= 1
        return iou

    def horizontal_edge_overlap(self, other_box: 'Box'):
        hori_overlap = max(
            min(self.right, other_box.right) - max(self.left, other_box.left),
            0,
        )
        return hori_overlap

    def vertical_edge_overlap(self, other_box: 'Box'):
        vert_overlap = max(
            min(self.bottom, other_box.bottom) - max(self.top, other_box.top),
            0,
        )
        return vert_overlap

    def contain(self, ob: Union['Box', Point]):
        if isinstance(ob, Box):
            return (ob.left > self.left and ob.right < self.right
                    and ob.top > self.top and ob.bottom < self.bottom)
        elif isinstance(ob, Point):
            return (self.left < ob.x < self.right
                    and self.top < ob.y < self.bottom)
        else:
            raise NotImplementedError()

    def to_tuple(self):
        return ScreezeBox(self.left, self.top, self.width, self.height)
