"""
Ops Agent - An intelligent operations agent powered by LangChain and MCP
"""

__version__ = "1.0.0"
__author__ = "Ops Team"

from .config import ConfigLoader
from .core.agent import OpsAgent

__all__ = ["ConfigLoader", "OpsAgent", "__version__"]

