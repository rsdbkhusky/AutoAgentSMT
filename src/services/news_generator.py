"""
新闻生成服务 - 调用LLM生成市场新闻
"""
import uuid
import logging

logger = logging.getLogger("news_generator")


class NewsGenerator:
    """调用LLM生成影响市场的新闻事件"""

    def __init__(self, llm, stocks_config: list[dict]):
        self.llm = llm
        self.stocks = stocks_config
        self.stock_list_text = "、".join([f"{s['name']}({s['code']}, {s['sector']})" for s in stocks_config])

    async def generate(self, market_snapshot: dict, round_number: int,
                       virtual_time: str) -> list[dict]:
        """生成一批新闻事件"""
        # 构建市场概况
        market_summary = ""
        stocks_data = market_snapshot.get("stocks", {})
        for code, quote in list(stocks_data.items())[:10]:
            market_summary += f"  {quote['name']}({code}): ¥{quote['price']}, 涨跌幅 {quote['change_pct']}%\n"

        messages = [
            {"role": "system", "content": f"""你是一位财经新闻编辑，负责为虚拟股市生成新闻。
当前市场上有以下股票：{self.stock_list_text}

请生成1-2条有影响力的财经新闻。每条新闻应该：
1. 与具体的股票或行业相关
2. 有明确的利好或利空倾向
3. 内容简短但有冲击力

请以JSON数组格式回复，每条新闻包含：
- title: 新闻标题
- content: 新闻内容（50字以内）
- sentiment: "positive"（利好）、"negative"（利空）或 "neutral"（中性）
- affected_stocks: 受影响的股票代码列表"""},
            {"role": "user", "content": f"""当前虚拟时间：{virtual_time}
当前部分行情：
{market_summary}
请生成新闻。"""}
        ]

        result = await self.llm.chat_json(messages)

        # 处理返回结果
        news_list = []
        items = result if isinstance(result, list) else result.get("news", [result]) if result else []

        for item in items:
            if not isinstance(item, dict) or "title" not in item:
                continue
            news = {
                "news_id": str(uuid.uuid4())[:8],
                "title": item.get("title", ""),
                "content": item.get("content", ""),
                "sentiment": item.get("sentiment", "neutral"),
                "affected_stocks": item.get("affected_stocks", []),
                "round_number": round_number,
                "virtual_time": virtual_time,
            }
            news_list.append(news)

        if not news_list:
            # LLM 返回格式异常时的保底新闻
            news_list.append({
                "news_id": str(uuid.uuid4())[:8],
                "title": "市场整体走势平稳",
                "content": "今日虚拟股市各板块表现平稳，未有重大消息影响。",
                "sentiment": "neutral",
                "affected_stocks": [],
                "round_number": round_number,
                "virtual_time": virtual_time,
            })

        logger.info(f"回合 {round_number} 生成 {len(news_list)} 条新闻")
        return news_list
