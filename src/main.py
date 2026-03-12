"""
多Agent虚拟股市交易模拟系统 - 入口文件
用法: python src/main.py --config config/main.yaml
"""
import argparse
import logging
import os
import sys
import yaml
import uvicorn
from datetime import datetime

# 将 src/ 加入模块搜索路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.clock import VirtualClock
from backend.market_engine import MarketEngine
from backend.ws_manager import WSManager
from backend.state import state
from backend.app import create_app
from services.llm_client import BaseLLM
from services.news_generator import NewsGenerator
from agents.agent_manager import AgentManager


def setup_logging(level: str = "info"):
    """配置日志，同时输出到终端和日志文件"""
    log_level = getattr(logging, level.upper(), logging.INFO)
    fmt = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
    datefmt = "%H:%M:%S"

    # 创建日志目录
    src_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(src_dir)
    log_dir = os.path.join(project_root, "log")
    os.makedirs(log_dir, exist_ok=True)

    # 生成日志文件名：log_YYMMDDHHMMSS.txt
    log_filename = f"log_{datetime.now().strftime('%y%m%d%H%M%S')}.txt"
    log_path = os.path.join(log_dir, log_filename)

    # 配置根 logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    formatter = logging.Formatter(fmt, datefmt=datefmt)

    # 终端输出
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 文件输出
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    logging.getLogger("main").info(f"日志文件: {log_path}")


def main():
    # 1. 解析命令行参数
    parser = argparse.ArgumentParser(description="多Agent虚拟股市交易模拟系统")
    parser.add_argument("--config", required=True, help="主配置文件路径")
    args = parser.parse_args()

    # 2. 读取配置
    config_path = os.path.abspath(args.config)
    base_dir = os.path.dirname(config_path)
    # 计算项目根目录（config文件所在目录的父目录）
    project_root = os.path.dirname(base_dir)

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # 3. 配置日志
    setup_logging(config.get("system", {}).get("log_level", "info"))
    logger = logging.getLogger("main")
    logger.info("配置加载完成")

    # 4. 创建虚拟时钟
    clock = VirtualClock(config["clock"])
    logger.info(f"虚拟时钟初始化: {clock.get_display_time()}")

    # 5. 创建 LLM 客户端
    llm = BaseLLM(config["llm"])
    logger.info(f"LLM 客户端初始化: {config['llm']['model']}")

    # 6. 创建撮合引擎
    engine = MarketEngine(config, clock)
    engine.initialize_stocks()
    logger.info(f"撮合引擎初始化: {len(engine.order_books)} 只股票")

    # 7. 创建 Agent 管理器
    agent_mgr = AgentManager(llm)
    agent_mgr.load_agents(config["agents"], base_dir=project_root)
    logger.info(f"Agent 管理器初始化: {len(agent_mgr.agents)} 个 Agent")

    # 8. 创建新闻生成器
    news_gen = NewsGenerator(llm, config["stocks"])
    logger.info("新闻生成器初始化完成")

    # 9. 注册全局状态
    state.engine = engine
    state.agent_manager = agent_mgr
    state.news_generator = news_gen
    state.llm = llm
    state.clock = clock
    state.ws_manager = WSManager()
    state.config = config

    # 10. 创建并启动 FastAPI 应用
    app = create_app()
    host = config.get("system", {}).get("host", "0.0.0.0")
    port = config.get("system", {}).get("port", 8000)

    logger.info(f"启动服务: http://{host}:{port}")
    logger.info(f"Swagger 文档: http://{host}:{port}/docs")

    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    main()
