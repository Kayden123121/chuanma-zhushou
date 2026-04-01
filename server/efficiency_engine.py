"""
川麻牌效：108 张（万/筒/条），不吃牌、无字牌；
向听计算关闭「国士无双」路径，保留一般型与七对（川麻常见胡型）。
贪心策略：优先最小听牌距离，其次最大进张数。
"""
from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional, Tuple, Union

from mahjong.meld import Meld
from mahjong.shanten import Shanten
from mahjong.tile import TilesConverter

from chuan_mahjong import MPS_INDEX_MAX, filter_34_to_mps, strip_136_honors


def _build_index_mpsz() -> List[str]:
    out = [f"{i + 1}m" for i in range(9)]
    out += [f"{i + 1}p" for i in range(9)]
    out += [f"{i + 1}s" for i in range(9)]
    out += [f"{i + 1}z" for i in range(7)]
    return out


INDEX_TO_MPSZ: List[str] = _build_index_mpsz()


def mpsz_list_to_one_line(tiles: List[str]) -> str:
    """仅万/筒/条，忽略字牌（川麻 108 张）。"""
    m, p, s = [], [], []
    for t in tiles:
        if not t or len(t) < 2:
            continue
        suit = t[-1]
        num = t[:-1]
        if suit == "m":
            m.append(num)
        elif suit == "p":
            p.append(num)
        elif suit == "s":
            s.append(num)
    parts = []
    if m:
        parts.append("".join(sorted(m, key=lambda x: int(x) if x.isdigit() else 0)) + "m")
    if p:
        parts.append("".join(sorted(p, key=lambda x: int(x) if x.isdigit() else 0)) + "p")
    if s:
        parts.append("".join(sorted(s, key=lambda x: int(x) if x.isdigit() else 0)) + "s")
    return "".join(parts)


