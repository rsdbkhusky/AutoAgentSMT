"""
LLM 客户端封装 - OpenAI 兼容接口 + 速率限制
"""
import asyncio
import json
import time
import logging
from openai import AsyncOpenAI

logger = logging.getLogger("llm_client")
_file_only = {"file_only": True}
_call_counter = 0


class RateLimiter:
    """令牌桶速率限制器"""

    def __init__(self, max_calls_per_minute: int):
        self.max_calls = max_calls_per_minute
        self.tokens = float(max_calls_per_minute)
        self.last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self):
        """等待直到获得一个调用令牌"""
        while True:
            async with self._lock:
                now = time.monotonic()
                elapsed = now - self.last_refill
                self.tokens = min(self.max_calls, self.tokens + elapsed * self.max_calls / 60.0)
                self.last_refill = now
                if self.tokens >= 1:
                    self.tokens -= 1
                    return
            await asyncio.sleep(0.5)


class BaseLLM:
    """OpenAI 兼容 LLM 客户端"""

    def __init__(self, config: dict):
        self.client = AsyncOpenAI(
            base_url=config["base_url"],
            api_key=config["api_key"],
        )
        self.model = config["model"]
        self.default_temperature = config.get("default_temperature", 0.7)
        self.max_tokens = config.get("max_tokens", 1024)
        self.retry_attempts = config.get("retry_attempts", 3)
        self.rate_limiter = RateLimiter(config.get("max_calls_per_minute", 30))

    async def chat(self, messages: list[dict], temperature: float = None,
                   max_tokens: int = None) -> str:
        """发送聊天请求，返回助手回复文本"""
        # await self.rate_limiter.acquire()
        temp = temperature if temperature is not None else self.default_temperature
        tokens = max_tokens if max_tokens is not None else self.max_tokens

        global _call_counter
        _call_counter += 1
        call_id = _call_counter
        logger.info(f"[LLM#{call_id}] 请求上下文:\n{json.dumps(messages, ensure_ascii=False, indent=2)}", extra=_file_only)

        for attempt in range(self.retry_attempts):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=1.9,
                    # max_tokens=tokens,
                    extra_body={"enable_thinking": False},
                )
                content = response.choices[0].message.content or ""
                logger.info(f"[LLM#{call_id}] 响应全文:\n{content}", extra=_file_only)
                return content
            except Exception as e:
                logger.warning(f"LLM 调用失败 (第{attempt + 1}次): {e}")
                if attempt < self.retry_attempts - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    logger.error(f"[LLM#{call_id}] 调用彻底失败: {e}")
                    return ""

    async def chat_json(self, messages: list[dict], temperature: float = 0.3) -> dict:
        """发送请求并解析JSON格式返回值"""
        text = await self.chat(messages, temperature=temperature)
        if not text:
            return {}
        # 尝试提取 JSON
        try:
            # 尝试直接解析
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        # 尝试从 markdown 代码块中提取
        try:
            if "```json" in text:
                json_str = text.split("```json")[1].split("```")[0].strip()
                return json.loads(json_str)
            elif "```" in text:
                json_str = text.split("```")[1].split("```")[0].strip()
                return json.loads(json_str)
            # 尝试找 { } 包围的内容
            start = text.index("{")
            end = text.rindex("}") + 1
            return json.loads(text[start:end])
        except (json.JSONDecodeError, ValueError, IndexError):
            logger.warning(f"无法解析LLM返回的JSON: {text[:200]}")
            return {}
