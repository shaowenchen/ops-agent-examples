"""
MCP Query Executor for executing multiple MCP queries
"""

import json
from typing import Dict, Any, List

from ..config import ConfigLoader
from ..tools.mcp_tool import MCPTool
from ..utils.logging import get_logger

logger = get_logger(__name__)


class MCPQueryExecutor:
    """Executor for running multiple MCP queries"""
    
    def __init__(self, config_loader: ConfigLoader):
        """
        Initialize MCP Query Executor
        
        Args:
            config_loader: Configuration loader instance
        """
        self.config_loader = config_loader
        # Cache for MCP tools by server name
        self._mcp_tools_cache = {}
        
        logger.info(f"Initialized MCP Query Executor")
    
    def _get_mcp_tool(self, server_name: str = 'default') -> MCPTool:
        """
        Get or create MCP tool for specified server
        
        Args:
            server_name: MCP server name (default: 'default')
        
        Returns:
            MCPTool instance for the specified server
        """
        # Use cache to avoid creating multiple clients for the same server
        if server_name not in self._mcp_tools_cache:
            mcp_tool = MCPTool(self.config_loader, server_name=server_name)
            mcp_config = self.config_loader.get_mcp_config(server_name)
            self._mcp_tools_cache[server_name] = mcp_tool
            logger.info(f"Created MCP tool for server: {server_name}")
            logger.info(f"Server URL: {mcp_config.server_url}")
            logger.info(f"Timeout: {mcp_config.timeout}")
        
        return self._mcp_tools_cache[server_name]
    
    def list_available_tools(self, server_name: str = 'default') -> List[Dict[str, Any]]:
        """
        List all available MCP tools from the server
        
        Args:
            server_name: MCP server name (default: 'default')
        
        Returns:
            List of available tools with their information
        """
        try:
            logger.info(f"Listing available MCP tools from server: {server_name}...")
            
            # Get MCP tool for specified server
            mcp_tool = self._get_mcp_tool(server_name)
            
            # Use MCPTool to list tools
            result = mcp_tool.list_available_tools()
            
            if result.get('success', False):
                tools = result.get('tools', [])
                
                # Convert tools to dict format (参考 list-mcp-tools-fastmp.py 的处理方式)
                tools_list = []
                for tool in tools:
                    tool_info = {
                        'name': tool.name if hasattr(tool, 'name') else str(tool),
                        'description': tool.description if hasattr(tool, 'description') else '',
                    }
                    
                    # Add input schema if available (参考示例代码，直接使用 inputSchema)
                    if hasattr(tool, 'inputSchema') and tool.inputSchema:
                        schema = tool.inputSchema
                        tool_info['input_schema'] = schema
                        
                        # 提取 schema 详细信息（可选，用于更好的展示）
                        if isinstance(schema, dict):
                            properties = schema.get('properties', {})
                            required = schema.get('required', [])
                            if properties:
                                tool_info['parameters'] = {}
                                for param_name, param_info in properties.items():
                                    tool_info['parameters'][param_name] = {
                                        'type': param_info.get('type', 'unknown'),
                                        'description': param_info.get('description', ''),
                                        'required': param_name in required
                                    }
                    
                    tools_list.append(tool_info)
                
                logger.info(f"Found {len(tools_list)} available tools")
                return tools_list
            else:
                error = result.get('error', 'Unknown error')
                logger.error(f"Failed to list tools: {error}")
                return []
            
        except Exception as e:
            logger.error(f"Failed to list available tools: {e}")
            return []
    
    def _call_tool(self, tool_name: str, args: Dict[str, Any], server_name: str = 'default') -> Dict[str, Any]:
        """
        Call MCP tool using MCPTool
        
        Args:
            tool_name: Tool name
            args: Tool arguments
            server_name: MCP server name (default: 'default')
        
        Returns:
            Tool response
        """
        try:
            # Get MCP tool for specified server
            mcp_tool = self._get_mcp_tool(server_name)
            
            # Use MCPTool to execute the tool
            logger.info(f"Calling MCP tool: {tool_name} on server: {server_name}")
            logger.debug(f"Tool arguments: {json.dumps(args, ensure_ascii=False, indent=2)}")
            
            result = mcp_tool.execute(
                server_name=server_name,
                tool_name=tool_name,
                args=args
            )
            
            # Check if execution failed (MCPTool returns error dict)
            if result.get('success') is False:
                error = result.get('error', 'Unknown error')
                # This is a tool execution error (tool exists but execution failed)
                # Mark it as execution error for better error handling
                error_msg = f"Tool '{tool_name}' execution failed: {error}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            # Check if MCP tool returned an error in the result
            if isinstance(result, dict) and result.get('isError', False):
                # Extract error message from content
                content = result.get('content', [])
                if isinstance(content, list) and len(content) > 0:
                    error_text = ' '.join([str(c) for c in content])
                else:
                    error_text = str(content) if content else 'Unknown error from MCP tool'
                
                # This is a tool execution error (tool exists but execution failed)
                # Different from tool not found error
                error_msg = f"Tool '{tool_name}' execution failed: {error_text}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            return result
        except Exception as e:
            error_msg = str(e)
            error_type = type(e).__name__
            logger.error(f"Exception type: {error_type}, message: {error_msg}")
            logger.exception("Full exception traceback:")
            
            # Get server URL for error message
            mcp_config = self.config_loader.get_mcp_config(server_name)
            server_url = mcp_config.server_url
            
            # Provide more helpful error messages
            if "nodename nor servname" in error_msg or "Name or service not known" in error_msg:
                raise ConnectionError(
                    f"Failed to resolve MCP server hostname: {server_url}\n"
                    f"Server: {server_name}\n"
                    f"Please check:\n"
                    f"  1. The server URL is correct in config.yaml\n"
                    f"  2. The server is accessible from your network\n"
                    f"  3. DNS resolution is working\n"
                    f"Original error: {error_msg}"
                )
            elif "Connection refused" in error_msg or "Connection reset" in error_msg:
                raise ConnectionError(
                    f"Failed to connect to MCP server: {server_url}\n"
                    f"Server: {server_name}\n"
                    f"Please check:\n"
                    f"  1. The server is running and accessible\n"
                    f"  2. The port and path are correct\n"
                    f"  3. Firewall/network settings allow the connection\n"
                    f"Original error: {error_msg}"
                )
            elif "404" in error_msg or "not found" in error_msg.lower():
                # Check if this is a tool execution error (tool exists but execution failed)
                # vs tool not found error
                # Patterns that indicate tool execution failure (not tool not found):
                execution_error_patterns = [
                    "execution failed",
                    "failed to fetch",
                    "failed to get",
                    "failed to query",
                    "API returned status",
                    "backend API",
                    "Tool '"
                ]
                
                is_execution_error = any(pattern in error_msg for pattern in execution_error_patterns)
                
                if is_execution_error:
                    # This is a tool execution error, not a tool not found error
                    # Re-raise with more context but don't suggest tool name is wrong
                    raise Exception(
                        f"Tool execution failed (404): {tool_name}\n"
                        f"Error: {error_msg}\n"
                        f"This usually means:\n"
                        f"  1. The tool exists but the backend API returned 404\n"
                        f"  2. The query parameters may be incorrect\n"
                        f"  3. The requested resource may not exist\n"
                        f"Please check the tool arguments and try again."
                    )
                else:
                    # This might be a tool not found error
                    # Try to get available tools for better error message
                    available_tools_msg = ""
                    try:
                        available_tools = self.list_available_tools(server_name)
                        if available_tools:
                            tool_names = [tool.get('name', 'unknown') for tool in available_tools]
                            available_tools_msg = f"\nAvailable tools on server: {', '.join(tool_names)}"
                    except:
                        pass
                    
                    raise ValueError(
                        f"Tool or endpoint not found (404): {tool_name}\n"
                        f"Server: {server_name}\n"
                        f"Please check:\n"
                        f"  1. The tool name '{tool_name}' is correct\n"
                        f"  2. The tool is available on the MCP server\n"
                        f"  3. The server URL and path are correct: {server_url}\n"
                        f"{available_tools_msg}\n"
                        f"Original error: {error_msg}"
                    )
            else:
                # Re-raise with more context
                raise type(e)(f"{error_type}: {error_msg}\nTool: {tool_name}, Args: {json.dumps(args, ensure_ascii=False)}")
    
    def execute_query(self, tool_name: str, args: Dict[str, Any] = None, server_name: str = 'default') -> Dict[str, Any]:
        """
        Execute a single MCP query
        
        Args:
            tool_name: MCP tool name
            args: Tool arguments
            server_name: MCP server name (default: 'default')
        
        Returns:
            Query result
        """
        if args is None:
            args = {}
        
        try:
            logger.info(f"Executing MCP query: {tool_name} on server: {server_name}")
            logger.debug(f"Query arguments: {json.dumps(args, ensure_ascii=False, indent=2)}")
            
            # Use MCPTool to execute the query
            result = self._call_tool(tool_name, args, server_name)
            
            logger.info(f"Query {tool_name} completed successfully")
            return {
                "tool_name": tool_name,
                "args": args,
                "result": result,
                "success": True
            }
        except Exception as e:
            logger.error(f"Failed to execute query {tool_name}: {e}")
            return {
                "tool_name": tool_name,
                "args": args,
                "error": str(e),
                "success": False
            }
    
    def execute_queries(self, queries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Execute multiple MCP queries sequentially
        
        Args:
            queries: List of query configurations, each with 'tool_name' and optional 'args'
        
        Returns:
            List of query results
        """
        results = []
        
        logger.info(f"Starting execution of {len(queries)} MCP queries")
        
        for idx, query in enumerate(queries, 1):
            tool_name = query.get('tool_name')
            args = query.get('args', {})
            # Get mcp_server from query, default to 'default'
            mcp_server = query.get('mcp_server', 'default')
            
            if not tool_name:
                logger.warning(f"Query {idx} missing tool_name, skipping")
                results.append({
                    "query_index": idx,
                    "error": "Missing tool_name",
                    "success": False
                })
                continue
            
            logger.info(f"\n{'='*80}")
            logger.info(f"Query {idx}/{len(queries)}: {tool_name} (server: {mcp_server})")
            logger.info(f"{'='*80}")
            
            result = self.execute_query(tool_name, args, mcp_server)
            result["query_index"] = idx
            # Include desc from original query if available
            if 'desc' in query:
                result["desc"] = query['desc']
            # Include formater from original query if available
            if 'formater' in query:
                result["formater"] = query['formater']
            # Include mcp_server in result
            result["mcp_server"] = mcp_server
            results.append(result)
        
        return results

