"""
Upstream Query Module

This module queries upstream information for services (e.g., qingqiu service)
"""

import json
from typing import Dict, Any, Tuple, Optional
from ...core.base_module import BaseModule, ModuleResult, ModuleStatus
from ...utils.logging import get_logger

logger = get_logger(__name__)


class UpstreamQueryModule(BaseModule):
    """
    Module for querying upstream information
    
    This module can query upstream information for services using MCP tools.
    Example: Query qingqiu service's upstream configuration
    """
    
    def __init__(self, mcp_tool=None, context: Dict[str, Any] = None):
        """
        Initialize Upstream Query Module
        
        Args:
            mcp_tool: MCP tool instance
            context: Shared context
        """
        super().__init__("upstream_query", mcp_tool, context)
    
    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate module parameters
        
        Args:
            params: Parameters to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Service name is required
        if 'service_name' not in params:
            return False, "service_name parameter is required"
        
        return True, None
    
    def execute(self, params: Dict[str, Any]) -> ModuleResult:
        """
        Execute upstream query
        
        Args:
            params: Module parameters:
                - service_name: Name of the service to query (required)
                - mcp_server: MCP server name (optional, default: 'default')
                - tool_name: MCP tool name (optional, default: 'get-events-from-ops')
                - additional_args: Additional arguments for MCP tool (optional)
        
        Returns:
            ModuleResult with upstream information
        """
        try:
            service_name = params.get('service_name')
            mcp_server = params.get('mcp_server', 'default')
            tool_name = params.get('tool_name', 'get-events-from-ops')
            additional_args = params.get('additional_args', {})
            
            logger.info(f"Querying upstream information for service: {service_name}")
            
            # Build query arguments
            # Example: Query events related to the service's upstream
            query_args = {
                "subject_pattern": f"ops.clusters.*.namespaces.*.services.{service_name}.upstream.>",
                "page_size": "50",
                **additional_args
            }
            
            # Call MCP tool to get upstream information
            result = self.call_mcp_tool(
                tool_name=tool_name,
                args=query_args,
                server_name=mcp_server
            )
            
            # Check if execution was successful
            if result.get('success') is False:
                error = result.get('error', 'Unknown error')
                return ModuleResult(
                    module_name=self.name,
                    status=ModuleStatus.FAILED,
                    error=f"MCP tool execution failed: {error}"
                )
            
            # Extract and process upstream data
            upstream_data = self._process_upstream_result(result, service_name)
            
            # Store service name in context for other modules
            self.set_context_value('last_queried_service', service_name)
            
            return ModuleResult(
                module_name=self.name,
                status=ModuleStatus.SUCCESS,
                data={
                    "service_name": service_name,
                    "upstream_info": upstream_data,
                    "raw_result": result
                },
                metadata={
                    "mcp_server": mcp_server,
                    "tool_name": tool_name
                }
            )
            
        except Exception as e:
            logger.error(f"Upstream query failed: {e}")
            logger.exception("Full exception traceback:")
            return ModuleResult(
                module_name=self.name,
                status=ModuleStatus.FAILED,
                error=str(e)
            )
    
    def _process_upstream_result(self, result: Dict[str, Any], service_name: str) -> Dict[str, Any]:
        """
        Process raw MCP result into structured upstream information
        
        Args:
            result: Raw MCP tool result
            service_name: Service name
            
        Returns:
            Processed upstream data
        """
        upstream_info = {
            "service_name": service_name,
            "upstreams": [],
            "summary": {}
        }
        
        # Extract content from result
        content = result.get('content', [])
        if isinstance(content, list):
            for item in content:
                if isinstance(item, str):
                    try:
                        # Try to parse JSON string
                        item_data = json.loads(item)
                        if isinstance(item_data, dict):
                            # Extract upstream information
                            upstream_info["upstreams"].append(item_data)
                    except json.JSONDecodeError:
                        # If not JSON, treat as text
                        upstream_info["upstreams"].append({"raw": item})
                elif isinstance(item, dict):
                    upstream_info["upstreams"].append(item)
        
        # Generate summary
        upstream_info["summary"] = {
            "total_upstreams": len(upstream_info["upstreams"]),
            "has_data": len(upstream_info["upstreams"]) > 0
        }
        
        return upstream_info

