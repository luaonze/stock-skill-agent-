# -*- coding: utf-8 -*-
# @Time    : 2026/5/19 12:01
# @Author  : Zery
# @File    : logger.py
# @Software: PyCharm

# utils/logger.py

"""
项目统一日志配置

使用方式：
    from utils.logger import logger

    logger.info("程序启动")
    logger.error("发生错误")
"""

import sys
from pathlib import Path
from loguru import logger

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent

# 日志目录
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

# 日志文件
LOG_FILE = LOG_DIR / "app.log"

# 移除 loguru 默认配置
logger.remove()

# 控制台输出
logger.add(
    sys.stdout,
    level="INFO",
    colorize=True,
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level:<8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    ),
)

# 文件输出（按天切分）
logger.add(
    LOG_FILE,
    level="DEBUG",
    rotation="1 day",      # 每天生成一个新文件
    retention="30 days",   # 保留30天
    encoding="utf-8",
    enqueue=True,
    format=(
        "{time:YYYY-MM-DD HH:mm:ss} | "
        "{level:<8} | "
        "{name}:{function}:{line} | "
        "{message}"
    ),
)

# 对外暴露的 logger 对象
__all__ = ["logger"]
