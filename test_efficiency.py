"""川麻牌效脚本自测（万/筒/条，无字牌）。"""
import os
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
_SERVER = os.path.join(_ROOT, "server")
if _SERVER not in sys.path:
    sys.path.insert(0, _SERVER)

from efficiency_engine import EfficiencyEngine
from mahjong.tile import TilesConverter


def test_efficiency():
    engine = EfficiencyEngine()

    print("--- Test 1: Best Discard (14 tiles, 川麻) ---")
    hand_str_14 = "11123456m88p999s1m"
    hand_14 = TilesConverter.one_line_string_to_136_array(hand_str_14)

    result = engine.calculate_best_discard(hand_14)
    print(f"Input: {hand_str_14}")
    print(f"Best Discard: {result.get('discard_tile')}")
    print(f"听牌距离: {result.get('shanten')}")
    print(f"进张: {result.get('ukeire')}")

    assert result.get("discard_tile") == "1m"

    print("\n--- Test 2: Lookup Table (13 tiles) ---")
    hand_str_13 = "1234567m456p789s"
    hand_13 = TilesConverter.one_line_string_to_136_array(hand_str_13)

    lookup = engine.generate_lookup_table(hand_13)
    print(f"Lookup Table keys count: {len(lookup)}")

    print("\n--- Test 3: Analyze Opportunities (13 tiles) ---")
    hand_str_tenpai = "12323m456p789s11p"
    hand_tenpai = TilesConverter.one_line_string_to_136_array(hand_str_tenpai)
    opportunities = engine.analyze_opportunities(hand_tenpai)
    print(f"听牌距离: {opportunities['current_shanten']}")
    print(f"胡牌候选: {opportunities['win_list']}")

    hand_str_pon = "11m123p456s789s12p"
    hand_pon = TilesConverter.one_line_string_to_136_array(hand_str_pon)
    opp_pon = engine.analyze_opportunities(hand_pon)
    print("\nPon Test:")
    print(f"Watch List (无吃): {[x['action'] for x in opp_pon['watch_list']]}")

    found_pon = any(w["tile"] == "1m" and w["action"] == "PON" for w in opp_pon["watch_list"])
    if found_pon:
        print("Pon 1m detected.")

    keep_list = opp_pon.get("keep_list", [])
    if keep_list:
        first_item = keep_list[0]
        assert isinstance(first_item, dict)
        assert "draw" in first_item
        print("Keep List structure verified.")


if __name__ == "__main__":
    test_efficiency()
