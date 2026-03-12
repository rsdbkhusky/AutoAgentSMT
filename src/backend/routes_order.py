"""
订单 REST 路由
"""
from fastapi import APIRouter, Query
from backend.state import state
from backend.models import OrderRequest

router = APIRouter(prefix="/api/orders", tags=["订单"])


@router.post("")
async def submit_order(order: OrderRequest):
    """提交订单"""
    result = state.engine.submit_order(
        agent_id=order.agent_id,
        stock_code=order.stock_code,
        side=order.side,
        price=order.price,
        quantity=order.quantity,
    )
    # 如果有成交，通过 WebSocket 广播
    for trade in result.get("trades", []):
        await state.ws_manager.broadcast("trade", trade)
    return result


@router.get("/history")
async def get_trade_history(stock_code: str = Query(default=""),
                            limit: int = Query(default=50, ge=1, le=500)):
    """查询成交历史"""
    trades = state.engine.trade_history
    if stock_code:
        trades = [t for t in trades if t.get("stock_code") == stock_code]
    return trades[-limit:]
