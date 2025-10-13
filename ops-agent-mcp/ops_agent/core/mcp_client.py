"""
MCP Client for Ops Agent MCP Edition
"""

import json
import logging
import asyncio
import re
from datetime import timedelta
from typing import Dict, Any, Optional, List, Union

from fastmcp import Client as FastMCPClient

from ..utils.logging import get_logger

logger = get_logger(__name__)


class MCPClient:
    """MCP Client for interacting with MCP servers"""
    
    def __init__(self, server_url: str, token: str, timeout: str = "30s"):
        """
        Initialize MCP Client
        
        Args:
            server_url: MCP server URL
            token: Authentication token
            timeout: Request timeout
        """
        self.server_url = server_url
        self.token = token
        
        # Convert timeout string to datetime.timedelta object
        self.timeout = self._parse_timeout(timeout)
        
        # Initialize FastMCP client
        self.client = FastMCPClient(
            transport=server_url,
            auth=token,
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
    
    def call_tool(self, server_name: str = None, tool_name: str = None, args: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Call an MCP tool
        
        Args:
            server_name: MCP server name (optional, not used by FastMCP client)
            tool_name: Tool name
            args: Tool arguments
        
        Returns:
            Tool response
        """
        try:
            # Use tool_name directly since FastMCP client doesn't use server prefixes
            actual_tool_name = tool_name or server_name  # Handle both calling patterns
            
            logger.info(f"Calling MCP tool: {actual_tool_name}")
            logger.debug(f"Tool arguments: {args}")
            
            # Call the tool using FastMCP client with correct parameter names
            # Since FastMCP client's call_tool is an async method, we need to run it with asyncio.run
            response = asyncio.run(self._async_call_tool(actual_tool_name, args))
            
            logger.info(f"Tool call successful: {actual_tool_name}")
            logger.debug(f"Tool response: {response}")
            
            return response
        except Exception as e:
            logger.error(f"Failed to call MCP tool {actual_tool_name}: {e}")
            raise
    
    async def _async_call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Async method to call FastMCP client's call_tool method
        
        Args:
            name: Full tool name (server_name.tool_name)
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
    
    def list_tools(self, server_name: str = None) -> List[Dict[str, Any]]:
        """
        List available tools from MCP servers
        
        Args:
            server_name: Optional MCP server name to filter by (not used by FastMCP client)
            
        Returns:
            List of available tools
        """
        try:
            logger.info(f"Listing MCP tools{'' if server_name is None else f' for server: {server_name}'}")
            
            # FastMCP client's list_tools() doesn't accept server_name parameter
            # We need to run it in an async context
            tools = asyncio.run(self._async_list_tools())
            
            logger.info(f"Found {len(tools)} tools{'' if server_name is None else f' for server: {server_name}'}")
            
            return tools
        except Exception as e:
            logger.error(f"Failed to list MCP tools{'' if server_name is None else f' for server: {server_name}'}: {e}")
            raise
    
    async def _async_list_tools(self) -> List[Dict[str, Any]]:
        """
        Async method to list tools using FastMCP client
        
        Returns:
            List of available tools
        """
        async with self.client as client:
            tools = await client.list_tools()
            return tools
    
    def get_tool_schema(self, server_name: str, tool_name: str) -> Dict[str, Any]:
        """
        Get the schema for a specific MCP tool
        
        Args:
            server_name: MCP server name
            tool_name: Tool name
            
        Returns:
            Tool schema
        """
        try:
            logger.info(f"Getting schema for MCP tool: {server_name}.{tool_name}")
            
            # Get tool schema
            schema = self.client.get_tool_schema(
                server_name=server_name,
                tool_name=tool_name
            )
            
            logger.info(f"Successfully retrieved schema for tool: {server_name}.{tool_name}")
            
            return schema
        except Exception as e:
            logger.error(f"Failed to get schema for MCP tool {server_name}.{tool_name}: {e}")
            raise