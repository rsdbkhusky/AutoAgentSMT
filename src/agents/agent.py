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

        # 信息频道配置（缺省全部开启，向后兼容）
        channels = config.get("info_channels", {})
        self.channel_market_history = channels.get("market_history", 5)
        self.channel_order_book = channels.get("order_book", True)
        self.channel_chat = channels.get("chat", True)
        self.channel_news = channels.get("news", True)

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
                       recent_chat: list[dict], engine) -> dict:
        """感知阶段：根据 info_channels 配置组装环境信息"""

        # 市场行情历史（多轮K线）
        market_text = ""
        if self.channel_market_history > 0:
            market_text = "市场行情：\n"
            for code, quote in market_snapshot.get("stocks", {}).items():
                market_text += f"\n  {quote['name']}({code}): 最新价 ¥{quote['price']} 涨跌{quote['change_pct']}%\n"
                klines = engine.get_klines(code, limit=self.channel_market_history)
                if klines:
                    market_text += "    近期走势:\n"
                    for k in klines:
                        market_text += (f"    {k['time_str']}: "
                                        f"开{k['open']:.2f} 高{k['high']:.2f} "
                                        f"低{k['low']:.2f} 收{k['close']:.2f} "
                                        f"量{k['volume']}\n")

        # 盘口深度（独立信息类型）
        depth_text = ""
        if self.channel_order_book:
            depth_text = "盘口深度：\n"
            for code in market_snapshot.get("stocks", {}):
                ob = engine.order_books.get(code)
                if ob:
                    depth = ob.get_depth(levels=5)
                    depth_text += f"  {code}:\n"
                    sells = depth.get("sell", [])
                    for ask in reversed(sells):
                        depth_text += f"    卖 ¥{ask['price']:.2f} × {ask['quantity']}\n"
                    depth_text += "    ----\n"
                    for bid in depth.get("buy", []):
                        depth_text += f"    买 ¥{bid['price']:.2f} × {bid['quantity']}\n"

        # 新闻
        news_text = ""
        if self.channel_news and news_list:
            news_text = "最新新闻：\n"
            for news in news_list[-3:]:
                sentiment_cn = {"positive": "利好", "negative": "利空", "neutral": "中性"}.get(news.get("sentiment", ""), "")
                news_text += f"  [{sentiment_cn}] {news['title']}: {news['content']}\n"

        # 群聊
        chat_text = ""
        if self.channel_chat and recent_chat:
            chat_text = "近期群聊讨论：\n"
            for msg in recent_chat[-5:]:
                chat_text += f"  {msg['agent_name']}: {msg['content']}\n"

        # 历史记忆（始终包含）
        memory_text = "你的近期记忆：\n" + self.memory.summarize()

        return {
            "market_text": market_text,
            "depth_text": depth_text,
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
            perception.get("depth_text", ""),
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

        if not decision:
            return {"orders": [], "reasoning": "暂时观望", "chat_message": ""}

        # 向后兼容：旧格式（单个 action）转换为新格式（orders 列表）
        if "orders" not in decision:
            action = decision.get("action", "hold")
            if action in ("buy", "sell"):
                return {
                    "orders": [{
                        "action": action,
                        "stock_code": decision.get("stock_code", ""),
                        "quantity": decision.get("quantity", 0),
                        "price": decision.get("price", 0),
                    }],
                    "reasoning": decision.get("reasoning", ""),
                    "chat_message": decision.get("chat_message", ""),
                }
            else:
                return {
                    "orders": [],
                    "reasoning": decision.get("reasoning", "暂时观望"),
                    "chat_message": decision.get("chat_message", ""),
                }

        return decision

    async def act(self, decision: dict, engine, prices: dict[str, float]) -> dict:
        """行动阶段：提交多个订单"""
        result = {
            "agent_id": self.agent_id,
            "agent_name": self.name,
            "decision": decision,
            "trade_results": [],
        }

        orders = decision.get("orders", [])
        if not orders:
            self.memory.add_event("decision", f"决定观望: {decision.get('reasoning', '')}")
            return result

        available_cash = self.cash
        available_positions = dict(self.positions)

        for order in orders:
            action = order.get("action", "hold")
            stock_code = order.get("stock_code", "")
            quantity = int(order.get("quantity", 0))
            price = float(order.get("price", 0))

            if action not in ("buy", "sell") or not stock_code or quantity <= 0 or price <= 0:
                continue

            # 买入检查
            if action == "buy":
                affordable = int(available_cash / price)
                quantity = min(quantity, affordable)
                if quantity <= 0:
                    self.memory.add_event("decision", f"尝试买入{stock_code}但资金不足")
                    continue

            # 卖出检查
            if action == "sell":
                held = available_positions.get(stock_code, 0)
                if held <= 0:
                    self.memory.add_event("decision", f"尝试卖出{stock_code}但无持仓")
                    continue
                quantity = min(quantity, held)

            trade_result = engine.submit_order(self.agent_id, stock_code, action, price, quantity)
            result["trade_results"].append(trade_result)

            # 更新实际持仓和可用余额
            for trade in trade_result.get("trades", []):
                trade_qty = trade["quantity"]
                trade_price = trade["price"]
                if action == "buy":
                    self.cash -= trade_price * trade_qty
                    available_cash -= trade_price * trade_qty
                    self.positions[stock_code] = self.positions.get(stock_code, 0) + trade_qty
                    available_positions[stock_code] = available_positions.get(stock_code, 0) + trade_qty
                elif action == "sell":
                    self.cash += trade_price * trade_qty
                    available_cash += trade_price * trade_qty
                    self.positions[stock_code] = self.positions.get(stock_code, 0) - trade_qty
                    available_positions[stock_code] = available_positions.get(stock_code, 0) - trade_qty
                    if self.positions[stock_code] <= 0:
                        self.positions.pop(stock_code, None)
                    if available_positions.get(stock_code, 0) <= 0:
                        available_positions.pop(stock_code, None)

            # 未成交部分预留资源，防止后续订单超额
            filled_qty = sum(t["quantity"] for t in trade_result.get("trades", []))
            unfilled = quantity - filled_qty
            if unfilled > 0:
                if action == "buy":
                    available_cash -= price * unfilled
                elif action == "sell":
                    available_positions[stock_code] = available_positions.get(stock_code, 0) - unfilled

            self.memory.add_event("trade",
                f"{action} {stock_code} {quantity}股 @ ¥{price}, 成交{len(trade_result.get('trades', []))}笔")

        return result

    async def run_round(self, market_snapshot: dict, news_list: list[dict],
                        recent_chat: list[dict], engine) -> dict:
        """执行完整的一轮：感知 → 决策 → 行动"""
        prices = {code: q["price"] for code, q in market_snapshot.get("stocks", {}).items()}
        current_time = market_snapshot.get("virtual_time", "")

        # 感知
        perception = await self.perceive(market_snapshot, news_list, recent_chat, engine)

        # 添加新闻到记忆
        for news in news_list:
            self.memory.add_event("news", f"[{news.get('sentiment','')}] {news['title']}")

        # 决策
        decision = await self.decide(perception, prices, current_time)

        # 日志
        orders = decision.get("orders", [])
        if orders:
            order_summary = ", ".join(
                f"{o.get('action')} {o.get('stock_code')} {o.get('quantity')}" for o in orders
            )
            logger.info(f"[{self.name}] 决策: {order_summary}")
        else:
            logger.info(f"[{self.name}] 决策: hold")

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
