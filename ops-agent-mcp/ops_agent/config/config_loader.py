"""
Configuration loader for Ops Agent MCP Edition
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class MCPConfig:
    """MCP server configuration"""
    server_url: str
    server_name: str
    timeout: str
    token: str


class ConfigLoader:
    """Configuration loader for Ops Agent MCP Edition"""
    
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
                "/etc/ops-agent/config.yaml"
            ]
            
            for loc in default_locations:
                if os.path.exists(loc):
                    self.config_path = loc
                    break
            else:
                self.config_path = default_locations[0]  # Default to first location even if it doesn't exist
        
        self._config = None
        self._mcp_config = None
        
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file or environment variables"""
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
        # MCP configuration
        if not self._config.get('mcp'):
            self._config['mcp'] = {}
        
        # Use MCP_SERVERURL instead of MCP_SERVER_URL for environment variable
        self._config['mcp']['server_url'] = os.environ.get('MCP_SERVERURL', self._config['mcp'].get('server_url', ''))
        self._config['mcp']['server_name'] = os.environ.get('MCP_SERVER_NAME', self._config['mcp'].get('server_name', ''))
        self._config['mcp']['timeout'] = os.environ.get('MCP_TIMEOUT', self._config['mcp'].get('timeout', '30s'))
        self._config['mcp']['token'] = os.environ.get('MCP_TOKEN', self._config['mcp'].get('token', ''))
    
    @property
    def mcp_config(self) -> MCPConfig:
        """Get MCP configuration"""
        if not self._mcp_config:
            if not self._config:
                self.load_config()
            
            mcp_config = self._config.get('mcp', {})
            self._mcp_config = MCPConfig(
                    server_url=mcp_config.get('server_url', ''),
                    server_name=mcp_config.get('server_name', ''),
                    timeout=mcp_config.get('timeout', '30s'),
                    token=mcp_config.get('token', '')
                )
        
        return self._mcp_config