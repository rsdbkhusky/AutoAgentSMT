"""
数据模型定义 - 所有 Pydantic 模型集中于此
"""
from pydantic import BaseModel
from typing import Literal


class OrderRequest(BaseModel):
    """订单提交请求"""
    agent_id: str
    stock_code: str
    side: Literal["buy", "sell"]
    price: float
    quantity: int


class OrderResponse(BaseModel):
    """订单提交响应"""
    order_id: str
    trades: list[dict]
    status: str
    message: str


class StockQuote(BaseModel):
    """单只股票行情"""
    code: str
    name: str
    price: float
    open_price: float
    high_price: float
    low_price: float
    change_pct: float
    volume: int
    sector: str


class KlineBar(BaseModel):
    """K线数据"""
    timestamp: float
    time_str: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class ChatMessage(BaseModel):
    """群聊消息"""
    agent_id: str
    agent_name: str
    content: str
    round_number: int
    virtual_time: str
    timestamp: float


class NewsEvent(BaseModel):
    """新闻事件"""
    news_id: str
    title: str
    content: str
    sentiment: str
    affected_stocks: list[str]
    round_number: int
    virtual_time: str


class AgentPosition(BaseModel):
    """Agent持仓与资产"""
    agent_id: str
    agent_name: str
    agent_type: str
    cash: float
    positions: dict[str, int]
    total_value: float
    pnl_pct: float