class EfficiencyEngine:
    def __init__(self) -> None:
        self.shanten_calculator = Shanten()
        self.index_to_mpsz = INDEX_TO_MPSZ

    def _to_34_array(self, hand_136: List[int]) -> List[int]:
        return TilesConverter.to_34_array(hand_136)

    def _get_full_hand_34(self, hand_136: List[int]) -> List[int]:
        return self._to_34_array(hand_136)

    def _chuan_shanten(self, tiles_34: List[int]) -> int:
        """川麻：仅万筒条；不算国士无双（无字牌）。"""
        h = filter_34_to_mps(tiles_34)
        return self.shanten_calculator.calculate_shanten(
            h, use_chiitoitsu=True, use_kokushi=False
        )

    def _min_shanten_after_discard(self, hand_34_14: List[int]) -> int:
        assert sum(hand_34_14) == 14
        best = 99
        h = hand_34_14
        for j in range(MPS_INDEX_MAX):
            if h[j] == 0:
                continue
            t = copy.copy(h)
            t[j] -= 1
            sh = self._chuan_shanten(t)
            if sh < best:
                best = sh
        return best

    def _get_blind_ukeire(self, hand_34: List[int], s0: int) -> Tuple[int, List[str]]:
        """
        进张：假设牌山每种牌最多 4 张，仅统计万/筒/条。
        听牌距离为 0 时：摸到即胡牌（14 张为和了）算进张。
        """
        assert sum(hand_34) == 13
        total = 0
        names: List[str] = []
        for i in range(MPS_INDEX_MAX):
            if hand_34[i] >= 4:
                continue
            h14 = copy.copy(hand_34)
            h14[i] += 1
            if s0 == 0:
                if self._chuan_shanten(h14) == Shanten.AGARI_STATE:
                    total += 4 - hand_34[i]
                    names.append(self.index_to_mpsz[i])
                continue
            best = self._min_shanten_after_discard(h14)
            if best < s0:
                total += 4 - hand_34[i]
                names.append(self.index_to_mpsz[i])
        return total, names

    def _best_discard_from_34(self, hand_34: List[int]) -> Optional[Dict[str, Any]]:
        total = sum(hand_34)
        if total < 1:
            return None
        candidates: List[Dict[str, Any]] = []
        for i in range(MPS_INDEX_MAX):
            if hand_34[i] <= 0:
                continue
            h = copy.copy(hand_34)
            h[i] -= 1
            s0 = self._chuan_shanten(h)
            if sum(h) == 13:
                u, ut = self._get_blind_ukeire(h, s0)
            else:
                u, ut = 0, []
            candidates.append(
                {
                    "discard_tile": self.index_to_mpsz[i],
                    "discard_id": i,
                    "shanten": s0,
                    "ukeire": u,
                    "ukeire_tiles": ut,
                }
            )
        if not candidates:
            return None
        candidates.sort(key=lambda x: (x["shanten"], -x["ukeire"], x["discard_id"]))
        best = candidates[0]
        best["message"] = (
            f"川麻牌效：建议打【{best['discard_tile']}】（切后听牌距离 {best['shanten']}，进张 {best['ukeire']}）"
        )
        return best

    def calculate_best_discard(
        self,
        hand: Union[List[int], List[str]],
        melds: Optional[List[Any]] = None,
        photo_count: Optional[int] = None,
    ) -> Dict[str, Any]:
        del photo_count
        del melds
        try:
            if not hand:
                return {"message": "未识别到手牌，无法计算牌效。"}
            if isinstance(hand[0], str):
                line = mpsz_list_to_one_line(hand)
                if not line:
                    return {"message": "手牌格式无效（川麻仅万/筒/条）。"}
                hand_136 = TilesConverter.one_line_string_to_136_array(line)
            else:
                hand_136 = strip_136_honors(hand)
            h34 = self._to_34_array(hand_136)
            h34 = filter_34_to_mps(h34)
            if sum(h34) != 14:
                return {
                    "message": f"需要 14 张序数牌才能计算最佳出牌，当前合计 {sum(h34)} 张。",
                    "tile_count": sum(h34),
                }
            res = self._best_discard_from_34(h34)
            if not res:
                return {"message": "无法生成切牌候选。"}
            return res
        except Exception as e:
            return {"message": f"牌效计算异常: {e}"}

    def _calculate_best_discard(
        self,
        hidden_hand: Union[List[str], List[int]],
        melds: Optional[List[Meld]] = None,
    ) -> Optional[Dict[str, Any]]:
        del melds
        if not hidden_hand:
            return None
        if isinstance(hidden_hand[0], str):
            line = mpsz_list_to_one_line(hidden_hand)
            hand_136 = TilesConverter.one_line_string_to_136_array(line)
        else:
            hand_136 = strip_136_honors(hidden_hand)
        h34 = filter_34_to_mps(self._to_34_array(hand_136))
        return self._best_discard_from_34(h34)

    def generate_lookup_table(
        self,
        hand_136: Union[List[int], List[str]],
        melds: Optional[List[Any]] = None,
    ) -> Dict[str, Dict[str, Any]]:
        del melds
        if isinstance(hand_136[0], str):
            line = mpsz_list_to_one_line(hand_136)
            hand_136 = TilesConverter.one_line_string_to_136_array(line)
        else:
            hand_136 = strip_136_honors(hand_136)
        h34 = filter_34_to_mps(self._to_34_array(hand_136))
        if sum(h34) != 13:
            return {}
        lookup: Dict[str, Dict[str, Any]] = {}
        for i in range(MPS_INDEX_MAX):
            if h34[i] >= 4:
                continue
            h14 = copy.copy(h34)
            h14[i] += 1
            res = self._best_discard_from_34(h14)
            if not res:
                continue
            lookup[self.index_to_mpsz[i]] = {
                "discard": res["discard_tile"],
                "shanten": res["shanten"],
                "ukeire": res["ukeire"],
            }
        return lookup

    def analyze_opportunities(
        self,
        hand_136: Union[List[int], List[str]],
        melds: Optional[List[Any]] = None,
    ) -> Dict[str, Any]:
        del melds
        if isinstance(hand_136[0], str):
            line = mpsz_list_to_one_line(hand_136)
            hand_136 = TilesConverter.one_line_string_to_136_array(line)
        else:
            hand_136 = strip_136_honors(hand_136)
        h34 = filter_34_to_mps(self._to_34_array(hand_136))
        if sum(h34) != 13:
            return {"current_shanten": -1, "win_list": [], "watch_list": [], "keep_list": []}

        cur = self._chuan_shanten(h34)
        win_list: List[str] = []
        if cur == 0:
            for i in range(MPS_INDEX_MAX):
                if h34[i] >= 4:
                    continue
                h14 = copy.copy(h34)
                h14[i] += 1
                if self._chuan_shanten(h14) == Shanten.AGARI_STATE:
                    win_list.append(self.index_to_mpsz[i])

        watch_list: List[Dict[str, Any]] = []
        for t in range(MPS_INDEX_MAX):
            if h34[t] >= 2:
                watch_list.append(
                    {
                        "tile": self.index_to_mpsz[t],
                        "action": "PON",
                        "discard_suggestion": "",
                        "shanten_after": cur,
                    }
                )
            if h34[t] >= 3:
                watch_list.append(
                    {
                        "tile": self.index_to_mpsz[t],
                        "action": "KAN",
                        "discard_suggestion": "",
                        "shanten_after": cur,
                    }
                )

        keep_list: List[Dict[str, Any]] = []
        for i in range(MPS_INDEX_MAX):
            if h34[i] >= 4:
                continue
            h14 = copy.copy(h34)
            h14[i] += 1
            res = self._best_discard_from_34(h14)
            if res:
                keep_list.append(
                    {
                        "draw": self.index_to_mpsz[i],
                        "discard": res["discard_tile"],
                        "shanten": res["shanten"],
                        "ukeire": res["ukeire"],
                    }
                )
        keep_list.sort(key=lambda x: (x["shanten"], -x["ukeire"]))
        return {
            "current_shanten": cur,
            "win_list": win_list,
            "watch_list": watch_list,
            "keep_list": keep_list,
            "message": f"听牌距离 {cur}，胡牌候选 {win_list[:8]}…",
        }


def format_suggestions(engine_result: Dict[str, Any], result_type: str = "discard") -> str:
    del result_type
    if not engine_result:
        return "分析中..."
    if engine_result.get("message"):
        return engine_result["message"]
    disc = engine_result.get("discard_tile")
    if disc:
        return (
            f"建议打出 {disc}（听牌距离 {engine_result.get('shanten')} / "
            f"进张 {engine_result.get('ukeire')}）"
        )
    return "分析中..."
