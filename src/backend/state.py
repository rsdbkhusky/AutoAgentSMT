"""
全局运行时状态容器
"""


class GlobalState:
    """全局状态单例，持有所有核心组件的引用"""

    def __init__(self):
        self.engine = None           # MarketEngine
        self.agent_manager = None    # AgentManager
        self.news_generator = None   # NewsGenerator
        self.llm = None              # BaseLLM
        self.clock = None            # VirtualClock
        self.ws_manager = None       # WSManager
        self.config = None           # 完整配置字典
        # 运行时状态
        self.paused = False
        self.running = False
        self.round_number = 0
        # 历史数据
        self.chat_messages: list[dict] = []
        self.news_history: list[dict] = []
        self.simulation_task = None  # asyncio.Task


# 全局单例
state = GlobalState()
