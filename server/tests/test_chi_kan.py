import unittest
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "."))

from efficiency_engine import EfficiencyEngine


class TestChiKan(unittest.TestCase):
    """川麻不吃牌，观察列表不应出现「吃」。"""

    def setUp(self):
        self.engine = EfficiencyEngine()

    def test_no_chi_in_watchlist(self):
        hand_13 = [4, 8, 16, 17, 18, 20, 21, 22, 24, 25, 26, 0, 1]
        result = self.engine.analyze_opportunities(hand_13)
        for item in result.get("watch_list", []):
            self.assertNotEqual(item.get("action"), "CHI", "川麻不应提示吃牌")

    def test_kan_logic(self):
        print("\n--- Testing Kan Logic (Sichuan) ---")
        hand_13 = [0, 1, 2, 4, 8, 12, 16, 20, 24, 100, 101, 68, 69]

        result = self.engine.analyze_opportunities(hand_13)
        print(f"Initial Shanten: {result['current_shanten']}")

        watch_list = result["watch_list"]
        found_kan = any(item["tile"] == "1m" and item["action"] == "KAN" for item in watch_list)
        if found_kan:
            print("Found Kan: 1m")
        else:
            print("Kan (1m) NOT found in watch list.")


if __name__ == "__main__":
    unittest.main()
