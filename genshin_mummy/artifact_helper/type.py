from enum import Enum, unique
from typing import Dict

import attrs
import numpy as np

from genshin_mummy.ocr.type import TextChunkCollection


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
        for idx, (subentry_key,
                  subentry_value) in enumerate(self.subentries.items(),
                                               start=1):
            result[f'副词条{idx}'] = f'{subentry_key.value}={subentry_value}'
        return result

    def to_str(self):
        return ' | '.join(
            [f'{key}: {value}' for key, value in self.to_dict().items()])

    def __str__(self) -> str:
        return self.to_str()


@attrs.define
class ArtifactDescription:
    # TODO:
    image: np.ndarray = attrs.field()
    text_chunk_collection: TextChunkCollection = attrs.field()
