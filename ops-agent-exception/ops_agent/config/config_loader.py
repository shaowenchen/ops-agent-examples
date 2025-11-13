# -*- coding: utf-8 -*-
"""
配置加载器 - 加载异常分析框架的配置
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class MCPConfig:
    """MCP 服务器配置"""
    server_url: str
    timeout: str
    token: str


@dataclass
class LLMConfig:
    """LLM 配置"""
    api_key: str
    api_host: str
    model: str
    max_tokens: Optional[int] = None


class ConfigLoader:
    """配置加载器"""
    
    def __init__(self, config_file: str = None):
        """
        初始化配置加载器
        
        Args:
            config_file: 配置文件路径
        """
        if config_file:
            self.config_path = config_file
        else:
            self.config_path = os.path.join(
                os.path.dirname(__file__), "../../configs/config.yaml"
            )
        
        # 加载主配置
        self.config = self._load_config()
        
        # 初始化各配置
        self.mcp_config = self._load_mcp_config()
        self.llm_config = self._load_llm_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """
        加载主配置文件
        
        Returns:
            配置字典
        """
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            return config or {}
        except FileNotFoundError:
            raise ValueError(f"配置文件不存在: {self.config_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"配置文件格式错误: {str(e)}")
        except Exception as e:
            raise ValueError(f"加载配置文件失败: {str(e)}")
    
    def _load_mcp_config(self) -> MCPConfig:
        """
        加载 MCP 配置
        
        Returns:
            MCP 配置对象
        """
        mcp_config = self.config.get("mcp", {})
        
        # 支持环境变量覆盖，环境变量优先级高于配置文件
        # 环境变量命名规则: MCP_<字段名大写>
        server_url = os.environ.get("MCP_SERVER_URL", mcp_config.get("server_url", ""))
        timeout = os.environ.get("MCP_TIMEOUT", mcp_config.get("timeout", "30s"))
        token = os.environ.get("MCP_TOKEN", mcp_config.get("token", ""))
        
        return MCPConfig(
            server_url=server_url,
            timeout=timeout,
            token=token
        )
    
    def _load_llm_config(self) -> LLMConfig:
        """
        加载 LLM 配置
        
        Returns:
            LLM 配置对象
        """
        llm_config = self.config.get("llm", {})
        
        # 支持环境变量覆盖，环境变量优先级高于配置文件
        # 环境变量命名规则: LLM_<字段名大写>，字段名中的下划线转换为下划线
        api_key = os.environ.get("LLM_API_KEY", llm_config.get("api_key", ""))
        api_host = os.environ.get("LLM_API_HOST", llm_config.get("api_host", ""))
        model = os.environ.get("LLM_MODEL", llm_config.get("model", ""))
        
        # 处理 max_tokens，支持从环境变量或配置文件读取
        max_tokens_str = os.environ.get("LLM_MAX_TOKENS")
        if max_tokens_str:
            try:
                max_tokens = int(max_tokens_str)
            except (ValueError, TypeError):
                max_tokens = None
        else:
            max_tokens = llm_config.get("max_tokens")
            if max_tokens is not None:
                try:
                    max_tokens = int(max_tokens)
                except (ValueError, TypeError):
                    max_tokens = None
        
        return LLMConfig(
            api_key=api_key,
            api_host=api_host,
            model=model,
            max_tokens=max_tokens
        )

