"""
虚拟时钟 - 管理模拟市场时间的推进
"""
from datetime import datetime, timedelta, time as dtime


class VirtualClock:
    """虚拟时钟，模拟股市交易时间"""

    def __init__(self, config: dict):
        self.current_time = datetime.strptime(config["start_time"], "%Y-%m-%d %H:%M:%S")
        self.time_step = timedelta(minutes=config["time_step_minutes"])
        # 解析交易时段
        self.trading_sessions = []
        for session in config["trading_sessions"]:
            start = datetime.strptime(session[0], "%H:%M").time()
            end = datetime.strptime(session[1], "%H:%M").time()
            self.trading_sessions.append((start, end))
        self.round_number = 0

    def tick(self) -> datetime:
        """推进一个时间步，自动跳过非交易时段和周末"""
        self.round_number += 1
        self.current_time += self.time_step
        # 跳过非交易时段
        while not self._is_trading_time():
            self._skip_to_next_session()
        return self.current_time

    def _is_trading_time(self) -> bool:
        """检查当前时间是否在交易时段内"""
        # 跳过周末（周六=5, 周日=6）
        if self.current_time.weekday() >= 5:
            return False
        current = self.current_time.time()
        for start, end in self.trading_sessions:
            if start <= current < end:
                return True
        return False

    def _skip_to_next_session(self):
        """跳转到下一个交易时段的开始"""
        current = self.current_time.time()
        # 查找当天后续的交易时段
        for start, _end in self.trading_sessions:
            if current < start:
                # 跳到这个时段的开始
                self.current_time = self.current_time.replace(
                    hour=start.hour, minute=start.minute, second=0, microsecond=0
                )
                return
        # 当天没有后续时段，跳到下一个工作日的第一个时段
        self.current_time += timedelta(days=1)
        # 跳过周末
        while self.current_time.weekday() >= 5:
            self.current_time += timedelta(days=1)
        first_start = self.trading_sessions[0][0]
        self.current_time = self.current_time.replace(
            hour=first_start.hour, minute=first_start.minute, second=0, microsecond=0
        )

    def get_display_time(self) -> str:
        """格式化显示虚拟时间"""
        return self.current_time.strftime("%Y-%m-%d %H:%M")

    def get_current_date(self) -> str:
        """获取当前交易日"""
        return self.current_time.strftime("%Y-%m-%d")

    def get_kline_timestamp(self) -> float:
        """返回用于K线图的Unix时间戳"""
        return self.current_time.timestamp()

    def to_dict(self) -> dict:
        """序列化为字典"""
        return {
            "current_time": self.get_display_time(),
            "current_date": self.get_current_date(),
            "round_number": self.round_number,
            "timestamp": self.get_kline_timestamp(),
        }
