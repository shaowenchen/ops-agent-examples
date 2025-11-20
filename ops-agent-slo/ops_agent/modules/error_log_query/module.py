"""
Error Log Query Module

This module queries error/exception logs from Elasticsearch
"""

import json
from typing import Dict, Any, Tuple, Optional
from ...core.base_module import BaseModule, ModuleResult, ModuleStatus
from ...utils.logging import get_logger

logger = get_logger(__name__)


class ErrorLogQueryModule(BaseModule):
    """
    Module for querying error/exception logs
    
    This module can query error logs from Elasticsearch using MCP tools.
    It can use context from other modules (e.g., service name from upstream query)
    """
    
    def __init__(self, mcp_tool=None, context: Dict[str, Any] = None):
        """
        Initialize Error Log Query Module
        
        Args:
            mcp_tool: MCP tool instance
            context: Shared context
        """
        super().__init__("error_log_query", mcp_tool, context)
    
    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate module parameters
        
        Args:
            params: Parameters to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # At least one query parameter should be provided
        if not any(key in params for key in ['service_name', 'index', 'query_body', 'use_context']):
            return False, "At least one of service_name, index, query_body, or use_context must be provided"
        
        return True, None
    
    def execute(self, params: Dict[str, Any]) -> ModuleResult:
        """
        Execute error log query
        
        Args:
            params: Module parameters:
                - service_name: Service name to query logs for (optional, can use context)
                - index: Elasticsearch index pattern (optional, default: 'logs-*')
                - query_body: Custom Elasticsearch query body (optional)
                - mcp_server: MCP server name (optional, default: 'default')
                - tool_name: MCP tool name (optional, default: 'search-logs-from-elasticsearch')
                - time_range: Time range for query (optional, e.g., '1h', '24h')
                - use_context: Whether to use service_name from context (optional, default: True)
        
        Returns:
            ModuleResult with error log information
        """
        try:
            # Get service name from params or context
            use_context = params.get('use_context', True)
            service_name = params.get('service_name')
            
            if not service_name and use_context:
                # Try to get from context (e.g., from upstream_query module)
                service_name = self.get_context_value('last_queried_service')
                if service_name:
                    logger.info(f"Using service_name from context: {service_name}")
            
            index = params.get('index', 'logs-*')
            mcp_server = params.get('mcp_server', 'default')
            tool_name = params.get('tool_name', 'search-logs-from-elasticsearch')
            time_range = params.get('time_range', '1h')
            
            # Build query body
            query_body = params.get('query_body')
            if not query_body:
                query_body = self._build_default_query(service_name, time_range)
            
            logger.info(f"Querying error logs for service: {service_name or 'all'}")
            logger.debug(f"Query body: {json.dumps(query_body, ensure_ascii=False, indent=2)}")
            
            # Call MCP tool to search logs
            result = self.call_mcp_tool(
                tool_name=tool_name,
                args={
                    "index": index,
                    "body": json.dumps(query_body) if isinstance(query_body, dict) else query_body
                },
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
            
            # Extract and process log data
            log_data = self._process_log_result(result, service_name)
            
            # Store log summary in context
            self.set_context_value('error_log_summary', log_data.get('summary', {}))
            
            return ModuleResult(
                module_name=self.name,
                status=ModuleStatus.SUCCESS,
                data={
                    "service_name": service_name,
                    "logs": log_data,
                    "raw_result": result
                },
                metadata={
                    "mcp_server": mcp_server,
                    "tool_name": tool_name,
                    "index": index,
                    "time_range": time_range
                }
            )
            
        except Exception as e:
            logger.error(f"Error log query failed: {e}")
            logger.exception("Full exception traceback:")
            return ModuleResult(
                module_name=self.name,
                status=ModuleStatus.FAILED,
                error=str(e)
            )
    
    def _build_default_query(self, service_name: str = None, time_range: str = '1h') -> Dict[str, Any]:
        """
        Build default Elasticsearch query for error logs
        
        Args:
            service_name: Service name to filter by (optional)
            time_range: Time range string (e.g., '1h', '24h')
        
        Returns:
            Elasticsearch query body
        """
        # Convert time range to milliseconds (simplified, assumes 'h' suffix)
        hours = int(time_range.rstrip('h'))
        from_time = f"now-{hours}h"
        
        query = {
            "size": 100,
            "query": {
                "bool": {
                    "must": [
                        {
                            "range": {
                                "@timestamp": {
                                    "gte": from_time
                                }
                            }
                        },
                        {
                            "bool": {
                                "should": [
                                    {"match": {"level": "ERROR"}},
                                    {"match": {"level": "error"}},
                                    {"match": {"level": "FATAL"}},
                                    {"match": {"level": "fatal"}},
                                    {"match": {"message": "exception"}},
                                    {"match": {"message": "Exception"}},
                                    {"match": {"message": "error"}},
                                    {"match": {"message": "Error"}}
                                ],
                                "minimum_should_match": 1
                            }
                        }
                    ]
                }
            },
            "sort": [
                {
                    "@timestamp": {
                        "order": "desc"
                    }
                }
            ]
        }
        
        # Add service name filter if provided
        if service_name:
            query["query"]["bool"]["must"].append({
                "match": {
                    "service": service_name
                }
            })
        
        return query
    
    def _process_log_result(self, result: Dict[str, Any], service_name: str = None) -> Dict[str, Any]:
        """
        Process raw MCP result into structured log information
        
        Args:
            result: Raw MCP tool result
            service_name: Service name (optional)
            
        Returns:
            Processed log data
        """
        log_data = {
            "service_name": service_name,
            "error_logs": [],
            "summary": {
                "total_errors": 0,
                "error_types": {},
                "time_range": None
            }
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
                            # Check if it's Elasticsearch response
                            if 'hits' in item_data:
                                hits = item_data.get('hits', {}).get('hits', [])
                                for hit in hits:
                                    source = hit.get('_source', {})
                                    log_data["error_logs"].append(source)
                                    
                                    # Count error types
                                    level = source.get('level', 'unknown')
                                    log_data["summary"]["error_types"][level] = \
                                        log_data["summary"]["error_types"].get(level, 0) + 1
                            else:
                                log_data["error_logs"].append(item_data)
                    except json.JSONDecodeError:
                        # If not JSON, treat as text
                        log_data["error_logs"].append({"raw": item})
                elif isinstance(item, dict):
                    # Handle direct dict response
                    if 'hits' in item:
                        hits = item.get('hits', {}).get('hits', [])
                        for hit in hits:
                            source = hit.get('_source', {})
                            log_data["error_logs"].append(source)
                    else:
                        log_data["error_logs"].append(item)
        
        # Update summary
        log_data["summary"]["total_errors"] = len(log_data["error_logs"])
        
        return log_data

