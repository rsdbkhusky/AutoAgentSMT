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
            {"role": "system", "content": f"""你是一位资深财经新闻编辑，负责为虚拟股市生成多样化的新闻。
当前市场上有以下股票：{self.stock_list_text}

请生成2-3条财经新闻。新闻必须多样化，要求如下：

类型多样性（必须混合以下类型，不要全是同一种）：
- 直接新闻：直接提及某只股票或公司的消息（如财报、管理层变动、产品发布）
- 行业新闻：影响整个行业板块的消息（如政策变化、行业数据、技术革命），不直接点名个股但影响相关板块
- 宏观新闻：影响整体市场的消息（如央行政策、GDP数据、国际局势、汇率变动）
- 间接新闻：看似无关但对某些股票有隐含影响的消息（如上游原材料涨价影响下游、竞品公司出事利好对手、气候异常影响农业和能源）

情绪多样性：
- 不要全是利好或全是利空，必须正反混合
- 同一行业的不同股票可以受到不同方向的影响
- 有些新闻的影响是模糊的，可以是中性的

内容要求：
- 标题有冲击力，像真实财经媒体的风格
- 内容简短但信息量大（80字以内）
- 不要每次都报同样的公司，轮换关注对象

请以JSON数组格式回复，每条新闻包含：
- title: 新闻标题
- content: 新闻内容（80字以内）
- sentiment: "positive"（利好）、"negative"（利空）或 "neutral"（中性/影响不确定）
- affected_stocks: 受影响的股票代码列表（间接影响的也要列出）"""},
            {"role": "user", "content": f"""当前虚拟时间：{virtual_time}
当前部分行情：
{market_summary}
请生成新闻，注意多样性。"""}
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
