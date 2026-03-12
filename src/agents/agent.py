"""
Agent 类 - 通用Agent，行为完全由配置文件驱动
"""
import logging
from agents.memory import Memory

logger = logging.getLogger("agent")


class Agent:
    """通用Agent类，性格和行为由配置文件中的提示词决定"""

    def __init__(self, agent_id: str, name: str, config: dict, llm):
        self.agent_id = agent_id
        self.name = name
        self.description = config.get("description", "")
        self.system_prompt_template = config.get("system_prompt", "")
        self.risk_tolerance = config.get("risk_tolerance", 0.5)
        self.initial_cash = config.get("initial_cash", 500000)
        self.cash = float(self.initial_cash)
        self.positions: dict[str, int] = {}  # {股票代码: 持仓数量}
        self.llm = llm
        self.memory = Memory(max_events=50)
        self.type_id = config.get("type_id", "unknown")
        self.config = config

    def get_portfolio_value(self, prices: dict[str, float]) -> float:
        """计算总资产"""
        stock_value = sum(prices.get(code, 0) * qty for code, qty in self.positions.items())
        return self.cash + stock_value

    def get_status_text(self, prices: dict[str, float]) -> str:
        """生成持仓状况文本"""
        total = self.get_portfolio_value(prices)
        pnl = total - self.initial_cash
        pnl_pct = (pnl / self.initial_cash) * 100 if self.initial_cash else 0
        lines = [f"现金: ¥{self.cash:,.2f}"]
        for code, qty in self.positions.items():
            price = prices.get(code, 0)
            lines.append(f"  {code}: {qty}股 (市值 ¥{price * qty:,.2f})")
        lines.append(f"总资产: ¥{total:,.2f} (盈亏: {pnl_pct:+.2f}%)")
        return "\n".join(lines)

    def _build_system_prompt(self, prices: dict[str, float], current_time: str) -> str:
        """构建系统提示词，填充动态变量"""
        prompt = self.system_prompt_template.format(
            name=self.name,
            description=self.description,
            portfolio_status=self.get_status_text(prices),
            current_time=current_time,
        )
        return prompt

    async def perceive(self, market_snapshot: dict, news_list: list[dict],
                       recent_chat: list[dict]) -> dict:
        """感知阶段：组装当前环境信息"""
        # 市场行情摘要
        market_text = "当前市场行情：\n"
        for code, quote in market_snapshot.get("stocks", {}).items():
            ask = quote.get('best_ask', 0)
            bid = quote.get('best_bid', 0)
            ask_str = f" 卖一¥{ask}" if ask else ""
            bid_str = f" 买一¥{bid}" if bid else ""
            market_text += f"  {quote['name']}({code}): ¥{quote['price']} 涨跌{quote['change_pct']}%{ask_str}{bid_str}\n"

        # 新闻摘要
        news_text = ""
        if news_list:
            news_text = "最新新闻：\n"
            for news in news_list[-3:]:
                sentiment_cn = {"positive": "利好", "negative": "利空", "neutral": "中性"}.get(news.get("sentiment", ""), "")
                news_text += f"  [{sentiment_cn}] {news['title']}: {news['content']}\n"

        # 群聊摘要
        chat_text = ""
        if recent_chat:
            chat_text = "近期群聊讨论：\n"
            for msg in recent_chat[-5:]:
                chat_text += f"  {msg['agent_name']}: {msg['content']}\n"

        # 历史记忆
        memory_text = "你的近期记忆：\n" + self.memory.summarize()

        return {
            "market_text": market_text,
            "news_text": news_text,
            "chat_text": chat_text,
            "memory_text": memory_text,
        }

    async def decide(self, perception: dict, prices: dict[str, float],
                     current_time: str) -> dict:
        """决策阶段：调用LLM产出结构化决策"""
        system_prompt = self._build_system_prompt(prices, current_time)
        user_content = "\n\n".join(filter(None, [
            perception["market_text"],
            perception["news_text"],
            perception["chat_text"],
            perception["memory_text"],
            "请根据以上信息，做出你的投资决策。严格以JSON格式回复。",
        ]))

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

        decision = await self.llm.chat_json(messages)

        # 如果 LLM 返回为空或格式不对，默认 hold
        if not decision or "action" not in decision:
            decision = {
                "action": "hold",
                "stock_code": "",
                "quantity": 0,
                "price": 0,
                "reasoning": "暂时观望",
                "chat_message": "",
            }

        return decision

    async def act(self, decision: dict, engine, prices: dict[str, float]) -> dict:
        """行动阶段：提交订单"""
        result = {"agent_id": self.agent_id, "agent_name": self.name, "decision": decision, "trade_result": None}

        action = decision.get("action", "hold")
        stock_code = decision.get("stock_code", "")
        quantity = int(decision.get("quantity", 0))
        price = float(decision.get("price", 0))

        if action in ("buy", "sell") and stock_code and quantity > 0 and price > 0:
            # 买入前检查资金
            if action == "buy" and price * quantity > self.cash:
                quantity = int(self.cash / price)
                if quantity <= 0:
                    self.memory.add_event("decision", f"尝试买入{stock_code}但资金不足")
                    return result

            # 卖出前检查持仓
            if action == "sell":
                held = self.positions.get(stock_code, 0)
                if held <= 0:
                    self.memory.add_event("decision", f"尝试卖出{stock_code}但无持仓")
                    return result
                quantity = min(quantity, held)

            trade_result = engine.submit_order(self.agent_id, stock_code, action, price, quantity)
            result["trade_result"] = trade_result

            # 更新 Agent 的资金和持仓
            for trade in trade_result.get("trades", []):
                trade_qty = trade["quantity"]
                trade_price = trade["price"]
                if action == "buy":
                    self.cash -= trade_price * trade_qty
                    self.positions[stock_code] = self.positions.get(stock_code, 0) + trade_qty
                elif action == "sell":
                    self.cash += trade_price * trade_qty
                    self.positions[stock_code] = self.positions.get(stock_code, 0) - trade_qty
                    if self.positions[stock_code] <= 0:
                        self.positions.pop(stock_code, None)

            self.memory.add_event("trade",
                f"{action} {stock_code} {quantity}股 @ ¥{price}, 成交{len(trade_result.get('trades', []))}笔")
        else:
            self.memory.add_event("decision", f"决定观望: {decision.get('reasoning', '')}")

        return result

    async def run_round(self, market_snapshot: dict, news_list: list[dict],
                        recent_chat: list[dict], engine) -> dict:
        """执行完整的一轮：感知 → 决策 → 行动"""
        prices = {code: q["price"] for code, q in market_snapshot.get("stocks", {}).items()}
        current_time = market_snapshot.get("virtual_time", "")

        # 感知
        perception = await self.perceive(market_snapshot, news_list, recent_chat)

        # 添加新闻到记忆
        for news in news_list:
            self.memory.add_event("news", f"[{news.get('sentiment','')}] {news['title']}")

        # 决策
        decision = await self.decide(perception, prices, current_time)
        logger.info(f"[{self.name}] 决策: {decision.get('action', 'hold')} "
                     f"{decision.get('stock_code', '')} {decision.get('quantity', 0)}")

        # 行动
        result = await self.act(decision, engine, prices)
        result["chat_message"] = decision.get("chat_message", "")
        return result

    def to_position_dict(self, prices: dict[str, float]) -> dict:
        """返回持仓信息字典"""
        total = self.get_portfolio_value(prices)
        pnl_pct = ((total - self.initial_cash) / self.initial_cash * 100) if self.initial_cash else 0
        return {
            "agent_id": self.agent_id,
            "agent_name": self.name,
            "agent_type": self.type_id,
            "cash": round(self.cash, 2),
            "positions": dict(self.positions),
            "total_value": round(total, 2),
            "pnl_pct": round(pnl_pct, 2),
        }
