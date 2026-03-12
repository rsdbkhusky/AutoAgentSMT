"""
WebSocket 连接管理器 - 负责广播实时事件到前端
"""
import json
import logging
from fastapi import WebSocket

logger = logging.getLogger("ws_manager")


class WSManager:
    """WebSocket 连接管理与事件广播"""

    def __init__(self):
        self.connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        """接受并注册 WebSocket 连接"""
        await ws.accept()
        self.connections.append(ws)
        logger.info(f"WebSocket 连接建立，当前连接数: {len(self.connections)}")

    async def disconnect(self, ws: WebSocket):
        """移除断开的连接"""
        if ws in self.connections:
            self.connections.remove(ws)
        logger.info(f"WebSocket 连接断开，当前连接数: {len(self.connections)}")

    async def broadcast(self, event_type: str, data: dict):
        """向所有已连接客户端广播事件"""
        if not self.connections:
            return
        message = json.dumps({"type": event_type, "data": data}, ensure_ascii=False, default=str)
        dead = []
        for ws in self.connections:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            if ws in self.connections:
                self.connections.remove(ws)
