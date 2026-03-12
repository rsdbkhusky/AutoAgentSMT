"""
撮合引擎 - OrderBook 和 MarketEngine
"""
import uuid
import time
from dataclasses import dataclass, field


@dataclass
class OrderEntry:
    """挂单条目"""
    order_id: str
    agent_id: str
    side: str           # "buy" | "sell"
    price: float
    quantity: int
    remaining: int
    timestamp: float


class OrderBook:
    """单只股票的订单簿"""

    def __init__(self, stock_code: str, stock_name: str, initial_price: float, sector: str):
        self.stock_code = stock_code
        self.stock_name = stock_name
        self.sector = sector
        self.last_price = initial_price
        self.prev_close = initial_price  # 前收盘价，用于计算涨跌幅
        self.buy_orders: list[OrderEntry] = []   # 按价格降序
        self.sell_orders: list[OrderEntry] = []  # 按价格升序
        # 本回合统计
        self.open_price = initial_price
        self.high_price = initial_price
        self.low_price = initial_price
        self.period_volume = 0
        self.period_trades: list[dict] = []
        # 历史数据
        self.klines: list[dict] = []
        self.all_trades: list[dict] = []

    def add_order(self, order: OrderEntry, price_limit_pct: float) -> list[dict]:
        """添加订单并尝试撮合，返回成交列表"""
        # 涨跌停检查
        upper_limit = round(self.prev_close * (1 + price_limit_pct), 2)
        lower_limit = round(self.prev_close * (1 - price_limit_pct), 2)
        if order.price > upper_limit or order.price < lower_limit:
            return []

        # 插入订单簿
        if order.side == "buy":
            self.buy_orders.append(order)
            self.buy_orders.sort(key=lambda o: (-o.price, o.timestamp))
        else:
            self.sell_orders.append(order)
            self.sell_orders.sort(key=lambda o: (o.price, o.timestamp))

        # 撮合
        trades = self._match()
        return trades

    def _match(self) -> list[dict]:
        """价格优先、时间优先撮合"""
        trades = []
        while self.buy_orders and self.sell_orders:
            best_buy = self.buy_orders[0]
            best_sell = self.sell_orders[0]

            if best_buy.price < best_sell.price:
                break  # 无法成交

            # 成交价：先到的订单的价格
            trade_price = best_sell.price if best_sell.timestamp <= best_buy.timestamp else best_buy.price
            trade_qty = min(best_buy.remaining, best_sell.remaining)

            trade = {
                "trade_id": str(uuid.uuid4())[:8],
                "stock_code": self.stock_code,
                "price": trade_price,
                "quantity": trade_qty,
                "buyer_id": best_buy.agent_id,
                "seller_id": best_sell.agent_id,
                "buy_order_id": best_buy.order_id,
                "sell_order_id": best_sell.order_id,
            }
            trades.append(trade)
            self.all_trades.append(trade)
            self.period_trades.append(trade)

            # 更新价格统计
            self.last_price = trade_price
            self.high_price = max(self.high_price, trade_price)
            self.low_price = min(self.low_price, trade_price)
            self.period_volume += trade_qty

            # 更新剩余量
            best_buy.remaining -= trade_qty
            best_sell.remaining -= trade_qty
            if best_buy.remaining == 0:
                self.buy_orders.pop(0)
            if best_sell.remaining == 0:
                self.sell_orders.pop(0)

        return trades

    def get_depth(self, levels: int = 5) -> dict:
        """获取买卖N档盘口"""
        buy_depth = []
        sell_depth = []

        # 合并同价位
        buy_prices: dict[float, int] = {}
        for o in self.buy_orders:
            buy_prices[o.price] = buy_prices.get(o.price, 0) + o.remaining
        sell_prices: dict[float, int] = {}
        for o in self.sell_orders:
            sell_prices[o.price] = sell_prices.get(o.price, 0) + o.remaining

        for price in sorted(buy_prices.keys(), reverse=True)[:levels]:
            buy_depth.append({"price": price, "quantity": buy_prices[price]})
        for price in sorted(sell_prices.keys())[:levels]:
            sell_depth.append({"price": price, "quantity": sell_prices[price]})

        return {"buy": buy_depth, "sell": sell_depth}

    def aggregate_kline(self, virtual_timestamp: float, time_str: str) -> dict:
        """聚合本回合K线"""
        kline = {
            "timestamp": virtual_timestamp,
            "time_str": time_str,
            "open": self.open_price,
            "high": self.high_price,
            "low": self.low_price,
            "close": self.last_price,
            "volume": self.period_volume,
        }
        self.klines.append(kline)
        return kline

    def reset_period(self):
        """重置回合统计，开始新回合"""
        self.open_price = self.last_price
        self.high_price = self.last_price
        self.low_price = self.last_price
        self.period_volume = 0
        self.period_trades = []

    def get_quote(self) -> dict:
        """获取当前行情"""
        change_pct = ((self.last_price - self.prev_close) / self.prev_close * 100) if self.prev_close else 0
        best_ask = self.sell_orders[0].price if self.sell_orders else 0
        best_bid = self.buy_orders[0].price if self.buy_orders else 0
        return {
            "code": self.stock_code,
            "name": self.stock_name,
            "price": round(self.last_price, 2),
            "open_price": round(self.open_price, 2),
            "high_price": round(self.high_price, 2),
            "low_price": round(self.low_price, 2),
            "change_pct": round(change_pct, 2),
            "volume": self.period_volume,
            "sector": self.sector,
            "best_ask": round(best_ask, 2),
            "best_bid": round(best_bid, 2),
        }


