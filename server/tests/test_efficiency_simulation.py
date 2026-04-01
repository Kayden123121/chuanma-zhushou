import unittest
import random
import sys
import os
from typing import List

sys.path.append(os.path.join(os.path.dirname(__file__), "."))

from chuan_mahjong import filter_34_to_mps
from efficiency_engine import EfficiencyEngine
from mahjong.tile import TilesConverter


class TestEfficiencySimulation(unittest.TestCase):
    def setUp(self):
        self.engine = EfficiencyEngine()

    def _generate_random_hand_mps_14(self) -> List[int]:
        """随机 14 张，仅万/筒/条（川麻 108 张）。"""
        deck: List[int] = []
        for i in range(27):
            deck.extend([i * 4, i * 4 + 1, i * 4 + 2, i * 4 + 3])
        random.shuffle(deck)
        return sorted(deck[:14])

    def test_static_benchmarks_chinitsu(self):
        """清一色混三门：切闲张后听牌（川麻，无字牌）。"""
        print("\n[Static] Testing mixed waits (Sichuan, no honors)...")
        hand_str = "11123456m88p999s1m"
        hand_136 = TilesConverter.one_line_string_to_136_array(hand_str)

        best_discard = self.engine.calculate_best_discard(hand_136)

        print(f"Hand: {hand_str}")
        self.assertIn("discard_tile", best_discard)
        print(f"Recommended Discard: {best_discard['discard_tile']}")
        print(f"Shanten after discard: {best_discard['shanten']}")
        print(f"Ukeire tiles: {best_discard['ukeire_tiles']}")

        self.assertEqual(best_discard["discard_tile"], "1m")
        self.assertEqual(best_discard["shanten"], 0)
        expected_waits = {"1m", "4m", "7m", "8p"}
        self.assertEqual(set(best_discard["ukeire_tiles"]), expected_waits)

    def test_static_benchmarks_seven_pairs(self):
        """七对形状（川麻允许七对）。"""
        print("\n[Static] Testing Seven Pairs (Sichuan)...")
        hand_str_14 = "1133557799m11p2p3p"
        hand_136_14 = TilesConverter.one_line_string_to_136_array(hand_str_14)

        best_discard = self.engine.calculate_best_discard(hand_136_14)

        print(f"Hand: {hand_str_14}")
        self.assertIn("discard_tile", best_discard)
        print(f"Recommended Discard: {best_discard['discard_tile']}")
        print(f"Shanten: {best_discard['shanten']}")
        self.assertLessEqual(best_discard["shanten"], 2)

    def test_fuzz_consistency(self):
        """随机万筒条手牌：切牌后听牌距离与进张一致。"""
        print("\n[Fuzz] Starting Fuzz Consistency Test (50 iterations, MPS only)...")
        iterations = 50
        pass_count = 0

        for i in range(iterations):
            hand_136 = self._generate_random_hand_mps_14()
            result = self.engine.calculate_best_discard(hand_136)
            if "discard_tile" not in result:
                continue

            discard_tile_idx = result["discard_id"]
            predicted_ukeire = result["ukeire"]
            predicted_shanten = result["shanten"]

            hand_34 = filter_34_to_mps(self.engine._to_34_array(hand_136))

            if hand_34[discard_tile_idx] <= 0:
                self.fail("Suggested discard not in hand")

            hand_34[discard_tile_idx] -= 1
            real_shanten = self.engine._chuan_shanten(hand_34)
            real_ukeire, _ = self.engine._get_blind_ukeire(hand_34, real_shanten)

            if real_shanten != predicted_shanten:
                self.fail(f"Iter {i}: Shanten mismatch! Pred: {predicted_shanten}, Real: {real_shanten}")
            if real_ukeire != predicted_ukeire:
                self.fail(f"Iter {i}: Ukeire mismatch! Pred: {predicted_ukeire}, Real: {real_ukeire}")

            pass_count += 1

        print(f"[Fuzz] Passed {pass_count}/{iterations} iterations.")


if __name__ == "__main__":
    unittest.main()
