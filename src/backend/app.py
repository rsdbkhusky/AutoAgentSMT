"""
FastAPI 应用工厂
"""
import asyncio
import time
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from backend.state import state
from backend.routes_market import router as market_router
from backend.routes_order import router as order_router
from backend.routes_social import router as social_router

logger = logging.getLogger("app")


async def simulation_loop():
    """模拟主循环"""
    config = state.config
    sim_config = config["simulation"]
    total_rounds = sim_config["total_rounds"]
    interval = sim_config["round_interval_seconds"]
    news_freq = sim_config["news_frequency"]

    state.running = True
    logger.info("模拟主循环启动")

    while state.clock.round_number < total_rounds:
        # 暂停检查
        if state.paused:
            await asyncio.sleep(0.5)
            continue

        # 推进虚拟时间
        state.clock.tick()
        round_num = state.clock.round_number

        # 广播回合开始
        await state.ws_manager.broadcast("round_start", {
            "round_number": round_num,
            "virtual_time": state.clock.get_display_time(),
        })

        # 按频率生成新闻
        news_list = []
        if round_num % news_freq == 0:
            try:
                snapshot = state.engine.get_market_snapshot()
                news_list = await state.news_generator.generate(
                    snapshot, round_num, state.clock.get_display_time()
                )
                for news in news_list:
                    state.news_history.append(news)
                    await state.ws_manager.broadcast("news", news)
            except Exception as e:
                logger.error(f"新闻生成失败: {e}")

        # 获取市场快照
        snapshot = state.engine.get_market_snapshot()
        recent_chat = state.chat_messages[-20:]

        # 所有 Agent 并发决策
        try:
            results = await state.agent_manager.run_round(
                snapshot, news_list, recent_chat, state.engine
            )

            # 处理 Agent 的群聊发言
            for result in results:
                chat_msg = result.get("chat_message", "")
                if chat_msg and chat_msg.strip():
                    msg = {
                        "agent_id": result["agent_id"],
                        "agent_name": result["agent_name"],
                        "content": chat_msg,
                        "round_number": round_num,
                        "virtual_time": state.clock.get_display_time(),
                        "timestamp": time.time(),
                    }
                    state.chat_messages.append(msg)
                    await state.ws_manager.broadcast("chat", msg)

                # 广播成交
                trade_results = result.get("trade_results", [])
                for trade_result in trade_results:
                    if trade_result and trade_result.get("trades"):
                        for trade in trade_result["trades"]:
                            await state.ws_manager.broadcast("trade", trade)

        except Exception as e:
            logger.error(f"Agent 回合执行失败: {e}")

        # 结束回合，聚合K线
        round_summary = state.engine.end_round()

        # 广播市场更新
        await state.ws_manager.broadcast("market_update", state.engine.get_market_snapshot())

        # 广播 Agent 持仓
        prices = state.engine.get_prices()
        positions = state.agent_manager.get_all_positions(prices)
        await state.ws_manager.broadcast("agent_update", positions)

        # 广播回合结束
        await state.ws_manager.broadcast("round_end", {
            "round_number": round_num,
            "virtual_time": state.clock.get_display_time(),
            "total_trades": round_summary["total_trades"],
        })

        logger.info(f"回合 {round_num} 完成 | 时间 {state.clock.get_display_time()} | "
                     f"成交 {round_summary['total_trades']} 笔")

        await asyncio.sleep(interval)

    state.running = False
    logger.info("模拟结束")


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # 启动
        if state.config["simulation"].get("auto_start", True):
            state.simulation_task = asyncio.create_task(simulation_loop())
            logger.info("模拟主循环已作为后台任务启动")
        yield
        # 关闭
        if state.simulation_task:
            state.simulation_task.cancel()

    app = FastAPI(title="多Agent虚拟股市交易模拟系统", lifespan=lifespan)

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由
    app.include_router(market_router)
    app.include_router(order_router)
    app.include_router(social_router)

    # WebSocket 端点
    @app.websocket("/ws")
    async def websocket_endpoint(ws: WebSocket):
        await state.ws_manager.connect(ws)
        try:
            while True:
                await ws.receive_text()  # 保持连接
        except WebSocketDisconnect:
            await state.ws_manager.disconnect(ws)

    return app
