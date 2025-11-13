# -*- coding: utf-8 -*-
"""
日志工具
"""

import logging
import sys
from pathlib import Path
from typing import Optional

# 全局日志配置状态
_logging_configured = False


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None
):
    """
    设置日志配置
    
    Args:
        level: 日志级别
        log_file: 日志文件路径
    """
    global _logging_configured
    
    if _logging_configured:
        return
    
    # 设置日志格式
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # 设置日志级别
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # 清除现有的处理器
    root_logger.handlers.clear()
    
    # 创建格式器
    formatter = logging.Formatter(log_format, date_format)
    
    # 配置控制台输出
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 如果指定了日志文件，配置文件输出
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    _logging_configured = True


def get_logger(name: str) -> logging.Logger:
    """
    获取日志记录器
    
    Args:
        name: 日志记录器名称
        
    Returns:
        日志记录器对象
    """
    # 如果日志还未配置，使用默认配置
    if not _logging_configured:
        setup_logging()
    
    return logging.getLogger(name)

