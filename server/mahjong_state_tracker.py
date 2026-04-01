from typing import List, Optional, Dict, Any, Union
import logging
from collections import Counter

logger = logging.getLogger(__name__)

class MahjongLogicError(Exception):
    """Custom exception for Mahjong logic errors."""
    pass

class MahjongStateTracker:
    def __init__(self):
        self.current_hidden_hand: Optional[List[str]] = None
        self.current_melded_tiles: List[str] = []
        self.lack_suit: Optional[str] = None
        self.action_history: List[Dict[str, Any]] = []
        self.visible_tiles: List[int] = [0] * 27
        # 新增：记录拍照次数，用于 Mock 演示逻辑
        self.photo_count = 0

    def _get_suit(self, tile: str) -> str:
        return tile[-1]

    def update_visible_tiles(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """根据语音事件更新已见牌计数（仅处理万/筒/条；川麻无字牌、无吃）。"""
        updated_count = 0
        details = []
        for event in events:
            action_type = event.get("type")
            if action_type in ("HU", "DINGQUE"):
                continue
            tile_str = event.get("tile")
            if not tile_str:
                continue

            tiles = []
            if len(tile_str) == 2:
                if tile_str[-1] not in "mps":
                    continue
                tiles.append(tile_str)
            else:
                suit = tile_str[-1]
                if suit not in "mps":
                    continue
                for char in tile_str[:-1]:
                    if char.isdigit():
                        tiles.append(f"{char}{suit}")

            for t in tiles:
                try:
                    val = int(t[0]) - 1
                    suit = t[1]
                    offset = {'m': 0, 'p': 9, 's': 18}[suit]
                    idx = offset + val
                    self.visible_tiles[idx] += 1
                    updated_count += 1
                    details.append(f"{action_type}: {t}")
                except Exception:
                    continue
        return {"updated_count": updated_count, "details": details}

    def update_state(self, new_hand: List[str], new_melds: List[str] = [], incoming_tile: Optional[str] = None) -> Dict[str, Any]:
        # 增加拍照计数
        self.photo_count += 1

        new_hand = [t for t in new_hand if t[-1] in 'mps']
        new_melds = [t for t in new_melds if t[-1] in 'mps']
        
        self.current_hidden_hand = new_hand
        self.current_melded_tiles = new_melds

        result = {
            "action": "PHOTO_ANALYSIS",
            "hand": new_hand,
            "melds": new_melds,
            "photo_count": self.photo_count
        }
        self.action_history.append(result)
        return result
