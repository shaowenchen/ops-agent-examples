"""
MCP Tool for Ops Agent MCP Edition
"""

import json
from typing import Dict, Any, Optional

from ..config import ConfigLoader
from ..core.mcp_client import MCPClient
from ..utils.logging import get_logger

logger = get_logger(__name__)


class MCPTool:
    """MCP Tool for executing MCP server operations"""
    
    def __init__(self, config_loader: ConfigLoader = None):
        """
        Initialize MCP Tool
        
        Args:
            config_loader: Configuration loader instance
        """
        if config_loader:
            self.config_loader = config_loader
        else:
            self.config_loader = ConfigLoader()
            self.config_loader.load_config()
        
        # Initialize MCP client
        mcp_config = self.config_loader.mcp_config
        self.mcp_client = MCPClient(
            server_url=mcp_config.server_url,
            token=mcp_config.token,
            timeout=mcp_config.timeout
        )
        
        # Store server name from config for optional use
        self.server_name = mcp_config.server_name
    
    def execute(self, server_name: str = None, tool_name: str = None, args: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute an MCP tool
        
        Args:
            server_name: MCP server name (optional, not used by FastMCP client)
            tool_name: Tool name
            args: Tool arguments
            
        Returns:
            Execution result
        """
        try:
            # Validate required parameters
            if not tool_name:
                raise ValueError("No tool name provided")
            if args is None:
                args = {}
            
            logger.info(f"Executing MCP tool: {tool_name}")
            
            # Execute the tool
            result = self.mcp_client.call_tool(
                server_name=server_name,
                tool_name=tool_name,
                args=args
            )
            
            logger.info(f"Successfully executed MCP tool: {tool_name}")
            
            return result
        except Exception as e:
            logger.error(f"Failed to execute MCP tool {tool_name}: {e}")
            # Return error information
            return {
                "error": str(e),
                "success": False
            }
    
    def list_available_tools(self, server_name: str = None) -> Dict[str, Any]:
        """
        List available MCP tools
        
        Args:
            server_name: Optional MCP server name to filter by
            
        Returns:
            List of available tools
        """
        try:
            logger.info(f"Listing available MCP tools{'' if server_name is None else f' for server: {server_name}'}")
            
            # Get available tools
            tools = self.mcp_client.list_tools(server_name=server_name)
            
            logger.info(f"Found {len(tools)} available MCP tools")
            
            return {
                "tools": tools,
                "count": len(tools),
                "success": True
            }
        except Exception as e:
            logger.error(f"Failed to list available MCP tools: {e}")
            return {
                "error": str(e),
                "success": False
            }