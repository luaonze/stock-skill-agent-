# -*- coding: utf-8 -*-
# @File    : config.py
# agents/config.py

"""
项目配置集中管理。

所有可变配置都优先从环境变量读取，代码里只保留默认值。
这样后续切换模型、API 地址、技能目录时，不需要修改业务代码。
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import dotenv


# 项目根目录：以当前文件位置反推，避免写死本机绝对路径。
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"


def load_env_file(env_file: Path = ENV_FILE) -> None:
    """
    加载 .env 文件。

    使用 python-dotenv 读取项目根目录下的 .env。
    """
    dotenv.load_dotenv(env_file)


def get_env_value(*names: str, default: Optional[str] = None) -> Optional[str]:
    """
    按顺序读取多个环境变量。

    例如同时兼容 OPENAI_API_KEY 和 OPENAI_API_KEY_1。
    """
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return default


def get_env_by_pointer(pointer_name: str, *fallback_names: str) -> Optional[str]:
    """
    支持“用一个环境变量指定另一个环境变量名”。

    示例：
        AGENT_API_KEY_ENV=OPENAI_API_KEY_1
        程序会实际读取 OPENAI_API_KEY_1 的值。
    """
    pointed_name = os.getenv(pointer_name)
    if pointed_name:
        return os.getenv(pointed_name)
    return get_env_value(*fallback_names)


def normalize_base_url(base_url: str) -> str:
    """
    统一 base_url 格式，自动补齐 /v1。
    """
    clean_url = base_url.rstrip("/")
    return clean_url if clean_url.endswith("/v1") else f"{clean_url}/v1"


def resolve_project_path(raw_path: str) -> Path:
    """
    解析项目路径。

    绝对路径直接使用；相对路径默认相对项目根目录。
    """
    path = Path(raw_path).expanduser()
    return path if path.is_absolute() else PROJECT_ROOT / path


@dataclass
class AppConfig:
    """
    应用运行配置。

    你最常改的配置：
    - default_model：默认分析模型
    - router_model：技能路由模型；为空时使用 default_model
    - llm_mode：responses 或 chat
    - skills_dir：技能目录
    """

    api_key: Optional[str]
    base_url: str
    default_model: str
    router_model: Optional[str]
    llm_mode: str
    skills_dir: Path
    max_completion_tokens: int
    temperature: float
    top_p: float

    @classmethod
    def from_env(cls) -> "AppConfig":
        """
        从 .env / 系统环境变量创建配置。
        """
        load_env_file()

        base_url = get_env_by_pointer(
            "AGENT_BASE_URL_ENV",
            "AGENT_BASE_URL",
            "OPENAI_BASE_URL",
            "OPENAI_BASE_URL_1",
        ) or "https://api.openai.com/v1"
        skills_dir = resolve_project_path(os.getenv("AGENT_SKILLS_DIR", "skills"))

        return cls(
            api_key=get_env_by_pointer(
                "AGENT_API_KEY_ENV",
                "AGENT_API_KEY",
                "OPENAI_API_KEY",
                "OPENAI_API_KEY_1",
            ),
            base_url=normalize_base_url(base_url or "https://api.openai.com/v1"),
            default_model=os.getenv("AGENT_MODEL", "gpt-5.4"),
            router_model=os.getenv("AGENT_ROUTER_MODEL"),
            llm_mode=os.getenv("AGENT_LLM_MODE", "responses").lower(),
            skills_dir=skills_dir.expanduser(),
            max_completion_tokens=int(os.getenv("AGENT_MAX_COMPLETION_TOKENS", "2048")),
            temperature=float(os.getenv("AGENT_TEMPERATURE", "1.0")),
            top_p=float(os.getenv("AGENT_TOP_P", "0.95")),
        )