class MarketEngine:
    """市场撮合引擎"""

    def __init__(self, config: dict, clock):
        self.order_books: dict[str, OrderBook] = {}
        self.clock = clock
        self.market_config = config["market"]
        self.stocks_config = config["stocks"]
        self.round_number = 0
        self.trade_history: list[dict] = []

    def initialize_stocks(self):
        """根据配置初始化所有股票的OrderBook，并创建做市商挂单提供流动性"""
        for stock in self.stocks_config:
            ob = OrderBook(
                stock_code=stock["code"],
                stock_name=stock["name"],
                initial_price=stock["initial_price"],
                sector=stock["sector"],
            )
            self.order_books[stock["code"]] = ob

        # 创建初始做市商挂单，提供流动性
        depth = self.market_config.get("initial_market_maker_depth", 5)
        mm_qty = self.market_config.get("market_maker_quantity", 1000)
        tick = self.market_config["price_tick"]
        for code, ob in self.order_books.items():
            base_price = ob.last_price
            for i in range(depth):
                # 卖单：从初始价格开始（i=0时等于base_price）
                sell_price = round(base_price + i * tick, 2)
                sell_order = OrderEntry(
                    order_id=f"mm_sell_{code}_{i}",
                    agent_id="__market_maker__",
                    side="sell",
                    price=sell_price,
                    quantity=mm_qty,
                    remaining=mm_qty,
                    timestamp=0,
                )
                ob.sell_orders.append(sell_order)
                # 买单：初始价格下方
                buy_price = round(base_price - (i + 1) * tick, 2)
                if buy_price > 0:
                    buy_order = OrderEntry(
                        order_id=f"mm_buy_{code}_{i}",
                        agent_id="__market_maker__",
                        side="buy",
                        price=buy_price,
                        quantity=mm_qty,
                        remaining=mm_qty,
                        timestamp=0,
                    )
                    ob.buy_orders.append(buy_order)
            # 排序
            ob.buy_orders.sort(key=lambda o: (-o.price, o.timestamp))
            ob.sell_orders.sort(key=lambda o: (o.price, o.timestamp))

    def submit_order(self, agent_id: str, stock_code: str, side: str,
                     price: float, quantity: int) -> dict:
        """提交订单，返回成交结果"""
        if stock_code not in self.order_books:
            return {"order_id": "", "trades": [], "status": "rejected", "message": f"股票 {stock_code} 不存在"}

        if quantity <= 0 or quantity > self.market_config["max_order_quantity"]:
            return {"order_id": "", "trades": [], "status": "rejected", "message": "委托数量不合法"}

        price = round(price, 2)
        if price <= 0:
            return {"order_id": "", "trades": [], "status": "rejected", "message": "委托价格不合法"}

        order_id = str(uuid.uuid4())[:8]
        order = OrderEntry(
            order_id=order_id,
            agent_id=agent_id,
            side=side,
            price=price,
            quantity=quantity,
            remaining=quantity,
            timestamp=self.clock.get_kline_timestamp(),
        )

        ob = self.order_books[stock_code]
        trades = ob.add_order(order, self.market_config["price_limit_pct"])
        self.trade_history.extend(trades)

        return {
            "order_id": order_id,
            "trades": trades,
            "status": "accepted",
            "message": f"订单已提交，成交{len(trades)}笔",
        }

    def get_market_snapshot(self) -> dict:
        """获取全市场行情快照"""
        stocks = {}
        for code, ob in self.order_books.items():
            stocks[code] = ob.get_quote()
        return {
            "round_number": self.clock.round_number,
            "virtual_time": self.clock.get_display_time(),
            "timestamp": self.clock.get_kline_timestamp(),
            "stocks": stocks,
        }

    def end_round(self) -> dict:
        """结束当前回合，聚合K线"""
        self.round_number += 1
        ts = self.clock.get_kline_timestamp()
        time_str = self.clock.get_display_time()

        round_summary = {
            "round_number": self.clock.round_number,
            "virtual_time": time_str,
            "klines": {},
            "total_trades": 0,
        }

        for code, ob in self.order_books.items():
            kline = ob.aggregate_kline(ts, time_str)
            round_summary["klines"][code] = kline
            round_summary["total_trades"] += len(ob.period_trades)
            ob.reset_period()

        return round_summary

    def get_klines(self, stock_code: str, limit: int = 100) -> list[dict]:
        """获取指定股票的K线历史"""
        if stock_code not in self.order_books:
            return []
        return self.order_books[stock_code].klines[-limit:]

    def get_prices(self) -> dict[str, float]:
        """获取所有股票当前价格"""
        return {code: ob.last_price for code, ob in self.order_books.items()}
