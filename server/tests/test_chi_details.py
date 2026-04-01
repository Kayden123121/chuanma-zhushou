import os
import sys

sys.path.append(os.path.join(os.getcwd(), "server"))

from efficiency_engine import EfficiencyEngine
from main import format_suggestions


def test_sichuan_watchlist_no_chi():
    """川麻 watch_list 仅碰/杠，不含吃。"""
    engine = EfficiencyEngine()
    # 13 张万筒条
    hand_136 = [4, 8, 16, 20, 36, 37, 38, 72, 73, 74, 0, 1, 2]

    result = engine.analyze_opportunities(hand_136, [])

    for item in result.get("watch_list", []):
        assert item.get("action") != "CHI"

    formatted = format_suggestions(result)
    assert "听牌距离" in formatted or "message" in str(result)


if __name__ == "__main__":
    test_sichuan_watchlist_no_chi()
    print("OK: Sichuan watchlist has no CHI.")
