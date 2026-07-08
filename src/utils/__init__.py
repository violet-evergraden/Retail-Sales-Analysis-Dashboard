"""日志工具模块"""
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


_loggers = {}


def setup_logger(
    name: str = "retail_dashboard",
    level: str = "INFO",
    log_format: Optional[str] = None,
    log_file: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
) -> logging.Logger:
    """
    配置并返回logger实例
    """
    if name in _loggers:
        return _loggers[name]

    if log_format is None:
        log_format = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # 控制台handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(logging.Formatter(log_format))
    logger.addHandler(console_handler)

    # 文件handler
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(log_format))
        logger.addHandler(file_handler)

    _loggers[name] = logger
    return logger


def get_logger(name: str = "retail_dashboard") -> logging.Logger:
    """获取已配置的logger，若不存在则创建默认配置"""
    if name not in _loggers:
        return setup_logger(name)
    return _loggers[name]
