"""
MCP Tool for Ops Agent SLO
"""

import json
import asyncio
import re
from datetime import timedelta
from typing import Dict, Any, Optional, List

from fastmcp import Client as FastMCPClient

from ..config import ConfigLoader
from ..utils.logging import get_logger

logger = get_logger(__name__)


class MCPTool:
    """MCP Tool for executing MCP server operations"""
    
    def __init__(self, config_loader: ConfigLoader = None, server_name: str = 'default'):
        """
        Initialize MCP Tool
        
        Args:
            config_loader: Configuration loader instance
            server_name: MCP server name (default: 'default')
        """
        if config_loader:
            self.config_loader = config_loader
        else:
            self.config_loader = ConfigLoader()
            self.config_loader.load_config()
        
        # Get MCP configuration for specified server
        mcp_config = self.config_loader.get_mcp_config(server_name)
        self.server_url = mcp_config.server_url
        self.token = mcp_config.token
        self.timeout_str = mcp_config.timeout
        self.server_name = mcp_config.server_name
        
        # Parse timeout string to datetime.timedelta object
        self.timeout = self._parse_timeout(self.timeout_str)
        
        # Initialize FastMCP client
        self.client = FastMCPClient(
            transport=self.server_url,
            auth=self.token,
            timeout=self.timeout
        )
    
    def _parse_timeout(self, timeout_str: str) -> timedelta:
        """
        Parse timeout string into datetime.timedelta object
        
        Args:
            timeout_str: Timeout string (e.g., "30s", "1m", "2h")
        
        Returns:
            datetime.timedelta object
        
        Raises:
            ValueError: If timeout string is invalid
        """
        # Regular expression to parse timeout string
        match = re.match(r'^(\d+)([smhd])$', timeout_str)
        if not match:
            raise ValueError(f"Invalid timeout format: {timeout_str}. Expected format like '30s', '1m', '2h'.")
        
        value, unit = match.groups()
        value = int(value)
        
        # Convert to seconds based on unit
        if unit == 's':
            return timedelta(seconds=value)
        elif unit == 'm':
            return timedelta(minutes=value)
        elif unit == 'h':
            return timedelta(hours=value)
        elif unit == 'd':
            return timedelta(days=value)
        
        raise ValueError(f"Invalid timeout unit: {unit}")
    
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
            
            logger.info(f"=== 开始执行MCP工具 ===")
            logger.info(f"工具名称: {tool_name}")
            logger.info(f"服务器名称: {server_name or self.server_name}")
            logger.info(f"服务器URL: {self.server_url}")
            logger.info(f"参数数量: {len(args) if args else 0}")
            if args:
                logger.info(f"参数详情: {args}")
            
            logger.info(f"准备调用MCP客户端 (服务器: {self.server_name}, URL: {self.server_url})")
            # Execute the tool using FastMCP client
            actual_tool_name = tool_name or server_name  # Handle both calling patterns
            result = asyncio.run(self._async_call_tool(actual_tool_name, args))
            
            logger.info(f"MCP工具调用完成: {tool_name}")
            logger.info(f"返回结果类型: {type(result)}")
            if result:
                logger.info(f"返回结果键: {list(result.keys()) if isinstance(result, dict) else '非字典类型'}")
                if isinstance(result, dict) and 'content' in result:
                    content = result['content']
                    logger.info(f"内容类型: {type(content)}")
                    if isinstance(content, list):
                        logger.info(f"内容数量: {len(content)}")
                    elif isinstance(content, str):
                        logger.info(f"内容长度: {len(content)}")
            else:
                logger.warning("MCP工具返回空结果")
            
            return result
        except Exception as e:
            logger.error(f"MCP工具执行失败 {tool_name}: {e}")
            logger.error(f"异常类型: {type(e).__name__}")
            logger.error(f"异常详情: {str(e)}")
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
            
            # Get available tools using FastMCP client
            tools = asyncio.run(self._async_list_tools())
            
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
    
    async def _async_call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Async method to call FastMCP client's call_tool method
        
        Args:
            name: Tool name
            arguments: Tool arguments
        
        Returns:
            Tool response
        """
        # FastMCP client needs to be used within an async context manager
        async with self.client as client:
            result = await client.call_tool(
                name=name,
                arguments=arguments
            )
            
            # Convert result to dict if needed, handling TextContent objects
            if hasattr(result, 'content'):
                # Handle MCP response with content
                content_list = []
                for content in result.content:
                    if hasattr(content, 'text'):
                        content_list.append(content.text)
                    elif hasattr(content, '__dict__'):
                        content_list.append(content.__dict__)
                    else:
                        content_list.append(str(content))
                
                return {
                    "content": content_list,
                    "isError": getattr(result, 'isError', False)
                }
            elif hasattr(result, 'dict'):
                return result.dict()
            elif hasattr(result, '__dict__'):
                return result.__dict__
            else:
                return {"result": str(result)}
    
    async def _async_list_tools(self) -> List[Dict[str, Any]]:
        """
        Async method to list tools using FastMCP client
        
        Returns:
            List of available tools
        """
        async with self.client as client:
            tools = await client.list_tools()
            return tools

