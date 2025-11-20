"""
Orchestrator for coordinating SLO check modules
"""

import json
from typing import Dict, Any, List, Optional
from ..config import ConfigLoader
from ..tools.mcp_tool import MCPTool
from .base_module import BaseModule, ModuleResult, ModuleStatus
from ..utils.logging import get_logger

logger = get_logger(__name__)


class Orchestrator:
    """
    Orchestrator for executing SLO check modules
    
    Features:
    - Module registration and execution
    - Parameter passing and reuse between modules
    - Shared context for data exchange
    - Sequential or parallel execution
    """
    
    def __init__(self, config_loader: ConfigLoader):
        """
        Initialize orchestrator
        
        Args:
            config_loader: Configuration loader instance
        """
        self.config_loader = config_loader
        self.modules: Dict[str, BaseModule] = {}
        self.context: Dict[str, Any] = {}
        self._mcp_tools_cache: Dict[str, MCPTool] = {}
        
        logger.info("Initialized SLO Orchestrator")
    
    def _get_mcp_tool(self, server_name: str = 'default') -> MCPTool:
        """
        Get or create MCP tool for specified server
        
        Args:
            server_name: MCP server name (default: 'default')
        
        Returns:
            MCPTool instance for the specified server
        """
        if server_name not in self._mcp_tools_cache:
            mcp_tool = MCPTool(self.config_loader, server_name=server_name)
            self._mcp_tools_cache[server_name] = mcp_tool
            logger.info(f"Created MCP tool for server: {server_name}")
        
        return self._mcp_tools_cache[server_name]
    
    def register_module(self, module: BaseModule) -> None:
        """
        Register a module with the orchestrator
        
        Args:
            module: Module instance to register
        """
        # Set up module with orchestrator's context and MCP tool
        module.context = self.context
        module.mcp_tool = self._get_mcp_tool()
        
        self.modules[module.name] = module
        logger.info(f"Registered module: {module.name}")
    
    def register_modules(self, modules: List[BaseModule]) -> None:
        """
        Register multiple modules
        
        Args:
            modules: List of module instances
        """
        for module in modules:
            self.register_module(module)
    
    def set_context(self, key: str, value: Any) -> None:
        """
        Set value in shared context
        
        Args:
            key: Context key
            value: Value to set
        """
        self.context[key] = value
        logger.debug(f"Set context[{key}] = {value}")
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """
        Get value from shared context
        
        Args:
            key: Context key
            default: Default value if key not found
            
        Returns:
            Context value or default
        """
        return self.context.get(key, default)
    
    def clear_context(self) -> None:
        """Clear shared context"""
        self.context.clear()
        logger.debug("Cleared context")
    
    def execute_module(self, module_name: str, params: Dict[str, Any] = None) -> ModuleResult:
        """
        Execute a single module
        
        Args:
            module_name: Name of the module to execute
            params: Module parameters
            
        Returns:
            ModuleResult from module execution
            
        Raises:
            ValueError: If module not found
        """
        if module_name not in self.modules:
            raise ValueError(f"Module '{module_name}' not found. Available modules: {list(self.modules.keys())}")
        
        module = self.modules[module_name]
        params = params or {}
        
        logger.info(f"Executing module: {module_name}")
        logger.debug(f"Module parameters: {json.dumps(params, ensure_ascii=False, indent=2)}")
        
        try:
            # Validate parameters
            is_valid, error_msg = module.validate_params(params)
            if not is_valid:
                return ModuleResult(
                    module_name=module_name,
                    status=ModuleStatus.FAILED,
                    error=f"Parameter validation failed: {error_msg}"
                )
            
            # Execute module
            result = module.execute(params)
            
            # Store result in context for other modules to use
            self.context[f"{module_name}_result"] = result.to_dict()
            
            logger.info(f"Module {module_name} completed with status: {result.status.value}")
            return result
            
        except Exception as e:
            logger.error(f"Module {module_name} execution failed: {e}")
            logger.exception("Full exception traceback:")
            return ModuleResult(
                module_name=module_name,
                status=ModuleStatus.FAILED,
                error=str(e)
            )
    
    def execute_workflow(self, workflow: List[Dict[str, Any]]) -> List[ModuleResult]:
        """
        Execute a workflow of modules
        
        Args:
            workflow: List of module execution configurations, each with:
                - module: Module name
                - params: Module parameters (optional)
                - condition: Condition to check before execution (optional)
                - use_result_from: Use result from another module (optional)
        
        Returns:
            List of ModuleResult from each module execution
        """
        results = []
        
        logger.info(f"Starting workflow execution with {len(workflow)} steps")
        
        for idx, step in enumerate(workflow, 1):
            module_name = step.get('module')
            if not module_name:
                logger.warning(f"Step {idx} missing module name, skipping")
                continue
            
            # Check condition if specified
            condition = step.get('condition')
            if condition:
                if not self._evaluate_condition(condition):
                    logger.info(f"Step {idx} condition not met, skipping module: {module_name}")
                    results.append(ModuleResult(
                        module_name=module_name,
                        status=ModuleStatus.SKIPPED,
                        metadata={"reason": "condition not met"}
                    ))
                    continue
            
            # Get parameters
            params = step.get('params', {})
            
            # Merge result from another module if specified
            use_result_from = step.get('use_result_from')
            if use_result_from:
                previous_result = self.get_context(f"{use_result_from}_result")
                if previous_result:
                    # Merge previous result data into params
                    if isinstance(previous_result, dict) and 'data' in previous_result:
                        params = {**params, **previous_result.get('data', {})}
                    logger.debug(f"Using result from {use_result_from} for module {module_name}")
            
            # Execute module
            logger.info(f"\n{'='*80}")
            logger.info(f"Step {idx}/{len(workflow)}: {module_name}")
            logger.info(f"{'='*80}")
            
            result = self.execute_module(module_name, params)
            result.metadata = result.metadata or {}
            result.metadata['step_index'] = idx
            results.append(result)
            
            # Stop on failure if configured
            stop_on_failure = step.get('stop_on_failure', False)
            if stop_on_failure and result.status == ModuleStatus.FAILED:
                logger.warning(f"Step {idx} failed and stop_on_failure is True, stopping workflow")
                break
        
        logger.info(f"Workflow execution completed. {len(results)} steps executed")
        return results
    
    def _evaluate_condition(self, condition: Dict[str, Any]) -> bool:
        """
        Evaluate a condition
        
        Args:
            condition: Condition dictionary with:
                - type: Condition type (e.g., 'context_key_exists', 'context_value_equals')
                - key: Context key to check
                - value: Expected value (for equals conditions)
        
        Returns:
            True if condition is met, False otherwise
        """
        condition_type = condition.get('type')
        
        if condition_type == 'context_key_exists':
            key = condition.get('key')
            return key in self.context
        
        elif condition_type == 'context_value_equals':
            key = condition.get('key')
            expected_value = condition.get('value')
            return self.get_context(key) == expected_value
        
        elif condition_type == 'module_succeeded':
            module_name = condition.get('module')
            result = self.get_context(f"{module_name}_result")
            if result and isinstance(result, dict):
                return result.get('status') == 'success'
            return False
        
        else:
            logger.warning(f"Unknown condition type: {condition_type}")
            return False
    
    def get_summary(self, results: List[ModuleResult]) -> Dict[str, Any]:
        """
        Get summary of execution results
        
        Args:
            results: List of ModuleResult
        
        Returns:
            Summary dictionary
        """
        total = len(results)
        success = sum(1 for r in results if r.status == ModuleStatus.SUCCESS)
        failed = sum(1 for r in results if r.status == ModuleStatus.FAILED)
        skipped = sum(1 for r in results if r.status == ModuleStatus.SKIPPED)
        partial = sum(1 for r in results if r.status == ModuleStatus.PARTIAL)
        
        return {
            "total": total,
            "success": success,
            "failed": failed,
            "skipped": skipped,
            "partial": partial,
            "success_rate": success / total if total > 0 else 0.0
        }

