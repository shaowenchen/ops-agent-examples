"""
Logging utilities for Ops Agent
"""

import logging
import colorlog
from typing import Optional


def setup_logging(level: str = "INFO") -> None:
    """
    Setup colored logging
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    handler = colorlog.StreamHandler()
    handler.setFormatter(colorlog.ColoredFormatter(
        '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    ))
    
    logger = logging.getLogger()
    logger.handlers.clear()  # Clear existing handlers
    logger.addHandler(handler)
    logger.setLevel(getattr(logging, level.upper()))


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)

