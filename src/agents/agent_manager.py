"""
Agent 管理器 - 批量创建和并发调度 Agent
"""
import asyncio
import logging
import yaml
import os
from agents.agent import Agent

logger = logging.getLogger("agent_manager")


class AgentManager:
    """Agent 生命周期管理与并发调度"""

    def __init__(self, llm):
        self.agents: list[Agent] = []
        self.llm = llm

    def load_agents(self, agent_entries: list[dict], base_dir: str = "."):
        """根据配置加载所有Agent类型并实例化

        agent_entries 格式: [{"path": "config/agents/xxx.yaml", "count": 10}, ...]
        """
        for entry in agent_entries:
            config_path = os.path.join(base_dir, entry["path"])
            count = entry.get("count", 1)

            with open(config_path, "r", encoding="utf-8") as f:
                type_config = yaml.safe_load(f)

            type_id = type_config.get("type_id", "unknown")
            name_prefix = type_config.get("name_prefix", type_id)

            for i in range(1, count + 1):
                agent_id = f"{type_id}_{i:02d}"
                agent_name = f"{name_prefix}_{i:02d}"
                agent = Agent(
                    agent_id=agent_id,
                    name=agent_name,
                    config=type_config,
                    llm=self.llm,
                )
                self.agents.append(agent)

            logger.info(f"加载 Agent 类型 [{type_id}] × {count}，名称前缀: {name_prefix}")

        logger.info(f"共加载 {len(self.agents)} 个 Agent")

    async def run_round(self, market_snapshot: dict, news_list: list[dict],
                        recent_chat: list[dict], engine) -> list[dict]:
        """并发执行所有Agent的一轮操作"""
        tasks = [
            agent.run_round(market_snapshot, news_list, recent_chat, engine)
            for agent in self.agents
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        round_results = []
        for agent, result in zip(self.agents, results):
            if isinstance(result, Exception):
                logger.error(f"Agent [{agent.name}] 执行出错: {result}")
                continue
            round_results.append(result)

        return round_results

    def get_all_positions(self, prices: dict[str, float]) -> list[dict]:
        """返回所有Agent的持仓状态"""
        return [agent.to_position_dict(prices) for agent in self.agents]
