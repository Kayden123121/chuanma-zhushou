import json
import os
import logging
from typing import List, Dict, Any
from openai import OpenAI
import re

from chuan_mahjong import RULES_BRIEF, MPSZ_TILE_HELP, sanitize_events

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self, api_key: str = None, base_url: str = None, model: str = "gpt-4o"):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        else:
            logger.warning("LLMService initialized without API_KEY. LLM features will be disabled.")
            self.client = None

    def analyze_game_events(self, text: str) -> List[Dict[str, Any]]:
        """
        Analyze transcribed text to extract Mahjong game events.
        Returns a list of events like: [{"type": "DISCARD", "tile": "5s"}]
        """
        if not self.client:
            logger.warning("LLM Client not initialized. Skipping analysis.")
            return []

        prompt = f"""
你是一名四川麻将（血战到底）场况裁判。请分析以下语音转录文本，提取其中的牌局事件。

{RULES_BRIEF}

注意：仅提取明确的本人操作指令。忽略闲聊、疑问句（如"你碰了吗"）以及对他家动作的猜测。

文本内容: "{text}"

请提取以下类型的事件（严格遵循动作定义）：
1. 出牌/切牌 (DISCARD): 说出要打出的牌名，如「打五万」「出三条」「八筒」。无碰/杠/胡时，以最后确认的出牌为准。
2. 碰 (PON): 明确说「碰」且能对应到一张牌（用该张牌的编码）。
3. 杠 (KAN): 明确说「杠」「开杠」「暗杠」「点杠」等，对应被杠的那张牌编码（补杠同理）。
4. 胡牌 (HU): 明确说「胡」「和」「自摸」等；自摸可输出 {{"type": "HU", "tile": null}} 或写出摸到的牌。
5. 不要输出「吃」(CHI)：四川麻将不允许吃牌。若用户说「吃」，视为无效，输出 []。

常见别名（仅万/筒/条）：
- 幺鸡/小鸡/一条 -> 1s
- 大饼有时指一筒 -> 1p（需结合语境）
- 二筒～九筒、二万～九万、二条～九条按数字对应

定缺与换三张（若语音明确提及，可作辅助事件，非必须）：
- 定缺：可输出 {{"type": "DINGQUE", "tile": "m"}} 表示缺万，p=缺筒，s=缺条（tile 用单字母 m/p/s）。

规则：
- 如果出现自我更正（如「打五万…不对，打八条」），只输出最后确认的动作。
- 牌名仅使用万/筒/条编码，禁止输出字牌（无东东南西北发白）。
{MPSZ_TILE_HELP}
- 严禁使用 "w" 表示万，必须写成 "m"（如 "5m"）。

示例参考：

输入: "打五索"
输出: [{{"type": "DISCARD", "tile": "5s"}}]

输入: "碰三万"
输出: [{{"type": "PON", "tile": "3m"}}]

输入: "杠八万"
输出: [{{"type": "KAN", "tile": "8m"}}]

输入: "胡了，自摸"
输出: [{{"type": "HU", "tile": null}}]

输入: "吃一二三筒"
输出: []

输入: "碰二条，打三万"
输出: [{{"type": "PON", "tile": "2s"}}, {{"type": "DISCARD", "tile": "3m"}}]

输入: "我缺万"
输出: [{{"type": "DINGQUE", "tile": "m"}}]

输入: "打五万...不对，打八条"
输出: [{{"type": "DISCARD", "tile": "8s"}}]

输入: "今天运气真好"
输出: []

要求：
- 只输出纯 JSON 数组，不要包含 Markdown 标记 (如 ```json)。
- 如果无法识别任何事件或文本无关，返回空数组 []。
- 重要：确保输出的是合法的 JSON 格式。
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that outputs raw JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            
            content = response.choices[0].message.content.strip()
            
            # Robust JSON extraction
            match = re.search(r"\[.*\]", content, re.DOTALL)
            if match:
                content = match.group(0)
            
            # Simple cleanup for markdown just in case (fallback)
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
                
            parsed = json.loads(content.strip())
            if isinstance(parsed, list):
                return sanitize_events(parsed)
            return []
            
        except Exception as e:
            logger.error(f"LLM Analysis Error: {e}")
            # Try to return partial result or empty
            return []
