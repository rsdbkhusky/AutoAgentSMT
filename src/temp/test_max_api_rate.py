"""
API 压力测试 - 同时发32个请求，统计回复和回复时间
"""
import random
import time
from openai import OpenAI

# ========== 配置 ==========
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
API_KEY = "sk-ea12206394f2408db43d64978c8e17da"
MODEL = "qwen3.5-flash"
# thinking on & max_token 1024: cnt=32 -> 12-65s
# thinking off & max_token deft: 2-6s

# BASE_URL = "https://openrouter.ai/api/v1"
# API_KEY = "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"
# # MODEL = "qwen/qwen3.5-flash-02-23"
# MODEL = "stepfun/step-3.5-flash:free"
# thinking on & max_token 1024: cnt=32 -> 16-68s
# thinking off & max_token deft: 5-18s

# BASE_URL = "https://api.siliconflow.cn/v1"
# API_KEY = "sk-ckxnkfqoskvvfzbmmcxgkxgolhejlnwgeqegptdlgwnwlkbf"
# MODEL = "Qwen/Qwen3.5-35B-A3B"
# thinking on & max_token 1024: cnt=32 -> 8-8s, but empty response
# thinking off & max_token deft: cnt=32 -> 2-12s

CONCURRENCY = 32

# ========== 随机内容生成 ==========
STOCK_NAMES = ["星辰科技", "灰狼能源", "翡翠消费", "龙腾重工", "凤凰传媒", "虎啸金融", "鹰眼安防", "白鸽医药"]
ACTIONS = ["大幅上涨", "小幅下跌", "横盘震荡", "涨停", "跌停", "放量突破", "缩量回调", "低开高走"]
REASONS = [
    "受政策利好影响", "财报超预期", "行业景气度提升", "主力资金大幅流入",
    "海外市场联动", "技术面突破关键阻力位", "市场情绪回暖", "机构集中调研",
    "原材料价格波动", "新产品发布预期", "管理层增持", "分析师上调评级",
]
GARBLE = "abcdefghijklmnopqrstuvwxyz0123456789"

PROMPT_TEMPLATE = """你是一位股票分析师。请对以下市场情况做一句话点评，不超过50字。

市场情况：{stock}今日{action}，{reason}。当前价格{price}元，成交量{volume}手。
补充信息：{noise}"""


def random_prompt():
    noise_parts = []
    for _ in range(random.randint(1, 3)):
        if random.random() < 0.3:
            noise_parts.append("".join(random.choices(GARBLE, k=random.randint(5, 15))))
        else:
            noise_parts.append(random.choice(REASONS))
    return PROMPT_TEMPLATE.format(
        stock=random.choice(STOCK_NAMES),
        action=random.choice(ACTIONS),
        reason=random.choice(REASONS),
        price=round(random.uniform(5, 200), 2),
        volume=random.randint(1000, 500000),
        noise="；".join(noise_parts),
    )


# ========== 测试 ==========
import threading

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)
t0 = time.time()

def call(i):
    start = time.time()
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": random_prompt()}],
            # max_tokens=64,
            extra_body={"enable_thinking": False},
        )
        elapsed = time.time() - start
        choice = resp.choices[0] if resp.choices else None
        content = choice.message.content if choice else None
        finish = choice.finish_reason if choice else None
        usage = resp.usage
        print(f"#{i+1:02d}  {elapsed:.2f}s  finish_reason={finish}  "
              f"prompt_tokens={usage.prompt_tokens if usage else '?'}  "
              f"completion_tokens={usage.completion_tokens if usage else '?'}  "
              f"content={'[空]' if not content else repr(content)}")
    except Exception as e:
        print(f"#{i+1:02d}  {time.time()-start:.2f}s  {type(e).__name__}: {e}")

print(f"同时发送 {CONCURRENCY} 个请求, MODEL {MODEL}, BASE_URL {BASE_URL}")
print("-" * 60)

threads = [threading.Thread(target=call, args=(i,)) for i in range(CONCURRENCY)]
for t in threads:
    t.start()
for t in threads:
    t.join()

print(f"\n全部完成，总耗时 {time.time()-t0:.2f}s")
