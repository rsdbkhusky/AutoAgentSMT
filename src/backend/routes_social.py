"""
社交和新闻 REST 路由
"""
from fastapi import APIRouter, Query
from backend.state import state

router = APIRouter(tags=["社交与新闻"])


@router.get("/api/social/messages")
async def get_chat_messages(limit: int = Query(default=50, ge=1, le=500)):
    """获取群聊历史消息"""
    return state.chat_messages[-limit:]


@router.get("/api/news")
async def get_news(limit: int = Query(default=20, ge=1, le=100)):
    """获取新闻列表"""
    return state.news_history[-limit:]


@router.get("/api/agents/positions")
async def get_agent_positions():
    """获取所有Agent持仓"""
    prices = state.engine.get_prices()
    return state.agent_manager.get_all_positions(prices)


@router.get("/api/status")
async def get_status():
    """获取模拟运行状态"""
    return {
        "round_number": state.clock.round_number,
        "virtual_time": state.clock.get_display_time(),
        "status": "paused" if state.paused else ("running" if state.running else "stopped"),
        "agent_count": len(state.agent_manager.agents),
        "stock_count": len(state.engine.order_books),
        "total_trades": len(state.engine.trade_history),
    }


@router.post("/api/control/pause")
async def pause_simulation():
    """暂停模拟"""
    state.paused = True
    return {"status": "paused"}


@router.post("/api/control/resume")
async def resume_simulation():
    """恢复模拟"""
    state.paused = False
    return {"status": "running"}
