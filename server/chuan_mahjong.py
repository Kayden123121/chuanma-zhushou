# 四川麻将（常见线上/血战到底）规则常量，供提示词与校验复用。
# 牌张：仅万/筒/条 108 张，无字牌；不能吃；可碰、杠（点杠/暗杠/补杠）。

from typing import Any, Dict, List

# 34 张索引：0–26 为万筒条；27–33 为字牌（川麻 108 张不含）
MPS_INDEX_MAX = 27

VARIANT_NAME = "四川麻将（血战到底）"

RULES_BRIEF = """
本对局为四川麻将（血战到底）常见规则：
- 仅使用万、筒、条三门共108张牌，不含东南西北发白。
- 不能吃牌，仅可碰牌、杠牌（点杠、暗杠、补杠）。
- 通常开局有「换三张」与「定缺」：手牌中最终不得保留三门花色，必须缺一门。
- 无「立直」等日式宣告；算分以房间血战/番型规则为准。
"""

MPSZ_TILE_HELP = """
牌编码仅使用 m(万)、p(筒)、s(条/索)，禁止输出 z 后缀的字牌：
- 万子: 1m～9m
- 筒子: 1p～9p
- 条/索: 1s～9s
"""


def sanitize_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """移除不符合川麻 108 张规则的事件（如吃、字牌）。"""
    out: List[Dict[str, Any]] = []
    for e in events:
        if not isinstance(e, dict):
            continue
        t = e.get("type")
        if t == "CHI":
            continue
        tile = e.get("tile")
        if t == "DINGQUE":
            if tile in ("m", "p", "s"):
                out.append(e)
            continue
        if t == "HU":
            out.append(e)
            continue
        if t not in ("DISCARD", "PON", "KAN"):
            continue
        if not tile or not isinstance(tile, str):
            continue
        if len(tile) == 2 and tile[-1] in "mps" and tile[0].isdigit():
            out.append(e)
            continue
        if len(tile) > 2 and tile[-1] in "mps":
            out.append(e)
            continue
    return out


def filter_34_to_mps(h34: List[int]) -> List[int]:
    """去掉字牌维度，仅保留万/筒/条（索引 0–26）。"""
    h = list(h34)
    for i in range(MPS_INDEX_MAX, 34):
        h[i] = 0
    return h


def strip_136_honors(hand_136: List[int]) -> List[int]:
    """从 136 张编码中移除字牌（tile//4 >= 27）。"""
    return [t for t in hand_136 if t // 4 < MPS_INDEX_MAX]
