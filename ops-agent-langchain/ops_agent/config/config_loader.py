"""
Configuration loader for Ops Agent
"""

import os
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class MCPConfig:
    """MCP server configuration"""
    server_url: str
    timeout: str
    token: str


@dataclass
class OpenAIConfig:
    """OpenAI API configuration"""
    api_key: str
    api_host: str
    model: str
    max_tokens: Optional[int] = None  # Maximum tokens for completion


@dataclass
class TaskConfig:
    """Task configuration"""
    tasks: List[Dict[str, Any]]
    version: str


class ConfigLoader:
    """Configuration loader for Ops Agent"""
    
    def __init__(self, config_file: str = None):
        """
        Initialize configuration loader
        
        Args:
            config_file: Configuration file path
        """
        if config_file:
            self.config_path = config_file
        else:
            self.config_path = os.path.join(os.path.dirname(__file__), "../../configs/config.yaml")
        
        # Load main configuration
        self.config = self._load_config()
        
        # Initialize configurations
        self.mcp_config = self._load_mcp_config()
        self.openai_config = self._load_openai_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """
        Load main configuration file
        
        Returns:
            Configuration dictionary
        """
        try:
            with open(self.config_path, "r") as f:
                config = yaml.safe_load(f)
            return config or {}
        except Exception as e:
            raise ValueError(f"Error loading configuration: {str(e)}")
    
    def _load_mcp_config(self) -> MCPConfig:
        """
        Load MCP configuration
        
        Returns:
            MCP configuration
        """
        mcp_config = self.config.get("mcp", {})
        
        # Override with environment variables if available
        server_url = os.environ.get("MCP_SERVER_URL", mcp_config.get("server_url", ""))
        timeout = os.environ.get("MCP_TIMEOUT", mcp_config.get("timeout", "30s"))
        token = os.environ.get("MCP_TOKEN", mcp_config.get("token", ""))
        
        return MCPConfig(
            server_url=server_url,
            timeout=timeout,
            token=token
        )
    
    def _load_openai_config(self) -> OpenAIConfig:
        """
        Load OpenAI configuration
        
        Returns:
            OpenAI configuration
        """
        openai_config = self.config.get("openai", {})
        
        # Override with environment variables if available
        api_key = os.environ.get("OPENAI_API_KEY", openai_config.get("api_key", ""))
        api_host = os.environ.get("OPENAI_API_HOST", openai_config.get("api_host", ""))
        model = os.environ.get("OPENAI_MODEL", openai_config.get("model", "gpt-4"))
        
        # Load max_tokens with default based on model
        max_tokens_str = os.environ.get("OPENAI_MAX_TOKENS", openai_config.get("max_tokens"))
        max_tokens = None
        if max_tokens_str:
            try:
                max_tokens = int(max_tokens_str)
            except (ValueError, TypeError):
                max_tokens = None
        
        # Set sensible defaults if not specified
        if max_tokens is None:
            max_tokens = 1000  # Default for other models
        
        return OpenAIConfig(
            api_key=api_key,
            api_host=api_host,
            model=model,
            max_tokens=max_tokens
        )
    
    def load_tasks(self, task_file: str) -> TaskConfig:
        """
        Load tasks from a YAML file
        
        Args:
            task_file: Path to task file
            
        Returns:
            Task configuration
        """
        try:
            with open(task_file, "r") as f:
                task_config = yaml.safe_load(f)
            
            version = task_config.get("version", "1.0")
            tasks = task_config.get("tasks", [])
            
            return TaskConfig(
                version=version,
                tasks=tasks
            )
        except Exception as e:
            raise ValueError(f"Error loading task file: {str(e)}")