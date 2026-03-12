"""
市场数据 REST 路由
"""
from fastapi import APIRouter, Query
from backend.state import state

router = APIRouter(prefix="/api/market", tags=["市场数据"])


@router.get("/snapshot")
async def get_market_snapshot():
    """获取全市场最新行情"""
    return state.engine.get_market_snapshot()


@router.get("/klines/{stock_code}")
async def get_klines(stock_code: str, limit: int = Query(default=100, ge=1, le=500)):
    """获取某只股票的K线历史"""
    return state.engine.get_klines(stock_code, limit)


@router.get("/depth/{stock_code}")
async def get_depth(stock_code: str, levels: int = Query(default=5, ge=1, le=20)):
    """获取某只股票的盘口"""
    if stock_code not in state.engine.order_books:
        return {"buy": [], "sell": []}
    return state.engine.order_books[stock_code].get_depth(levels)
