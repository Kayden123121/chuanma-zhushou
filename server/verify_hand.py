import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from chuan_mahjong import filter_34_to_mps
from efficiency_engine import EfficiencyEngine
from mahjong.tile import TilesConverter


def main():
    engine = EfficiencyEngine()

    # 川麻示例：万筒条 14 张，无字牌
    hand_str = "3467m2356p5578s12m"
    print(f"正在分析手牌（川麻）: {hand_str}")

    try:
        hand_136 = TilesConverter.one_line_string_to_136_array(hand_str)
    except Exception as e:
        print(f"Error parsing hand: {e}")
        return

    print("正在计算最佳切牌（贪心：听牌距离 + 进张）...")
    hidden_hand_34 = filter_34_to_mps(engine._to_34_array(hand_136))
    full_hand_34 = list(hidden_hand_34)

    candidates = []
    unique_tiles = [i for i, c in enumerate(full_hand_34) if c > 0 and i < 27]

    print(f"Candidates indices: {unique_tiles}")

    for tile_idx in unique_tiles:
        full_hand_34[tile_idx] -= 1

        shanten = engine._chuan_shanten(full_hand_34)
        ukeire, ukeire_tiles = engine._get_blind_ukeire(full_hand_34, shanten)

        tile_str = engine.index_to_mpsz[tile_idx]
        candidates.append(
            {
                "discard_tile": tile_str,
                "discard_id": tile_idx,
                "shanten": shanten,
                "ukeire": ukeire,
                "ukeire_tiles": ukeire_tiles,
            }
        )

        full_hand_34[tile_idx] += 1

    candidates.sort(key=lambda x: (x["shanten"], -x["ukeire"]))

    print("-" * 30)
    print("所有切牌选项 (Top 5):")
    for c in candidates[:5]:
        print(f"切: {c['discard_tile']} -> 听牌距离: {c['shanten']}, 进张: {c['ukeire']}")

    result = candidates[0] if candidates else None

    if result:
        print("-" * 30)

    if result:
        discard_34 = result["discard_id"]

        hand_13 = []
        removed = False
        for t in hand_136:
            if not removed and (t // 4) == discard_34:
                removed = True
                continue
            hand_13.append(t)

        print("-" * 30)
        print("切牌后状态分析 (13张):")
        opps = engine.analyze_opportunities(hand_13)
        print(f"当前听牌距离 (13张): {opps['current_shanten']}")

        watch_list = opps.get("watch_list", [])
        if watch_list:
            print("碰/杠 观察列表（川麻无吃）:")
            for item in watch_list:
                print(f"  - 牌: {item['tile']}, 动作: {item['action']}")
        else:
            print("没有推荐的碰/杠机会。")

        keep_list = opps.get("keep_list", [])
        if keep_list:
            print("摸打进张分析 (Top 5):")
            for i, item in enumerate(keep_list[:5]):
                print(
                    f"  {i+1}. 摸: {item['draw']} -> 切: {item['discard']} "
                    f"(听牌距离: {item['shanten']}, 进张: {item['ukeire']})"
                )


if __name__ == "__main__":
    main()
