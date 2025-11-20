"""
Configuration loader for Ops Agent CheckAll
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass
class MCPConfig:
    """MCP server configuration"""
    server_url: str
    server_name: str
    timeout: str
    token: str


class ConfigLoader:
    """Configuration loader for Ops Agent CheckAll"""
    
    def __init__(self, config_file: str = None):
        """
        Initialize configuration loader
        
        Args:
            config_file: Configuration file path
        """
        if config_file:
            self.config_path = config_file
        else:
            # Try to find config in default locations
            default_locations = [
                os.path.join(os.path.dirname(__file__), "../../configs/config.yaml"),
                "./configs/config.yaml",
                "/etc/ops-agent-checkall/config.yaml"
            ]
            
            for loc in default_locations:
                if os.path.exists(loc):
                    self.config_path = loc
                    break
            else:
                self.config_path = default_locations[0]  # Default to first location
        
        self._config = None
        self._mcp_config = None
        self._mcp_servers = None  # 存储多个 MCP 服务器配置
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file or environment variables"""
        # Load environment variables from .env if present (project root or cwd)
        try:
            # Try project root .env
            project_root_env = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.env"))
            load_dotenv(dotenv_path=project_root_env, override=False)
            # Also try current working directory .env
            load_dotenv(override=False)
        except Exception:
            # Best-effort loading; never fail on dotenv
            pass

        # First try to load from file
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self._config = yaml.safe_load(f)
            except Exception as e:
                print(f"Failed to load config file {self.config_path}: {e}")
                self._config = {}
        else:
            self._config = {}
        
        # Override with environment variables
        self._load_from_env()
        return self._config
    
    def _load_from_env(self) -> None:
        """Load configuration from environment variables"""
        import json
        
        # 初始化 mcp_servers 配置
        mcp_servers_raw = self._config.get('mcp_servers', [])
        
        # 只支持列表格式
        mcp_servers_dict = {}
        if isinstance(mcp_servers_raw, list):
            # 列表格式：支持 MCP1, MCP2 并列
            default_server_name = None
            first_server_name = None
            
            # 第一遍：找出标记为 default 的服务器
            for server in mcp_servers_raw:
                if isinstance(server, dict) and server.get('default', False):
                    default_server_name = server.get('name')
                    break
            
            # 第二遍：处理所有服务器
            for idx, server in enumerate(mcp_servers_raw):
                if isinstance(server, dict):
                    server_name = server.get('name', f'MCP{idx + 1}')
                    if idx == 0:
                        first_server_name = server_name
                    
                    # 移除 default 和 name 字段，保留其他配置
                    server_config = {k: v for k, v in server.items() if k not in ['default', 'name']}
                    server_config['server_name'] = server_name
                    mcp_servers_dict[server_name] = server_config
            
            # 确定默认服务器：优先使用标记为 default 的，否则使用第一个
            if default_server_name is None:
                default_server_name = first_server_name
            
            # 将默认服务器也映射为 'default' key
            if default_server_name and default_server_name in mcp_servers_dict:
                mcp_servers_dict['default'] = mcp_servers_dict[default_server_name].copy()
                mcp_servers_dict['default']['server_name'] = 'default'
        
        self._config['mcp_servers'] = mcp_servers_dict
        
        # 支持通过环境变量配置多个 MCP 服务器（只支持列表格式）
        # 格式：MCP_SERVERS_JSON='[{"name":"MCP1","server_url":"...","token":"..."},{"name":"MCP2",...}]'
        mcp_servers_json = os.environ.get('MCP_SERVERS_JSON')
        if mcp_servers_json:
            try:
                env_servers = json.loads(mcp_servers_json)
                if isinstance(env_servers, list):
                    # 列表格式
                    for server in env_servers:
                        if isinstance(server, dict):
                            server_name = server.get('name', f'MCP{len(mcp_servers_dict) + 1}')
                            server_config = {k: v for k, v in server.items() if k not in ['default', 'name']}
                            server_config['server_name'] = server_name
                            if server.get('default', False):
                                mcp_servers_dict['default'] = server_config.copy()
                                mcp_servers_dict['default']['server_name'] = 'default'
                            mcp_servers_dict[server_name] = server_config
                    # 记录环境变量加载的服务器
                    import logging
                    logger = logging.getLogger(__name__)
                    env_server_names = [s.get('name', 'unknown') for s in env_servers if isinstance(s, dict)]
                    logger.info(f"Loaded {len(env_server_names)} MCP servers from environment: {env_server_names}")
            except json.JSONDecodeError as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to parse MCP_SERVERS_JSON: {e}")
        
        # 记录所有配置的服务器
        if mcp_servers_dict:
            import logging
            logger = logging.getLogger(__name__)
            server_names = list(mcp_servers_dict.keys())
            logger.info(f"Total configured MCP servers: {server_names}")
            for name, config in mcp_servers_dict.items():
                if isinstance(config, dict):
                    server_url = config.get('server_url', 'N/A')
                    logger.debug(f"  - {name}: {server_url}")
        
        self._config['mcp_servers'] = mcp_servers_dict
    
    @property
    def mcp_config(self) -> MCPConfig:
        """Get default MCP configuration (backwards compatibility)"""
        return self.get_mcp_config('default')
    
    def get_mcp_config(self, server_name: str = 'default') -> MCPConfig:
        """
        Get MCP configuration for a specific server
        
        Args:
            server_name: Server name (default: 'default')
        
        Returns:
            MCPConfig instance
        
        Raises:
            ValueError: If server not found and no default server available
        """
        if not self._config:
            self.load_config()
        
        # 获取所有服务器配置
        mcp_servers = self._config.get('mcp_servers', {})
        
        # 如果指定的服务器不存在，记录警告并使用 default
        original_server_name = server_name
        if server_name not in mcp_servers:
            available_servers = list(mcp_servers.keys())
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                f"MCP server '{original_server_name}' not found. Available servers: {available_servers}. "
                f"Falling back to 'default'."
            )
            server_name = 'default'
        
        # 如果 default 也不存在，抛出错误
        if server_name not in mcp_servers:
            available_servers = list(mcp_servers.keys())
            raise ValueError(
                f"MCP server '{original_server_name}' not found, and no 'default' server available. "
                f"Available servers: {available_servers}. "
                f"Please check your configuration."
            )
        
        # 获取指定服务器的配置
        server_config = mcp_servers.get(server_name, {})
        
        return MCPConfig(
            server_url=server_config.get('server_url', ''),
            server_name=server_config.get('server_name', server_name),
            timeout=server_config.get('timeout', '30s'),
            token=server_config.get('token', '')
        )
    
    def list_mcp_servers(self) -> Dict[str, MCPConfig]:
        """
        List all configured MCP servers
        
        Returns:
            Dictionary mapping server names to MCPConfig instances
        """
        if not self._config:
            self.load_config()
        
        mcp_servers = self._config.get('mcp_servers', {})
        servers = {}
        
        # 排除 'default' 的重复映射，只返回实际配置的服务器
        seen_names = set()
        for server_name, server_config in mcp_servers.items():
            if isinstance(server_config, dict):
                actual_name = server_config.get('server_name', server_name)
                if actual_name not in seen_names and server_name != 'default':
                    servers[actual_name] = self.get_mcp_config(actual_name)
                    seen_names.add(actual_name)
        
        # 确保 default 也在列表中
        if 'default' in mcp_servers:
            servers['default'] = self.get_mcp_config('default')
        
        return servers

