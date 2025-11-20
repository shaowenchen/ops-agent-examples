"""
Logging utilities for Ops Agent SLO
"""

import sys
import logging
import colorlog
from typing import Optional


def setup_logging(log_level: str = "INFO"):
    """
    Setup logging configuration
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler with colored formatter
    console_handler = logging.StreamHandler(sys.stdout)
    
    # Define log format
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    colored_log_format = "%(log_color)s" + log_format
    
    # Create color formatter
    color_formatter = colorlog.ColoredFormatter(
        colored_log_format,
        datefmt="%Y-%m-%d %H:%M:%S",
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    )
    
    # Set formatter for console handler
    console_handler.setFormatter(color_formatter)
    
    # Add console handler to root logger
    root_logger.addHandler(console_handler)


def get_logger(name: str, log_level: Optional[str] = None) -> logging.Logger:
    """
    Get a logger with the specified name
    
    Args:
        name: Logger name
        log_level: Optional log level to override the default
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # If log level is specified, override the default
    if log_level:
        logger.setLevel(getattr(logging, log_level.upper()))
    
    return logger

