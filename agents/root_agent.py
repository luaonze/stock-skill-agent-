# -*- coding: utf-8 -*-
# @Time    : 2026/5/18 20:51
# @Author  : Zery
# @File    : root_agent.py
# @Software: PyCharm
# agents/root_agent.py

"""
股票分析 Agent 主流程。

本文件只组织业务流程：
用户输入 -> 选择技能 -> 激活技能 -> 调用模型 -> 返回结果
"""

import json
from dataclasses import replace
from pathlib import Path
from typing import Dict, List, Optional

from agents.config import AppConfig
from agents.llm import LLMClient
from agents.skill_manager import SkillManager
from utils.logger import logger


# Agent 的基础身份提示：负责执行分析，不负责自己发明技能。
AGENT_SYSTEM_PROMPT = """
你是一个股票分析执行器。

你的职责：
1. 严格根据已经激活的 skill 内容执行分析。
2. 保持专业、克制、结构化的股票研究风格。
3. 区分事实、推测、风险和结论。

你的限制：
1. 你不会自己选择 skill。
2. 你不会调用外部工具。
3. 如果用户没有提供实时行情或关键数据，不得编造最新价格、成交量、涨跌幅、财报或新闻。
4. 不得承诺收益，不得使用“必涨”“稳赚”“一定”等绝对化表述。

输出要求：
1. 严格遵循当前 skill 的规则和输出格式。
2. 先给核心结论，再给分析逻辑和风险。
3. 如果信息不足，先说明缺少哪些数据，再给条件分析。
"""


# 技能路由提示：让模型只从当前 skills 目录中选择一个技能名称。
SKILL_ROUTER_PROMPT = """
你是一个技能路由器（Skill Router）。

你的唯一任务是根据用户问题选择最合适的 skill。
你不负责回答用户问题，也不负责解释原因。

当前可用技能：
{skills_list}

选择规则：
1. 如果用户问新闻事件、公司公告、行业政策、基本面、估值、市场情绪、资金偏好对股票的影响，选择 stock-analyst。
2. 如果用户问股价走势、K 线、支撑压力、均线、MACD、RSI、成交量、买卖点、止损位，选择 stock-price-analyst。
3. 如果问题同时包含基本面和技术面，优先判断用户最想解决的问题；无法判断时选择 stock-analyst。

输出要求：
1. 只返回 skill name
2. 不要返回解释
3. 必须完全匹配技能名称
4. 不要返回 Markdown
5. 不要返回标点符号

用户问题：
{user_input}
"""


