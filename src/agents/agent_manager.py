"""
Agent 管理器 - 批量创建和并发调度 Agent
"""
import asyncio
import logging
import math
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
                agent_name = f"{name_prefix}_{i:02d}" if count > 1 else name_prefix
                agent = Agent(
                    agent_id=agent_id,
                    name=agent_name,
                    config=type_config,
                    llm=self.llm,
                )
                self.agents.append(agent)

            logger.info(f"加载 Agent 类型 [{type_id}] × {count}，名称前缀: {name_prefix}")

        logger.info(f"共加载 {len(self.agents)} 个 Agent")

    def distribute_initial_shares(self, stocks_config: list[dict]):
        """初始分配股票：模拟 IPO，所有 Agent 按资金比例认购全部流通股

        如果所有 Agent 的总资金不足以买下全部股票，则等比例缩减流通股数量，
        多余部分视为限售股（不参与交易），使流通股总价值 = Agent 总资金。
        """
        if not self.agents or not stocks_config:
            return

        total_cash = sum(agent.cash for agent in self.agents)
        total_stock_value = sum(s["initial_price"] * s["total_shares"] for s in stocks_config)

        # 计算流通比例
        if total_cash < total_stock_value:
            ratio = total_cash / total_stock_value
            logger.warning(
                f"Agent 总资金 ¥{total_cash:,.0f} 不足以购买全部股本 ¥{total_stock_value:,.0f}，"
                f"流通比例调整为 {ratio:.2%}，其余视为限售股"
            )
        else:
            ratio = 1.0
            logger.info(f"Agent 总资金 ¥{total_cash:,.0f}，股票总价值 ¥{total_stock_value:,.0f}，全部流通")

        # 对每只股票进行分配
        for stock in stocks_config:
            code = stock["code"]
            price = stock["initial_price"]
            total_shares = stock["total_shares"]
            circulating = int(total_shares * ratio)

            if circulating != total_shares:
                locked = total_shares - circulating
                logger.info(f"  {stock['name']}({code}): 总股本 {total_shares}，"
                            f"流通股 {circulating}，限售股 {locked}")

            # 按资金比例分配给各 Agent
            distributed = 0
            for agent in self.agents:
                share_count = int(circulating * agent.initial_cash / total_cash)
                cost = round(share_count * price, 2)
                agent.cash -= cost
                if share_count > 0:
                    agent.positions[code] = agent.positions.get(code, 0) + share_count
                distributed += share_count

            # 剩余零头分配给现金最多的 Agent
            remainder = circulating - distributed
            if remainder > 0:
                agents_by_cash = sorted(self.agents, key=lambda a: a.cash, reverse=True)
                for i in range(remainder):
                    agent = agents_by_cash[i % len(agents_by_cash)]
                    agent.cash -= price
                    agent.positions[code] = agent.positions.get(code, 0) + 1

        # 汇总日志
        total_spent = sum(agent.initial_cash - agent.cash for agent in self.agents)
        logger.info(f"初始分配完成：共花费 ¥{total_spent:,.0f}，"
                    f"Agent 剩余总现金 ¥{sum(a.cash for a in self.agents):,.0f}")

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
