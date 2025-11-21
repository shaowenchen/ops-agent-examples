"""
SLO check modules
"""

import inspect
from typing import List, Type
from ..core.base_module import BaseModule
from ..core.orchestrator import Orchestrator
from ..utils.logging import get_logger

from .upstream_query.module import UpstreamQueryModule
from .error_log_query.module import ErrorLogQueryModule
from .llm_chat.module import LLMChatModule
from .xiezuo.module import XieZuoModule

__all__ = ['UpstreamQueryModule', 'ErrorLogQueryModule', 'LLMChatModule', 'XieZuoModule']

logger = get_logger(__name__)


def register_all_modules(orchestrator: Orchestrator) -> None:
    """
    自动发现并注册所有模块到编排器
    
    Args:
        orchestrator: 编排器实例
    """
    import sys
    # 获取当前模块
    current_module = sys.modules[__name__]
    
    # 从 __all__ 中获取所有模块类
    module_classes: List[Type[BaseModule]] = []
    
    # 方法1: 从 __all__ 获取所有模块类
    for name in __all__:
        module_class = getattr(current_module, name, None)
        if (inspect.isclass(module_class) and 
            issubclass(module_class, BaseModule) and 
            module_class is not BaseModule):
            module_classes.append(module_class)
    
    # 方法2: 自动发现所有 BaseModule 子类（作为补充，防止遗漏）
    for name in dir(current_module):
        if name.startswith('_') or name in __all__:
            continue
        obj = getattr(current_module, name)
        if (inspect.isclass(obj) and 
            issubclass(obj, BaseModule) and 
            obj is not BaseModule and
            obj not in module_classes):
            module_classes.append(obj)
    
    # 自动注册所有发现的模块
    for module_class in module_classes:
        try:
            module_instance = module_class()
            orchestrator.register_module(module_instance)
            logger.debug(f"Registered module: {module_instance.name}")
        except Exception as e:
            logger.warning(f"Failed to register module {module_class.__name__}: {e}")

