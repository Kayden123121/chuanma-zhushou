import time
import json
from openai import OpenAI

# Configuration
API_URL = "http://127.0.0.1:1234/v1"
API_KEY = "qwen/qwen3-4b-2507"
MODEL_NAME = "qwen/qwen3-4b-2507"

# 川麻场况示例（无吃、无字牌）
TRANSCRIPT = "下家打了一张五万，我这边碰了，然后切一张三条！"


def run_test():
    print(f"Connecting to LLM at {API_URL}...")
    print(f"Model: {MODEL_NAME}")
    print(f"Simulated Transcript: \"{TRANSCRIPT}\"")
    print("-" * 50)

    client = OpenAI(base_url=API_URL, api_key=API_KEY)

    prompt = f"""
你是一名四川麻将（血战到底）场况裁判。请分析以下语音转录文本，提取其中的牌局事件。

文本内容: "{TRANSCRIPT}"

请提取以下类型的事件：
1. 出牌 (DISCARD): 例如 "切三条"、"打五万"
2. 碰 (PON)
3. 杠 (KAN)
不要输出「吃」；不要输出字牌（川麻 108 张仅万/筒/条）。

请返回 JSON 格式的列表，每个元素包含 "type" 和 "tile" (仅 m/p/s，如 5m, 3s)。

要求：
- 只输出纯 JSON 数组，不要包含 Markdown 标记。
- 如果无法识别任何事件或文本无关，返回空数组 []。
"""

    start_time = time.time()
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that outputs raw JSON."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
        )
        content = response.choices[0].message.content.strip()
        print(f"Response: {content}")
        print(f"Time: {time.time() - start_time:.2f}s")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    run_test()
