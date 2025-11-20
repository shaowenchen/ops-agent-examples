"""
Base module class for SLO check modules
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum


class ModuleStatus(Enum):
    """Module execution status"""
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    PARTIAL = "partial"


@dataclass
class ModuleResult:
    """Result from module execution"""
    module_name: str
    status: ModuleStatus
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary"""
        return {
            "module_name": self.module_name,
            "status": self.status.value,
            "data": self.data,
            "error": self.error,
            "metadata": self.metadata or {}
        }


class BaseModule(ABC):
    """
    Base class for all SLO check modules
    
    Each module should:
    1. Inherit from BaseModule
    2. Implement the execute() method
    3. Optionally override validate_params() for parameter validation
    4. Use self.mcp_tool to call MCP tools
    5. Use self.context to access shared context and parameters
    """
    
    def __init__(self, name: str, mcp_tool=None, context: Optional[Dict[str, Any]] = None):
        """
        Initialize module
        
        Args:
            name: Module name
            mcp_tool: MCP tool instance for calling MCP services
            context: Shared context dictionary for parameter passing
        """
        self.name = name
        self.mcp_tool = mcp_tool
        self.context = context or {}
    
    @abstractmethod
    def execute(self, params: Dict[str, Any]) -> ModuleResult:
        """
        Execute the module
        
        Args:
            params: Module-specific parameters
            
        Returns:
            ModuleResult with execution results
        """
        pass
    
    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate module parameters
        
        Args:
            params: Parameters to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        return True, None
    
    def get_context_value(self, key: str, default: Any = None) -> Any:
        """
        Get value from shared context
        
        Args:
            key: Context key
            default: Default value if key not found
            
        Returns:
            Context value or default
        """
        return self.context.get(key, default)
    
    def set_context_value(self, key: str, value: Any) -> None:
        """
        Set value in shared context
        
        Args:
            key: Context key
            value: Value to set
        """
        self.context[key] = value
    
    def call_mcp_tool(self, tool_name: str, args: Dict[str, Any], server_name: str = 'default') -> Dict[str, Any]:
        """
        Call MCP tool
        
        Args:
            tool_name: MCP tool name
            args: Tool arguments
            server_name: MCP server name
            
        Returns:
            Tool execution result
        """
        if not self.mcp_tool:
            raise ValueError("MCP tool not available")
        
        return self.mcp_tool.execute(
            server_name=server_name,
            tool_name=tool_name,
            args=args
        )

