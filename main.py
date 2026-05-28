# -*- coding: utf-8 -*-
# main.py

"""
命令行入口。

常用方式：
    python3 main.py
    python3 main.py --model MiMo-V2.5-Pro --llm-mode chat
    python3 main.py --skills-dir ./skills
"""

import argparse
from pathlib import Path
from typing import Optional

from agents.config import AppConfig
from agents.root_agent import StockAnalysisAgent


def parse_args() -> argparse.Namespace:
    """
    解析命令行参数。

    参数优先级：命令行参数 > .env 配置 > 代码默认值。
    """
    parser = argparse.ArgumentParser(description="股票分析 Agent 命令行入口")
    parser.add_argument("--model", help="分析模型名称，例如 gpt-5.4 或 MiMo-V2.5-Pro")
    parser.add_argument("--router-model", help="技能路由模型名称；不填则使用分析模型")
    parser.add_argument("--llm-mode", choices=["responses", "chat"], help="模型调用模式")
    parser.add_argument("--skills-dir", help="技能目录，默认读取 AGENT_SKILLS_DIR 或 ./skills")
    return parser.parse_args()


def optional_path(path: Optional[str]) -> Optional[Path]:
    """
    将可选路径字符串转成 Path。
    """
    return Path(path).expanduser() if path else None


def main() -> None:
    """
    创建 Agent 并进入连续对话。
    """
    args = parse_args()
    config = AppConfig.from_env()
    agent = StockAnalysisAgent(
        config=config,
        model=args.model,
        router_model=args.router_model,
        skills_dir=optional_path(args.skills_dir),
        llm_mode=args.llm_mode,
    )

    while True:
        user_input = input("请输入您的问题（输入 'exit' 退出）：").strip()
        if user_input.lower() in {"exit", "quit", "q"}:
            print("退出对话。")
            break

        answer = agent.chat(user_input)
        print(f"\n助手回复:\n{answer}\n")


if __name__ == "__main__":
    main()
