"""
Agent 记忆模块 - 短期事件记忆的滑动窗口
"""
import time


class Memory:
    """Agent 短期记忆，维护最近 N 条事件"""

    def __init__(self, max_events: int = 50):
        self.events: list[dict] = []
        self.max_events = max_events

    def add_event(self, event_type: str, content: str, metadata: dict = None):
        """添加事件到记忆"""
        event = {
            "timestamp": time.time(),
            "type": event_type,     # "trade" | "news" | "chat" | "decision" | "market"
            "content": content,
        }
        if metadata:
            event["metadata"] = metadata
        self.events.append(event)
        # 超限时移除最旧事件
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events:]

    def get_recent(self, n: int = 10, event_type: str = None) -> list[dict]:
        """获取最近 n 条事件，可按类型过滤"""
        if event_type:
            filtered = [e for e in self.events if e["type"] == event_type]
            return filtered[-n:]
        return self.events[-n:]

    def summarize(self) -> str:
        """将当前记忆压缩为文本摘要"""
        if not self.events:
            return "暂无历史记忆。"
        lines = []
        for event in self.events[-15:]:  # 只取最近15条
            lines.append(f"[{event['type']}] {event['content']}")
        return "\n".join(lines)
