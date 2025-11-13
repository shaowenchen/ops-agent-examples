# -*- coding: utf-8 -*-
"""
ReAct Agent - Pure ReAct (Reasoning, Acting, Observing) pattern implementation
Best practices implementation with improved error handling and performance
"""

import json
import asyncio
import re
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum

from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from pydantic import BaseModel, Field, create_model

from fastmcp import Client

from ..config import ConfigLoader
from ..utils.logging import get_logger
from ..utils.formatting import format_task_result
from ..utils.callbacks import DetailedLoggingCallback

logger = get_logger(__name__)


class StepStatus(Enum):
    """Status of a ReAct step"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ReActStep:
    """Represents a single ReAct step with enhanced metadata"""
    step_number: int
    thought: str
    action: Optional[str] = None
    action_input: Optional[Dict[str, Any]] = None
    observation: Optional[str] = None
    status: StepStatus = StepStatus.PENDING
    is_final: bool = False
    final_answer: Optional[str] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None


class ReActAgent:
    """
    Enhanced ReAct (Reasoning, Acting, Observing) Agent with best practices
    
    Features:
    - Pure ReAct pattern implementation
    - Enhanced error handling and recovery
    - Performance monitoring
    - Configurable step limits and timeouts
    - Detailed logging and debugging
    - Tool validation and safety checks
    """
    
    def __init__(
        self,
        config_loader: ConfigLoader,
        verbose: bool = True,
        max_steps: int = 10,
        step_timeout: float = 30.0,
        enable_tool_validation: bool = True
    ):
        """
        Initialize Enhanced ReAct Agent
        
        Args:
            config_loader: Configuration loader instance
            verbose: Enable verbose logging
            max_steps: Maximum number of ReAct steps
            step_timeout: Timeout for each step in seconds
            enable_tool_validation: Enable tool parameter validation
        """
        self.config_loader = config_loader
        self.verbose = verbose
        self.max_steps = max_steps
        self.step_timeout = step_timeout
        self.enable_tool_validation = enable_tool_validation
        
        # Load configurations
        self.openai_config = config_loader.openai_config
        self.mcp_config = config_loader.mcp_config
        
        # Initialize callback for detailed logging
        self.callback = DetailedLoggingCallback()
        
        # Initialize LLM with optimized settings
        self.llm = self._create_llm()
        
        # Initialize MCP client
        logger.info(f"Connecting to MCP server: {self.mcp_config.server_url}")
        self.mcp_server_url = self.mcp_config.server_url
        self.mcp_token = self.mcp_config.token
        
        # Load MCP tools dynamically
        self.tools = self._load_mcp_tools()
        logger.info(f"Loaded {len(self.tools)} tools from MCP server")
        
        # Log available tools with enhanced information
        if self.tools:
            logger.info("=" * 80)
            logger.info("📦 Available MCP Tools for ReAct Agent:")
            logger.info("=" * 80)
            for idx, tool in enumerate(self.tools, 1):
                logger.info(f"{idx}. {tool['name']}")
                logger.info(f"   Description: {tool['description'][:100]}...")
                if tool.get('input_schema'):
                    params = tool['input_schema'].get('properties', {})
                    logger.info(f"   Parameters: {list(params.keys())}")
            logger.info("=" * 80)
        
        logger.info("Enhanced ReAct Agent initialized successfully")
    
    def _create_llm(self) -> ChatOpenAI:
        """Create optimized LLM instance"""
        llm_kwargs = {
            "model": self.openai_config.model,
            "api_key": self.openai_config.api_key,
            "base_url": self.openai_config.api_host,
            "temperature": 0.1,  # Slightly higher for more creative reasoning
            "verbose": self.verbose,
            "callbacks": [self.callback]
        }
        
        if self.openai_config.max_tokens:
            llm_kwargs["max_tokens"] = self.openai_config.max_tokens
        
        return ChatOpenAI(**llm_kwargs)
    
    def _load_mcp_tools(self) -> List[Dict[str, Any]]:
        """Load tools from MCP server with enhanced error handling"""
        try:
            async def fetch_tools():
                server_url = self.mcp_server_url
                client_kwargs = {}
                
                logger.info(f"Fetching tools from MCP server: {server_url}")
                async with Client(server_url, **client_kwargs) as client:
                    mcp_tools = await client.list_tools()
                    logger.info(f"✅ Discovered {len(mcp_tools)} tools from MCP server")
                    
                    # Convert to enhanced dict format
                    tools = []
                    for tool in mcp_tools:
                        tools.append({
                            'name': tool.name,
                            'description': tool.description or f"Tool: {tool.name}",
                            'input_schema': tool.inputSchema if hasattr(tool, 'inputSchema') else None,
                            'mcp_tool': tool  # Keep reference to original tool
                        })
                    
                    return tools
            
            # Run async function with proper error handling
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import nest_asyncio
                    nest_asyncio.apply()
                    return loop.run_until_complete(fetch_tools())
                else:
                    return loop.run_until_complete(fetch_tools())
            except RuntimeError:
                return asyncio.run(fetch_tools())
            
        except Exception as e:
            logger.error(f"❌ Error loading MCP tools: {str(e)}")
            logger.exception("Full error traceback:")
            return []
    
    def _validate_tool_parameters(self, tool_name: str, parameters: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate tool parameters against schema"""
        if not self.enable_tool_validation:
            return True, ""
        
        # Find tool schema
        tool_info = None
        for tool in self.tools:
            if tool['name'] == tool_name:
                tool_info = tool
                break
        
        if not tool_info or not tool_info.get('input_schema'):
            return True, ""  # No schema to validate against
        
        schema = tool_info['input_schema']
        properties = schema.get('properties', {})
        required = schema.get('required', [])
        
        # Check required parameters
        for param in required:
            if param not in parameters:
                return False, f"Missing required parameter: {param}"
        
        # Check parameter types
        for param_name, param_value in parameters.items():
            if param_name in properties:
                expected_type = properties[param_name].get('type', 'string')
                if not self._validate_parameter_type(param_value, expected_type):
                    return False, f"Parameter '{param_name}' has wrong type. Expected: {expected_type}"
        
        return True, ""
    
    def _validate_parameter_type(self, value: Any, expected_type: str) -> bool:
        """Validate parameter type"""
        type_mapping = {
            'string': str,
            'number': (int, float),
            'integer': int,
            'boolean': bool,
            'array': list,
            'object': dict
        }
        
        expected_python_type = type_mapping.get(expected_type, str)
        if isinstance(expected_python_type, tuple):
            return isinstance(value, expected_python_type)
        return isinstance(value, expected_python_type)
    
    def _format_tools_for_prompt(self) -> str:
        """Format available tools for inclusion in prompts with enhanced information"""
        if not self.tools:
            return "No tools available"
        
        tool_descriptions = []
        for idx, tool in enumerate(self.tools, 1):
            name = tool['name']
            description = tool['description']
            
            # Add parameter information if available
            params_info = ""
            if tool.get('input_schema') and tool['input_schema'].get('properties'):
                properties = tool['input_schema']['properties']
                required = tool['input_schema'].get('required', [])
                
                params = []
                for param_name, param_info in properties.items():
                    param_type = param_info.get('type', 'string')
                    param_desc = param_info.get('description', '')
                    is_required = param_name in required
                    req_marker = " (required)" if is_required else " (optional)"
                    params.append(f"    - {param_name}: {param_type}{req_marker} - {param_desc}")
                
                if params:
                    params_info = f"\n  Parameters:\n" + "\n".join(params)
            
            tool_descriptions.append(f"{idx}. {name}\n   Description: {description}{params_info}")
        
        return "\n\n".join(tool_descriptions)
    
    def _create_react_prompt(self, question: str, steps: List[ReActStep]) -> str:
        """Create enhanced ReAct prompt with better formatting and instructions"""
        
        # Format previous steps
        previous_steps = ""
        for step in steps:
            previous_steps += f"Step {step.step_number}:\n"
            previous_steps += f"Thought: {step.thought}\n"
            if step.action:
                previous_steps += f"Action: {step.action}\n"
                if step.action_input:
                    previous_steps += f"Action Input: {json.dumps(step.action_input, ensure_ascii=False)}\n"
            if step.observation:
                previous_steps += f"Observation: {step.observation}\n"
            if step.is_final and step.final_answer:
                previous_steps += f"Final Answer: {step.final_answer}\n"
            if step.error:
                previous_steps += f"Error: {step.error}\n"
            previous_steps += "\n"
        
        # Format available tools
        available_tools = self._format_tools_for_prompt()
        
        prompt = f"""You are a helpful assistant that can use tools to answer questions. You should follow the ReAct (Reasoning, Acting, Observing) pattern.

Available tools:
{available_tools}

Instructions:
1. Think step by step about what you need to do
2. If you need to use a tool, specify the action and input
3. Wait for the observation before proceeding
4. Continue until you have enough information to provide a final answer
5. Be precise with tool parameters and handle errors gracefully

Format your response as follows:
Thought: [your reasoning about what to do next]
Action: [tool name, or "None" if no tool needed]
Action Input: [JSON object with parameters, or "None" if no tool needed]

{previous_steps}Question: {question}
Thought:"""
        
        return prompt
    
    def _parse_react_response(self, response: str) -> Tuple[str, Optional[str], Optional[Dict[str, Any]]]:
        """Parse ReAct response with enhanced error handling"""
        lines = response.strip().split('\n')
        
        thought = ""
        action = None
        action_input = None
        
        for line in lines:
            line = line.strip()
            if line.startswith("Thought:"):
                thought = line[8:].strip()
            elif line.startswith("Action:"):
                action_text = line[7:].strip()
                if action_text.lower() != "none":
                    action = action_text
            elif line.startswith("Action Input:"):
                input_text = line[13:].strip()
                if input_text.lower() != "none":
                    try:
                        action_input = json.loads(input_text)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse action input as JSON: {input_text}, error: {e}")
                        # Try to fix common JSON issues
                        try:
                            # Handle single quotes
                            fixed_input = input_text.replace("'", '"')
                            action_input = json.loads(fixed_input)
                        except:
                            action_input = {"input": input_text}
        
        return thought, action, action_input
    
    async def _call_tool_with_timeout(self, tool_name: str, parameters: Dict[str, Any], max_retries: int = 2) -> str:
        """Call a specific MCP tool with timeout and retry logic"""
        logger.info("=" * 80)
        logger.info(f"🔧 CALLING TOOL: {tool_name}")
        logger.info("=" * 80)
        logger.info(f"📥 Parameters: {json.dumps(parameters, indent=2, ensure_ascii=False)}")
        
        # Validate parameters first
        is_valid, error_msg = self._validate_tool_parameters(tool_name, parameters)
        if not is_valid:
            return f"Parameter validation error: {error_msg}"
        
        # Find the tool
        tool_info = None
        for tool in self.tools:
            if tool['name'] == tool_name:
                tool_info = tool
                break
        
        if not tool_info:
            error_msg = f"Tool '{tool_name}' not found"
            logger.error(error_msg)
            return error_msg
        
        # Retry logic for tool calls
        for attempt in range(max_retries):
            try:
                logger.info(f"🔄 Tool attempt {attempt + 1}/{max_retries}")
                
                # Create client and call tool with timeout
                server_url = self.mcp_server_url
                client_kwargs = {}
                
                async with Client(server_url, **client_kwargs) as client:
                    logger.info(f"📞 Calling tool: {tool_name}")
                    
                    # Use asyncio.wait_for for timeout
                    result = await asyncio.wait_for(
                        client.call_tool(tool_name, parameters),
                        timeout=self.step_timeout
                    )
                    
                    # Extract text content from result
                    if hasattr(result, 'content') and result.content:
                        extracted = result.content[0].text if hasattr(result.content[0], 'text') else str(result.content[0])
                        logger.info(f"📤 Result: {extracted[:500]}...")
                        logger.info("=" * 80)
                        return extracted
                    
                    result_str = str(result)
                    logger.info(f"📤 Result: {result_str[:500]}...")
                    logger.info("=" * 80)
                    return result_str
                    
            except asyncio.TimeoutError:
                logger.warning(f"⏰ Tool timeout on attempt {attempt + 1}")
                if attempt < max_retries - 1:
                    wait_time = 1 + attempt  # Short wait for tool retries
                    logger.info(f"⏳ Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
                else:
                    error_msg = f"Tool call timed out after {max_retries} attempts"
                    logger.error("=" * 80)
                    logger.error(f"⏰ TIMEOUT: {error_msg}")
                    logger.error("=" * 80)
                    return error_msg
                    
            except Exception as e:
                if self._is_recoverable_error(e) and attempt < max_retries - 1:
                    logger.warning(f"⚠️ Recoverable tool error on attempt {attempt + 1}: {e}")
                    wait_time = 1 + attempt
                    logger.info(f"⏳ Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
                else:
                    error_msg = f"Error calling tool {tool_name}: {str(e)}"
                    logger.error("=" * 80)
                    logger.error(f"❌ {error_msg}")
                    logger.error("=" * 80)
                    return error_msg
        
        return f"Tool call failed after {max_retries} attempts"
    
    def _should_continue(self, steps: List[ReActStep], max_steps: int) -> bool:
        """Determine if we should continue the ReAct loop with enhanced logic"""
        if len(steps) >= max_steps:
            logger.warning(f"Reached maximum steps limit: {max_steps}")
            return False
        
        # Check if the last step was final
        if steps and steps[-1].is_final:
            return False
        
        # Check for consecutive failures
        if len(steps) >= 3:
            recent_steps = steps[-3:]
            if all(step.error for step in recent_steps):
                logger.warning("Too many consecutive failures, stopping")
                return False
        
        return True
    
    def _extract_final_answer(self, response: str) -> Optional[str]:
        """Extract final answer from response with improved parsing"""
        lines = response.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith("Final Answer:"):
                return line[13:].strip()
        return None
    
    def _detect_repetitive_thinking(self, steps: List[ReActStep], current_thought: str) -> bool:
        """Detect if the agent is stuck in repetitive thinking patterns"""
        if len(steps) < 3:
            return False
        
        # Check if the current thought is very similar to recent thoughts
        recent_thoughts = [step.thought for step in steps[-3:] if step.thought]
        if not recent_thoughts:
            return False
        
        # Simple similarity check - if current thought contains key phrases from recent thoughts
        current_lower = current_thought.lower()
        for recent_thought in recent_thoughts:
            recent_lower = recent_thought.lower()
            # Check for high similarity (more than 70% overlap in key words)
            if self._calculate_similarity(current_lower, recent_lower) > 0.7:
                return True
        
        # Check for exact repetition patterns
        if len(steps) >= 5:
            last_5_thoughts = [step.thought for step in steps[-5:] if step.thought]
            if len(set(last_5_thoughts)) <= 2:  # Only 2 unique thoughts in last 5 steps
                return True
        
        return False
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple word-based similarity between two texts"""
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _generate_final_answer_from_context(self, steps: List[ReActStep], question: str) -> str:
        """Generate a final answer based on the context from previous steps"""
        # Find the most recent successful tool execution
        for step in reversed(steps):
            if step.observation and step.status == StepStatus.COMPLETED:
                # Extract key information from the observation
                observation = step.observation
                
                # Try to parse JSON responses
                try:
                    import json
                    if observation.startswith('{') and observation.endswith('}'):
                        data = json.loads(observation)
                        if 'count' in data:
                            return f"Found {data['count']} available SOPS procedures. Here are the details: {observation[:500]}..."
                        elif 'services' in data:
                            return f"Found {len(data['services'])} services. Here are the details: {observation[:500]}..."
                except:
                    pass
                
                # For non-JSON responses, return a summary
                return f"Based on the available information: {observation[:300]}..."
        
        # Fallback answer
        return f"I have gathered information related to your question: '{question}'. Please see the detailed results above."
    
    def _is_recoverable_error(self, error: Exception) -> bool:
        """Check if an error is recoverable (timeout, network issues, etc.)"""
        error_str = str(error).lower()
        recoverable_patterns = [
            'timeout',
            '524',
            'connection',
            'network',
            'http',
            'retry',
            'temporary'
        ]
        return any(pattern in error_str for pattern in recoverable_patterns)
    
    async def _get_llm_response_with_retry(self, prompt: str, step_number: int, max_retries: int = 3) -> str:
        """Get LLM response with retry logic for handling timeouts and network issues"""
        import asyncio
        
        for attempt in range(max_retries):
            try:
                logger.info(f"🔄 LLM attempt {attempt + 1}/{max_retries} for step {step_number}")
                
                # Use asyncio.wait_for to handle timeouts
                response = await asyncio.wait_for(
                    self._call_llm_async(prompt),
                    timeout=self.step_timeout
                )
                return response.content
                
            except asyncio.TimeoutError:
                logger.warning(f"⏰ LLM timeout on attempt {attempt + 1} for step {step_number}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.info(f"⏳ Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
                else:
                    raise Exception(f"LLM timeout after {max_retries} attempts")
                    
            except Exception as e:
                if self._is_recoverable_error(e) and attempt < max_retries - 1:
                    logger.warning(f"⚠️ Recoverable error on attempt {attempt + 1}: {e}")
                    wait_time = 2 ** attempt
                    logger.info(f"⏳ Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
                else:
                    raise e
        
        raise Exception(f"Failed to get LLM response after {max_retries} attempts")
    
    async def _call_llm_async(self, prompt: str):
        """Async wrapper for LLM call"""
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        
        def _sync_llm_call():
            return self.llm.invoke([HumanMessage(content=prompt)], config={"callbacks": [self.callback]})
        
        # Run the synchronous LLM call in a thread pool
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            return await loop.run_in_executor(executor, _sync_llm_call)
    
    async def execute_react_loop(self, question: str) -> List[ReActStep]:
        """
        Execute the enhanced ReAct loop for a given question
        
        Args:
            question: The question to answer
            
        Returns:
            List of ReAct steps taken
        """
        steps = []
        step_number = 1
        
        logger.info("🤔 Starting Enhanced ReAct loop...")
        logger.info(f"Question: {question}")
        logger.info(f"Max steps: {self.max_steps}, Timeout per step: {self.step_timeout}s")
        
        while self._should_continue(steps, self.max_steps):
            logger.info(f"\n--- ReAct Step {step_number} ---")
            
            # Create prompt with current question and previous steps
            prompt = self._create_react_prompt(question, steps)
            
            # Get LLM response with retry logic
            logger.info("🧠 Getting LLM response...")
            try:
                response_text = await self._get_llm_response_with_retry(prompt, step_number)
                logger.info(f"📝 LLM Response:\n{response_text}")
                
            except Exception as e:
                logger.error(f"Error getting LLM response after retries: {e}")
                step = ReActStep(
                    step_number=step_number,
                    thought="Error getting LLM response",
                    status=StepStatus.FAILED,
                    error=str(e)
                )
                steps.append(step)
                break
            
            # Parse the response
            thought, action, action_input = self._parse_react_response(response_text)
            
            # Create step
            step = ReActStep(
                step_number=step_number,
                thought=thought,
                status=StepStatus.IN_PROGRESS
            )
            
            # Check if this is a final answer
            final_answer = self._extract_final_answer(response_text)
            if final_answer:
                step.is_final = True
                step.final_answer = final_answer
                step.status = StepStatus.COMPLETED
                steps.append(step)
                logger.info(f"✅ Final answer found: {final_answer}")
                break
            
            # Check for repetitive thinking patterns (anti-loop mechanism)
            if self._detect_repetitive_thinking(steps, thought):
                logger.warning("🔄 Detected repetitive thinking pattern, forcing final answer")
                step.is_final = True
                step.final_answer = self._generate_final_answer_from_context(steps, question)
                step.status = StepStatus.COMPLETED
                steps.append(step)
                logger.info(f"✅ Forced final answer: {step.final_answer}")
                break
            
            # If action is specified, execute it
            if action:
                step.action = action
                step.action_input = action_input
                
                logger.info(f"⚙️ Executing action: {action}")
                if action_input:
                    logger.info(f"📥 With input: {action_input}")
                
                # Call the tool with timeout
                import time
                start_time = time.time()
                try:
                    observation = await self._call_tool_with_timeout(action, action_input or {})
                    step.observation = observation
                    step.status = StepStatus.COMPLETED
                    step.execution_time = time.time() - start_time
                    
                    logger.info(f"👁️ Observation: {observation[:200]}...")
                    logger.info(f"⏱️ Execution time: {step.execution_time:.2f}s")
                    
                except Exception as e:
                    step.status = StepStatus.FAILED
                    step.error = str(e)
                    step.execution_time = time.time() - start_time
                    logger.error(f"❌ Tool execution failed: {e}")
            else:
                logger.info("ℹ️ No action specified, continuing with reasoning...")
                step.status = StepStatus.COMPLETED
            
            steps.append(step)
            step_number += 1
        
        if not steps or not steps[-1].is_final:
            logger.warning(f"⚠️ ReAct loop completed without final answer after {len(steps)} steps")
        
        return steps
    
    def execute_question(self, question: str) -> Dict[str, Any]:
        """
        Execute a question using enhanced ReAct pattern
        
        Args:
            question: The question to answer
            
        Returns:
            Execution result with enhanced metadata
        """
        try:
            # Run the ReAct loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import nest_asyncio
                    nest_asyncio.apply()
                    steps = loop.run_until_complete(self.execute_react_loop(question))
                else:
                    steps = loop.run_until_complete(self.execute_react_loop(question))
            except RuntimeError:
                steps = asyncio.run(self.execute_react_loop(question))
            
            # Extract final result
            final_answer = None
            if steps and steps[-1].is_final:
                final_answer = steps[-1].final_answer
            elif steps and steps[-1].observation:
                final_answer = steps[-1].observation
            
            # Calculate statistics
            total_time = sum(step.execution_time or 0 for step in steps)
            successful_steps = sum(1 for step in steps if step.status == StepStatus.COMPLETED)
            failed_steps = sum(1 for step in steps if step.status == StepStatus.FAILED)
            
            # Format result
            return {
                "status": "success" if final_answer else "partial",
                "final_answer": final_answer,
                "steps": steps,
                "total_steps": len(steps),
                "successful_steps": successful_steps,
                "failed_steps": failed_steps,
                "total_execution_time": total_time,
                "average_step_time": total_time / len(steps) if steps else 0
            }
            
        except Exception as e:
            logger.error(f"Error executing question: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
                "steps": [],
                "total_steps": 0,
                "successful_steps": 0,
                "failed_steps": 0,
                "total_execution_time": 0,
                "average_step_time": 0
            }
    
    def execute_tasks(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Execute a list of tasks using enhanced ReAct pattern
        
        Args:
            tasks: List of task configurations with 'intent' and 'description'
            
        Returns:
            List of task execution results
        """
        results = []
        
        for idx, task in enumerate(tasks, 1):
            task_description = task.get("description", f"Task {idx}")
            task_intent = task.get("intent", task_description)
            
            logger.info(f"\n{'='*80}")
            logger.info(f"🎯 ReAct Task {idx}: {task_description}")
            logger.info(f"   Intent: {task_intent}")
            logger.info(f"{'='*80}\n")
            
            try:
                # Execute using ReAct pattern
                result = self.execute_question(task_intent)
                
                # Format result for consistency
                formatted_result = format_task_result(
                    task_name=f"react-task-{idx}",
                    status=result["status"],
                    result={
                        "output": result.get("final_answer", ""),
                        "steps": result.get("steps", []),
                        "total_steps": result.get("total_steps", 0),
                        "successful_steps": result.get("successful_steps", 0),
                        "failed_steps": result.get("failed_steps", 0),
                        "total_execution_time": result.get("total_execution_time", 0),
                        "average_step_time": result.get("average_step_time", 0),
                        "summary": self._generate_react_summary(task_intent, result)
                    }
                )
                
                results.append(formatted_result)
                logger.info(f"✅ ReAct Task {idx} completed: {result['status']}")
                logger.info(f"   Steps: {result.get('total_steps', 0)}")
                logger.info(f"   Time: {result.get('total_execution_time', 0):.2f}s")
                
            except Exception as e:
                logger.error(f"❌ Error executing ReAct task {idx}: {str(e)}")
                result = format_task_result(f"react-task-{idx}", "failed", {"error": str(e)})
                results.append(result)
        
        return results
    
    def _generate_react_summary(self, intent: str, result: Dict[str, Any]) -> str:
        """Generate an enhanced summary of the ReAct execution"""
        steps = result.get("steps", [])
        final_answer = result.get("final_answer", "")
        total_steps = result.get("total_steps", 0)
        successful_steps = result.get("successful_steps", 0)
        failed_steps = result.get("failed_steps", 0)
        total_time = result.get("total_execution_time", 0)
        avg_time = result.get("average_step_time", 0)
        
        summary = f"""# 📋 Enhanced ReAct Execution Summary

## 🎯 Intent
{intent}

## 📊 Execution Statistics
- **Total Steps**: {total_steps}
- **Successful Steps**: {successful_steps}
- **Failed Steps**: {failed_steps}
- **Total Execution Time**: {total_time:.2f}s
- **Average Step Time**: {avg_time:.2f}s

## 🔄 ReAct Steps ({total_steps} total)
"""
        
        for step in steps:
            summary += f"\n### Step {step.step_number}\n"
            summary += f"**Thought:** {step.thought}\n"
            summary += f"**Status:** {step.status.value}\n"
            
            if step.action:
                summary += f"**Action:** {step.action}\n"
                if step.action_input:
                    summary += f"**Action Input:** {json.dumps(step.action_input, indent=2, ensure_ascii=False)}\n"
            
            if step.observation:
                summary += f"**Observation:** {step.observation[:200]}...\n"
            
            if step.error:
                summary += f"**Error:** {step.error}\n"
            
            if step.execution_time:
                summary += f"**Execution Time:** {step.execution_time:.2f}s\n"
            
            if step.is_final and step.final_answer:
                summary += f"**Final Answer:** {step.final_answer}\n"
        
        summary += f"\n## ✨ Final Result\n{final_answer}\n"
        
        return summary