class StockAnalysisAgent:
    """
    股票分析 Agent。

    职责边界：
    - 不直接管理 API Key / base_url，这些交给 AppConfig。
    - 不直接解析 SKILL.md，这些交给 SkillManager。
    - 不关心模型底层接口，这些交给 LLMClient。
    """

    def __init__(
        self,
        config: Optional[AppConfig] = None,
        model: Optional[str] = None,
        router_model: Optional[str] = None,
        skills_dir: Optional[Path] = None,
        llm_mode: Optional[str] = None,
    ):
        # 支持从代码参数临时覆盖 .env 配置，方便测试或命令行指定模型。
        base_config = config or AppConfig.from_env()
        self.config = replace(
            base_config,
            default_model=model or base_config.default_model,
            router_model=router_model or base_config.router_model,
            skills_dir=Path(skills_dir) if skills_dir else base_config.skills_dir,
            llm_mode=llm_mode or base_config.llm_mode,
        )

        # 初始化核心组件。
        self.llm = LLMClient(config=self.config)
        self.skill_manager = SkillManager(str(self.config.skills_dir))
        self.active_skill_name: Optional[str] = None
        self.messages: List[Dict[str, str]] = self._build_initial_messages()

    def chat(self, user_input: str, model: Optional[str] = None) -> str:
        """
        对话主入口。

        流程：
        1. 清理用户输入。
        2. 自动选择最合适的 skill。
        3. 激活 skill，将技能说明加入系统上下文。
        4. 调用模型生成回答。
        """
        clean_input = user_input.strip()
        if not clean_input:
            return "请输入有效问题。"

        skill_name = self.route_skill(clean_input, model=model)
        self.activate_skill(skill_name)
        return self.generate_answer(clean_input, model=model)

    def route_skill(self, user_input: str, model: Optional[str] = None) -> str:
        """
        技能路由：让模型从当前可用技能中选出一个 skill name。
        """
        skills_text = self.skill_manager.select_skill()
        if not skills_text:
            raise RuntimeError(f"未发现可用技能，请检查技能目录: {self.config.skills_dir}")

        prompt = SKILL_ROUTER_PROMPT.format(
            skills_list=skills_text,
            user_input=user_input,
        ).strip()

        # 路由模型可独立配置；未配置时使用本次指定模型或默认模型。
        selected_model = self.config.router_model or model or self.config.default_model
        response = self.llm.generate_response(messages=prompt, model=selected_model)
        skill_name = self._normalize_skill_name(response.get("content", ""))

        if skill_name not in self.skill_manager.skills:
            fallback_skill = next(iter(self.skill_manager.skills))
            logger.warning(f"模型返回未知技能: {skill_name}，使用默认技能: {fallback_skill}")
            return fallback_skill

        logger.info(f"选择技能: {skill_name}")
        return skill_name

    def activate_skill(self, skill_name: str) -> None:
        """
        激活指定技能：读取 SKILL.md 完整内容，并注入 system message。
        """
        if skill_name == self.active_skill_name:
            logger.info(f"技能 {skill_name} 已激活，无需重复注入。")
            return

        skill_content = self.skill_manager.activate_skill(skill_name)
        if not skill_content:
            logger.warning(f"技能 {skill_name} 内容为空，跳过激活。")
            return

        if not isinstance(skill_content, str):
            skill_content = json.dumps(skill_content, ensure_ascii=False)

        self._replace_skill_system_message(skill_content)
        self.active_skill_name = skill_name
        logger.info(f"已激活技能: {skill_name}")

    def generate_answer(self, user_input: str, model: Optional[str] = None) -> str:
        """
        调用模型生成最终回答，并保存多轮对话上下文。
        """
        self.messages.append({"role": "user", "content": user_input})

        response = self.llm.generate_response(
            messages=self.messages,
            model=model or self.config.default_model,
        )
        answer = response.get("content", "")
        self.messages.append({"role": "assistant", "content": answer})

        self._log_usage(response.get("usage", {}))
        return answer

    def reset(self) -> None:
        """
        重置对话上下文，清空已激活技能和历史消息。
        """
        self.active_skill_name = None
        self.messages = self._build_initial_messages()

    # 下面三个方法保留旧接口，避免之前写法直接失效。
    def Single_Conversation(self, user_input: str, model: Optional[str] = None) -> str:
        """旧接口兼容：单次对话。"""
        return self.chat(user_input, model=model)

    async def loop_Conversation(self, user_input: str, model: Optional[str] = None) -> str:
        """旧接口兼容：多轮对话。"""
        return self.chat(user_input, model=model)

    async def Conversation(self, user_input: str, model: Optional[str] = None) -> str:
        """旧接口兼容：对话入口。"""
        return self.chat(user_input, model=model)

    @staticmethod
    def _build_initial_messages() -> List[Dict[str, str]]:
        """
        构建初始系统消息。
        """
        return [{"role": "system", "content": AGENT_SYSTEM_PROMPT.strip()}]

    def _replace_skill_system_message(self, skill_content: str) -> None:
        """
        替换当前技能提示，避免多个 skill 的规则同时影响模型输出。
        """
        base_prompt = AGENT_SYSTEM_PROMPT.strip()
        history_messages = [
            message
            for message in self.messages
            if message.get("role") != "system"
        ]
        self.messages = [
            {"role": "system", "content": base_prompt},
            {"role": "system", "content": skill_content},
            *history_messages,
        ]

    @staticmethod
    def _normalize_skill_name(raw_name: str) -> str:
        """
        清理模型返回的技能名称，去掉引号、代码块符号和多余换行。
        """
        lines = raw_name.strip().strip("`").strip('"').strip("'").splitlines()
        return lines[0].strip() if lines else ""

    @staticmethod
    def _log_usage(usage: Dict[str, Optional[int]]) -> None:
        """
        记录 token 使用情况，方便排查成本和上下文长度问题。
        """
        logger.info(
            "token_usage "
            f"input={usage.get('input_tokens')} "
            f"output={usage.get('output_tokens')} "
            f"total={usage.get('total_tokens')}"
        )
