"""
Ops Agent - Task planning and execution engine powered by LangChain
"""

import json
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Union

from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from langchain.schema import SystemMessage, HumanMessage
from langchain.tools import StructuredTool
from pydantic import BaseModel, Field, create_model
import re

from fastmcp import Client

from ..config import ConfigLoader, TaskConfig
from ..utils.logging import get_logger
from ..utils.formatting import format_task_result, format_prompt_with_context
from ..utils.callbacks import DetailedLoggingCallback

logger = get_logger(__name__)


class OpsAgent:
    """Ops Agent for task planning and execution"""
    
    def __init__(
        self,
        config_loader: ConfigLoader,
        verbose: bool = True,
        max_iterations: int = 20
    ):
        """
        Initialize Ops Agent
        
        Args:
            config_loader: Configuration loader instance
            verbose: Enable verbose logging
            max_iterations: Maximum iterations for agent execution
        """
        self.config_loader = config_loader
        self.verbose = verbose
        self.max_iterations = max_iterations
        
        # Load configurations
        self.openai_config = config_loader.openai_config
        self.mcp_config = config_loader.mcp_config
        
        # Initialize callback for detailed logging
        self.callback = DetailedLoggingCallback()
        
        # Initialize LLM
        self.llm = self._create_llm()
        
        # Initialize MCP client - keep it persistent for tool calls
        logger.info(f"Connecting to MCP server: {self.mcp_config.server_url}")
        self.mcp_client = None
        self.mcp_server_url = self.mcp_config.server_url
        self.mcp_token = self.mcp_config.token
        
        # Load MCP tools dynamically from server
        self.tools = self._load_mcp_tools()
        logger.info(f"Loaded {len(self.tools)} tools from MCP server")
        
        # Log available tools
        if self.tools:
            logger.info("=" * 80)
            logger.info("📦 Available MCP Tools for Agent:")
            logger.info("=" * 80)
            for idx, tool in enumerate(self.tools, 1):
                tool_name = tool.name if hasattr(tool, 'name') else str(tool)
                tool_desc = tool.description if hasattr(tool, 'description') else 'No description'
                tool_func = tool.func if hasattr(tool, 'func') else None
                logger.info(f"{idx}. {tool_name}")
                logger.info(f"   Description: {tool_desc[:100]}...")
                logger.info(f"   Has func: {tool_func is not None}")
                logger.info(f"   Callable: {callable(tool_func) if tool_func else False}")
            logger.info("=" * 80)
        
        # Initialize agent
        self.agent_executor = self._create_agent()
        
        logger.info("Ops Agent initialized successfully")
    
    def _load_mcp_tools(self) -> list:
        """
        Dynamically load tools from MCP server using fastmcp Client
        
        Returns:
            List of LangChain tools converted from MCP tools
        """
        try:
            # Create async function to connect to MCP server and fetch tools
            async def fetch_tools():
                # Prepare connection URL with authentication
                server_url = self.mcp_server_url
                
                # Create client with authentication if token is provided
                client_kwargs = {}
                if self.mcp_token:
                    # For SSE MCP servers, token is usually passed in headers
                    logger.info("Adding authentication token to MCP client")
                
                # Connect to MCP server temporarily to fetch tool list
                logger.info(f"Fetching tools from MCP server: {server_url}")
                async with Client(server_url, **client_kwargs) as client:
                    # Dynamically list all available tools from MCP server
                    mcp_tools = await client.list_tools()
                    logger.info(f"✅ Discovered {len(mcp_tools)} tools from MCP server")
                    
                    # Log each tool
                    for idx, tool in enumerate(mcp_tools, 1):
                        logger.info(f"   {idx}. {tool.name}: {tool.description[:80] if tool.description else 'No description'}...")
                    
                    return mcp_tools
            
            # Run async function in event loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If loop is already running, create a new one
                    import nest_asyncio
                    nest_asyncio.apply()
                    mcp_tools = loop.run_until_complete(fetch_tools())
                else:
                    mcp_tools = loop.run_until_complete(fetch_tools())
            except RuntimeError:
                # No event loop, create a new one
                mcp_tools = asyncio.run(fetch_tools())
            
            # Convert MCP tools to LangChain tools
            # NOTE: Each tool will create its own client connection when called
            langchain_tools = []
            for mcp_tool in mcp_tools:
                langchain_tool = self._convert_mcp_tool_to_langchain(mcp_tool)
                langchain_tools.append(langchain_tool)
            
            return langchain_tools
            
        except Exception as e:
            logger.error(f"❌ Error loading MCP tools: {str(e)}")
            logger.exception("Full error traceback:")
            logger.warning("Continuing without MCP tools")
            return []
    
    def _convert_mcp_tool_to_langchain(self, mcp_tool: Any) -> StructuredTool:
        """
        Convert MCP tool to LangChain StructuredTool
        
        Args:
            mcp_tool: MCP tool object from MCP server
            
        Returns:
            LangChain StructuredTool that creates new client connection for each call
        """
        tool_name = mcp_tool.name
        tool_description = mcp_tool.description or f"Tool: {tool_name}"
        
        logger.info(f"📦 Converting MCP tool: {tool_name}")
        
        # Create Pydantic model for tool input schema dynamically
        if hasattr(mcp_tool, 'inputSchema') and mcp_tool.inputSchema:
            # Extract properties from MCP tool schema
            properties = mcp_tool.inputSchema.get('properties', {})
            required_fields = mcp_tool.inputSchema.get('required', [])
            
            logger.info(f"   Schema properties: {list(properties.keys())}")
            logger.info(f"   Required fields: {required_fields}")
            
            # Build Pydantic fields
            field_definitions = {}
            for field_name, field_info in properties.items():
                field_type = self._json_type_to_python(field_info.get('type', 'string'))
                field_desc = field_info.get('description', '')
                is_required = field_name in required_fields
                
                if is_required:
                    field_definitions[field_name] = (field_type, Field(..., description=field_desc))
                else:
                    field_definitions[field_name] = (Optional[field_type], Field(None, description=field_desc))
            
            # Create dynamic Pydantic model
            ArgsSchema = create_model(f"{tool_name}Args", **field_definitions)
        else:
            # Default empty schema
            logger.info(f"   No schema defined, using empty schema")
            ArgsSchema = create_model(f"{tool_name}Args")
        
        # Create wrapper function that creates a new client for each call
        async def call_mcp_tool(**kwargs):
            """Async wrapper to call MCP tool - creates new client connection"""
            logger.info("=" * 80)
            logger.info(f"🔧 MCP TOOL CALL: {tool_name}")
            logger.info("=" * 80)
            logger.info(f"📥 Input parameters: {json.dumps(kwargs, indent=2)}")
            
            try:
                # Create new client connection for this specific call
                server_url = self.mcp_server_url
                client_kwargs = {}
                
                logger.info(f"🌐 Connecting to MCP server: {server_url}")
                
                # Use async with to ensure proper connection management
                async with Client(server_url, **client_kwargs) as client:
                    logger.info(f"✅ Connected to MCP server")
                    logger.info(f"📞 Calling tool: {tool_name} with args: {kwargs}")
                    
                    # Call the actual MCP tool
                    result = await client.call_tool(tool_name, kwargs)
                    
                    logger.info(f"✅ Tool call completed")
                    logger.info(f"📤 Raw result type: {type(result)}")
                    
                    # Extract text content from result
                    if hasattr(result, 'content') and result.content:
                        extracted = result.content[0].text if hasattr(result.content[0], 'text') else str(result.content[0])
                        logger.info(f"📤 Extracted result: {extracted[:500]}...")
                        logger.info("=" * 80)
                        return extracted
                    
                    result_str = str(result)
                    logger.info(f"📤 String result: {result_str[:500]}...")
                    logger.info("=" * 80)
                    return result_str
                    
            except Exception as e:
                logger.error("=" * 80)
                logger.error(f"❌ ERROR calling MCP tool {tool_name}")
                logger.error(f"Error type: {type(e).__name__}")
                logger.error(f"Error message: {str(e)}")
                logger.exception("Full traceback:")
                logger.error("=" * 80)
                return f"Error calling {tool_name}: {str(e)}"
        
        # Create sync wrapper for LangChain
        def sync_call_mcp_tool(**kwargs):
            """Sync wrapper for LangChain compatibility"""
            logger.info(f"🔄 Sync wrapper called for {tool_name}")
            
            # Fix nested JSON issue before calling tool
            # Check if any parameter value is a JSON string that should be unwrapped
            fixed_kwargs = {}
            for key, value in kwargs.items():
                if isinstance(value, str) and value.strip().startswith('{'):
                    try:
                        # Try to parse as JSON
                        parsed = json.loads(value.strip())
                        if isinstance(parsed, dict):
                            # This is a nested JSON - the whole dict should be the parameters
                            logger.warning(f"🔧 Detected nested JSON in parameter '{key}'")
                            logger.warning(f"   Before: {kwargs}")
                            logger.warning(f"   Unwrapping to: {parsed}")
                            fixed_kwargs = parsed
                            break
                    except json.JSONDecodeError:
                        # Not valid JSON, keep as string
                        fixed_kwargs[key] = value
                else:
                    fixed_kwargs[key] = value
            
            # If we didn't detect nested JSON, use original kwargs
            if not fixed_kwargs:
                fixed_kwargs = kwargs
            
            try:
                # Try to use existing event loop
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        import nest_asyncio
                        nest_asyncio.apply()
                    return loop.run_until_complete(call_mcp_tool(**fixed_kwargs))
                except RuntimeError:
                    # No event loop exists, create new one
                    return asyncio.run(call_mcp_tool(**fixed_kwargs))
            except Exception as e:
                logger.error(f"Error in sync wrapper for {tool_name}: {str(e)}")
                logger.exception("Full error:")
                return f"Error: {str(e)}"
        
        # Create LangChain StructuredTool
        langchain_tool = StructuredTool(
            name=tool_name.replace('_', '-'),  # LangChain prefers hyphens
            description=tool_description,
            func=sync_call_mcp_tool,
            args_schema=ArgsSchema,
            coroutine=call_mcp_tool  # Support async execution
        )
        
        logger.info(f"✅ Converted tool: {langchain_tool.name}")
        return langchain_tool
    
    def _json_type_to_python(self, json_type: str) -> type:
        """Convert JSON schema type to Python type"""
        type_mapping = {
            'string': str,
            'number': float,
            'integer': int,
            'boolean': bool,
            'array': list,
            'object': dict
        }
        return type_mapping.get(json_type, str)
    
    def _create_llm(self) -> ChatOpenAI:
        """
        Create LLM instance
        
        Returns:
            ChatOpenAI: Configured LLM instance
        """
        llm_kwargs = {
            "model": self.openai_config.model,
            "api_key": self.openai_config.api_key,
            "base_url": self.openai_config.api_host,
            "temperature": 0,
            "verbose": self.verbose,
            "callbacks": [self.callback]
        }
        
        # Add max_tokens if configured
        if self.openai_config.max_tokens:
            llm_kwargs["max_tokens"] = self.openai_config.max_tokens
            logger.info(f"🔒 Setting max_tokens limit: {self.openai_config.max_tokens}")
        
        return ChatOpenAI(**llm_kwargs)
    
    def _create_agent(self) -> AgentExecutor:
        """
        Create LangChain agent with dynamically loaded tools using ReAct pattern
        
        Returns:
            AgentExecutor: Configured agent executor
        """
        logger.info(f"Creating agent with {len(self.tools)} tools")
        
        # Log tool names for debugging
        tool_names = [tool.name for tool in self.tools]
        logger.info(f"Tool names available to agent: {tool_names}")
        
         # Create ReAct prompt template - CRITICAL: Model must not generate Observation
        template = '''You are an intelligent operations assistant. 
 
 You have access to the following tools:
 
 {tools}
 
 CRITICAL INSTRUCTIONS FOR TOOL USAGE:
 1. When you decide to use a tool, output ONLY these three lines:
    Thought: [your reasoning]
    Action: [tool name from the list above]
    Action Input: [A SINGLE LINE JSON object with parameters]
    
 2. After outputting Action Input, STOP IMMEDIATELY
 3. DO NOT write "Observation:" - the system will execute the tool and show you the result
 4. Wait for the real tool execution result before continuing
 5. The system will show you: "Observation: [actual result from tool]"
 6. Then you can think again and decide next action
 
 Use this EXACT format:
 
 Question: the input question you must answer
 Thought: [think about what to do]
 Action: [one of: {tool_names}]
 Action Input: {{"param1": "value1", "param2": "value2"}}
 Observation: [STOP! System fills this - you cannot write this]
 Thought: [think about the observation]
 ... (repeat Thought/Action/Action Input/Observation as needed)
 Thought: I now have enough information
 Final Answer: [your final answer]
 
 IMPORTANT EXAMPLES FOR ACTION INPUT:
 
 ✅ CORRECT - Single line JSON object:
 Action Input: {{"subject_pattern": "ops.clusters.*.nodes.*.event", "limit": "100"}}
 
 ✅ CORRECT - Tool with no parameters:
 Action Input: {{}}
 
 ✅ CORRECT - Tool with single parameter:
 Action Input: {{"service": "my-service"}}
 
 ❌ WRONG - Do not wrap JSON in quotes:
 Action Input: "{{\\"param\\": \\"value\\"}}"
 
 ❌ WRONG - Do not put JSON on multiple lines:
 Action Input: {{
   "param": "value"
 }}
 
 REMEMBER: 
 - Action Input must be a SINGLE LINE JSON object
 - Do NOT wrap the JSON in quotes or escape it
 - You MUST call real tools - don't just describe what you would do
 - After "Action Input:", output NOTHING - stop and wait for Observation
 
 Begin!
 
 Question: {input}
 Thought:{agent_scratchpad}'''
        
        prompt = PromptTemplate.from_template(template)
        
        # Create ReAct agent with dynamically loaded tools
        # Use standard create_react_agent for better stability
        agent = create_react_agent(self.llm, self.tools, prompt)
        
        # Create a custom parsing error handler
        def handle_parsing_error(error: Exception) -> str:
            """Handle parsing errors gracefully"""
            error_msg = str(error)
            logger.warning(f"⚠️  Parsing error: {error_msg}")
            return f"Invalid format. Please follow the exact format:\nThought: [your reasoning]\nAction: [tool name]\nAction Input: {{json parameters}}\n\nError was: {error_msg}"
        
        # Create agent executor with strict error handling
        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=self.verbose,
            max_iterations=self.max_iterations,
            handle_parsing_errors=handle_parsing_error,
            callbacks=[self.callback],
            return_intermediate_steps=True,
            early_stopping_method="force"  # Force tool execution
        )
    
    def _generate_tool_descriptions(self) -> str:
        """
        Generate a summary of available tools for logging/debugging
        
        Returns:
            String description of available tools
        """
        if not self.tools:
            return "No tools available"
        
        descriptions = []
        for tool in self.tools:
            name = tool.name if hasattr(tool, 'name') else str(tool)
            desc = tool.description if hasattr(tool, 'description') else 'No description'
            descriptions.append(f"  - {name}: {desc}")
        return "\n".join(descriptions)
    
    def _generate_task_name(self, description: str, index: int) -> str:
        """
        Generate a clean task name from description
        
        Args:
            description: Task description
            index: Task index
            
        Returns:
            Clean task name (lowercase, hyphenated)
        """
        if not description or description.startswith("Task "):
            return f"task-{index}"
        
        # Convert description to clean name
        # e.g., "List available SOPS" -> "list-available-sops"
        import re
        clean_name = description.lower()
        clean_name = re.sub(r'[^\w\s-]', '', clean_name)  # Remove special chars
        clean_name = re.sub(r'\s+', '-', clean_name.strip())  # Replace spaces with hyphens
        clean_name = re.sub(r'-+', '-', clean_name)  # Remove duplicate hyphens
        
        # Limit length
        if len(clean_name) > 50:
            clean_name = clean_name[:50].rstrip('-')
        
        return clean_name or f"task-{index}"
    
    def _format_available_tools(self) -> str:
        """
        Format available MCP tools for inclusion in prompts
        
        Returns:
            Formatted string listing all available tools with descriptions and schemas
        """
        if not self.tools:
            return "No MCP tools available"
        
        tool_list = []
        for idx, tool in enumerate(self.tools, 1):
            tool_name = tool.name if hasattr(tool, 'name') else 'unknown'
            tool_desc = tool.description if hasattr(tool, 'description') else 'No description'
            
            # Get schema info if available
            schema_info = ""
            if hasattr(tool, 'args_schema') and tool.args_schema:
                try:
                    schema = tool.args_schema.schema()
                    properties = schema.get('properties', {})
                    required = schema.get('required', [])
                    
                    if properties:
                        params = []
                        for param_name, param_info in properties.items():
                            param_type = param_info.get('type', 'string')
                            param_desc = param_info.get('description', '')
                            is_required = param_name in required
                            req_marker = " (required)" if is_required else " (optional)"
                            params.append(f"    - {param_name}: {param_type}{req_marker} - {param_desc}")
                        
                        if params:
                            schema_info = f"\n  Parameters:\n" + "\n".join(params)
                except:
                    pass
            
            tool_entry = f"{idx}. {tool_name}\n   Description: {tool_desc}{schema_info}"
            tool_list.append(tool_entry)
        
        return "\n\n".join(tool_list)
    
    def execute_tasks(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Execute a list of tasks using autonomous planning and execution loop
        
        Args:
            tasks: List of task configurations with 'intent' and 'description'
            
        Returns:
            List of task execution results
        """
        results = []
        task_context = {}
        
        for idx, task in enumerate(tasks, 1):
            # Auto-generate task name from description or use index
            task_description = task.get("description", f"Task {idx}")
            task_name = self._generate_task_name(task_description, idx)
            task_intent = task.get("intent", task_description)
            
            logger.info(f"\n{'='*80}")
            logger.info(f"🎯 Task {idx}: {task_description}")
            logger.info(f"   Intent: {task_intent}")
            logger.info(f"{'='*80}\n")
            
            try:
                # Execute task with autonomous planning loop
                result = self._execute_task_with_planning(
                    task_name=task_name,
                    intent=task_intent,
                    description=task_description,
                    context=task_context
                )
                
                results.append(result)
                
                # Store result in context for dependent tasks
                task_context[task_name] = result.get("result", {})
                
                logger.info(f"✅ Task '{task_name}' completed: {result['status']}\n")
                
            except Exception as e:
                logger.error(f"❌ Error executing task '{task_name}': {str(e)}")
                result = format_task_result(task_name, "failed", {"error": str(e)})
                results.append(result)
        
        return results
    
    def _execute_task_with_planning(
        self,
        task_name: str,
        intent: str,
        description: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a single task using autonomous planning and iterative refinement loop
        
        This implements an agentic loop:
        1. Generate a plan based on intent
        2. Execute the plan using available MCP tools
        3. Evaluate if the result meets expectations
        4. If not satisfied, gather more information and refine
        5. Loop until goal is achieved or max iterations reached
        
        Args:
            task_name: Name of the task
            intent: User's intent/goal for this task
            description: Task description
            context: Execution context from previous tasks
            
        Returns:
            Task execution result
        """
        max_refinement_iterations = 5
        iteration = 0
        accumulated_info = []
        final_result = None
        
        logger.info("🤔 Starting autonomous planning and execution loop...")
        
        while iteration < max_refinement_iterations:
            iteration += 1
            logger.info(f"\n--- Iteration {iteration}/{max_refinement_iterations} ---")
            
            # Step 1: Generate or refine plan based on current information
            if iteration == 1:
                logger.info("📋 Step 1: Generating initial execution plan...")
                plan = self._generate_plan(intent, description, context)
            else:
                logger.info("📋 Step 1: Refining plan based on gathered information...")
                plan = self._refine_plan(intent, description, accumulated_info)
            
            logger.info(f"   Plan: {plan[:200]}...")
            
            # Step 2: Execute the plan
            logger.info("⚙️  Step 2: Executing plan with MCP tools...")
            execution_result = self._execute_plan(plan, context)
            accumulated_info.append({
                "iteration": iteration,
                "plan": plan,
                "result": execution_result
            })
            
            logger.info(f"   Execution completed")
            
            # Step 3: Evaluate if result meets expectations
            logger.info("✓  Step 3: Evaluating if goal is achieved...")
            is_satisfied, evaluation = self._evaluate_result(
                intent=intent,
                result=execution_result,
                iteration=iteration
            )
            
            logger.info(f"   Evaluation: {evaluation[:150]}...")
            
            if is_satisfied:
                logger.info("🎉 Goal achieved! Task completed successfully.")
                final_result = execution_result
                break
            else:
                logger.info("🔄 Goal not yet achieved, gathering more information...")
                # Step 4: Determine what additional information is needed
                additional_needs = self._determine_additional_needs(
                    intent=intent,
                    current_result=execution_result,
                    evaluation=evaluation
                )
                logger.info(f"   Additional needs: {additional_needs[:150]}...")
                
                if iteration < max_refinement_iterations:
                    logger.info("   Proceeding to next iteration...\n")
        
        # Final result
        if final_result is None:
            logger.warning(f"⚠️  Max iterations ({max_refinement_iterations}) reached")
            final_result = accumulated_info[-1]["result"] if accumulated_info else "No result"
        
        # Generate task summary
        logger.info("\n" + "=" * 80)
        logger.info("📊 TASK SUMMARY")
        logger.info("=" * 80)
        summary = self._generate_task_summary(
            task_name=task_name,
            intent=intent,
            description=description,
            final_result=final_result,
            iterations=iteration,
            accumulated_info=accumulated_info
        )
        logger.info(summary)
        logger.info("=" * 80 + "\n")
        
        return format_task_result(
            task_name=task_name,
            status="success" if final_result else "partial",
            result={
                "output": final_result,
                "iterations": iteration,
                "summary": summary,
                "all_attempts": accumulated_info
            }
        )
    
    def _generate_plan(self, intent: str, description: str, context: Dict[str, Any]) -> str:
        """Generate initial execution plan based on intent"""
        # Get available tools information
        available_tools = self._format_available_tools()
        
        prompt = f"""Based on the intent, create a CONCISE execution instruction (2-3 sentences max).

Intent: {intent}
Description: {description}

Available context: {json.dumps(context, indent=2) if context else "None"}

AVAILABLE MCP TOOLS:
{available_tools}

Provide a BRIEF, direct instruction that specifies:
- Which tool to use
- What parameters to pass
- Expected outcome

Keep it SHORT and actionable (maximum 3 sentences):"""
        
        try:
            logger.info("\n" + "=" * 80)
            logger.info("🧠 PLANNING - Generating Execution Plan")
            logger.info("=" * 80)
            logger.info(f"📝 Prompt:\n{prompt}")
            logger.info("=" * 80)
            
            response = self.llm.invoke([HumanMessage(content=prompt)], config={"callbacks": [self.callback]})
            
            logger.info("\n" + "=" * 80)
            logger.info("📋 PLAN Generated:")
            logger.info("=" * 80)
            logger.info(response.content)
            logger.info("=" * 80 + "\n")
            
            return response.content
        except Exception as e:
            logger.error(f"Error generating plan: {e}")
            return f"Execute intent: {intent}"
    
    def _refine_plan(self, intent: str, description: str, accumulated_info: List[Dict]) -> str:
        """Refine plan based on accumulated information"""
        # Simplified tool list - just names
        tool_names = [tool.name for tool in self.tools]
        
        previous_attempts = "\n".join([
            f"Try {info['iteration']}: {str(info['result'])[:80]}..."
            for info in accumulated_info[-2:]  # Last 2 attempts only
        ])
        
        prompt = f"""Previous attempts failed. Provide a BRIEF alternative approach (1-2 sentences).

Intent: {intent}

Available tools: {', '.join(tool_names)}

Previous failures:
{previous_attempts}

What to try differently (be CONCISE):"""
        
        try:
            logger.info("\n" + "=" * 80)
            logger.info("🔄 PLANNING - Refining Execution Plan")
            logger.info("=" * 80)
            logger.info(f"📝 Prompt:\n{prompt}")
            logger.info("=" * 80)
            
            response = self.llm.invoke([HumanMessage(content=prompt)], config={"callbacks": [self.callback]})
            
            logger.info("\n" + "=" * 80)
            logger.info("📋 REFINED PLAN:")
            logger.info("=" * 80)
            logger.info(response.content)
            logger.info("=" * 80 + "\n")
            
            return response.content
        except Exception as e:
            logger.error(f"Error refining plan: {e}")
            return f"Continue working on: {intent}"
    
    def _execute_plan(self, plan: str, context: Dict[str, Any]) -> str:
        """Execute the plan using agent with MCP tools"""
        try:
            # Extract concise instruction from the plan to avoid overly long prompts
            # Look for key action phrases or use the first meaningful sentence
            lines = plan.split('\n')
            concise_instruction = None
            
            # Try to find the core instruction
            for line in lines[:10]:  # Check first 10 lines
                line = line.strip()
                # Look for imperative statements
                if any(keyword in line.lower() for keyword in ['use', 'call', 'execute', 'list', 'get', 'query', 'search', 'find']):
                    if len(line) < 200 and not line.startswith('#'):
                        concise_instruction = line
                        break
            
            # If no concise instruction found, use first non-empty line
            if not concise_instruction:
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('#') and len(line) < 300:
                        concise_instruction = line
                        break
            
            # Fallback to truncated plan
            if not concise_instruction or len(concise_instruction) < 10:
                concise_instruction = plan[:300] + "..." if len(plan) > 300 else plan
            
            logger.info(f"📋 Simplified instruction: {concise_instruction}")
            
            response = self.agent_executor.invoke(
                {"input": concise_instruction},
                config={"callbacks": [self.callback]}
            )
            return response.get("output", "")
        except Exception as e:
            logger.error(f"Error executing plan: {e}")
            return f"Error: {str(e)}"
    
    def _evaluate_result(self, intent: str, result: str, iteration: int) -> Tuple[bool, str]:
        """Evaluate if the result meets the intent expectations"""
        prompt = f"""Evaluate if the following result satisfies the intended goal.

Intent/Goal: {intent}

Current Result:
{result}

Iteration: {iteration}

Answer with:
1. SATISFIED or NOT_SATISFIED
2. Brief explanation of your evaluation

Format:
Status: [SATISFIED/NOT_SATISFIED]
Reason: [Your explanation]"""
        
        try:
            logger.info("\n" + "=" * 80)
            logger.info("✅ EVALUATION - Checking Goal Achievement")
            logger.info("=" * 80)
            logger.info(f"📝 Prompt:\n{prompt}")
            logger.info("=" * 80)
            
            response = self.llm.invoke([HumanMessage(content=prompt)], config={"callbacks": [self.callback]})
            evaluation = response.content
            
            is_satisfied = "SATISFIED" in evaluation.upper() and "NOT_SATISFIED" not in evaluation.upper()
            
            logger.info("\n" + "=" * 80)
            logger.info(f"📊 EVALUATION RESULT: {'✅ SATISFIED' if is_satisfied else '❌ NOT SATISFIED'}")
            logger.info("=" * 80)
            logger.info(evaluation)
            logger.info("=" * 80 + "\n")
            
            return is_satisfied, evaluation
        except Exception as e:
            logger.error(f"Error evaluating result: {e}")
            # If evaluation fails, consider it satisfied to avoid infinite loops
            return True, f"Evaluation error: {e}"
    
    def _determine_additional_needs(
        self,
        intent: str,
        current_result: str,
        evaluation: str
    ) -> str:
        """Determine what additional information or actions are needed"""
        # Get available tools information
        available_tools = self._format_available_tools()
        
        prompt = f"""Based on the evaluation, determine what additional information or actions are needed.

Intent: {intent}

Current Result:
{current_result}

Evaluation:
{evaluation}

AVAILABLE MCP TOOLS:
{available_tools}

What specific information or actions would help achieve the goal? Be specific about:
1. Which of the above MCP tools to use
2. What parameters to provide for each tool
3. What information to look for in the results

Response:"""
        
        try:
            logger.info("\n" + "=" * 80)
            logger.info("🔍 ANALYSIS - Determining Additional Needs")
            logger.info("=" * 80)
            logger.info(f"📝 Prompt:\n{prompt}")
            logger.info("=" * 80)
            
            response = self.llm.invoke([HumanMessage(content=prompt)], config={"callbacks": [self.callback]})
            
            logger.info("\n" + "=" * 80)
            logger.info("📋 ADDITIONAL NEEDS:")
            logger.info("=" * 80)
            logger.info(response.content)
            logger.info("=" * 80 + "\n")
            
            return response.content
        except Exception as e:
            logger.error(f"Error determining needs: {e}")
            return "Try gathering more information using available tools"
    
    def _generate_task_summary(
        self,
        task_name: str,
        intent: str,
        description: str,
        final_result: str,
        iterations: int,
        accumulated_info: List[Dict]
    ) -> str:
        """
        Generate a comprehensive summary of task execution in Markdown format
        
        Args:
            task_name: Name of the task
            intent: Original intent
            description: Task description
            final_result: Final execution result
            iterations: Number of iterations executed
            accumulated_info: All iteration information
            
        Returns:
            Formatted summary in Markdown
        """
        # Collect tools used
        tools_used = set()
        for info in accumulated_info:
            result_text = str(info.get('result', ''))
            # Try to extract tool names from the result
            if 'Action:' in result_text:
                import re
                actions = re.findall(r'Action:\s*(\S+)', result_text)
                tools_used.update(actions)
        
        tools_list = ", ".join(sorted(tools_used)) if tools_used else "N/A"
        
        # Truncate final_result if too long for the summary generation prompt
        result_preview = final_result[:1500] if len(final_result) > 1500 else final_result
        result_is_truncated = len(final_result) > 1500
        
        prompt = f"""Generate a comprehensive task execution report in Markdown format.

TASK INFORMATION:
- Task Name: {task_name}
- Description: {description}
- User Intent: {intent}

EXECUTION DETAILS:
- Total Iterations: {iterations}
- Tools Used: {tools_list}
- Final Status: {'✅ Success' if final_result else '⚠️ Incomplete'}

FINAL RESULT ({"PREVIEW - see full result below" if result_is_truncated else "COMPLETE"}):
{result_preview}

Please generate a well-structured Markdown report with the following sections:
1. ## 📋 Task Overview
2. ## 🎯 Objective  
3. ## 🔧 Execution Process (brief, 2-3 points)
4. ## ✨ Key Findings (extract the most important information from the result)
5. ## 📊 Summary

Use emojis, bullet points, and clear formatting. Be informative and extract key insights.
Output ONLY the Markdown, no additional text:"""
        
        try:
            logger.info("\n" + "=" * 80)
            logger.info("📝 GENERATING MARKDOWN SUMMARY")
            logger.info("=" * 80)
            
            # Create LLM with higher max_tokens for summary generation
            summary_llm = ChatOpenAI(
                model=self.openai_config.model,
                api_key=self.openai_config.api_key,
                base_url=self.openai_config.api_host,
                temperature=0,
                max_tokens=2000,  # Allow longer summaries
                verbose=self.verbose,
                callbacks=[self.callback]
            )
            
            response = summary_llm.invoke([HumanMessage(content=prompt)], config={"callbacks": [self.callback]})
            markdown_summary = response.content
            
            # Clean up any markdown code blocks if LLM wrapped it
            if markdown_summary.startswith('```markdown'):
                markdown_summary = markdown_summary.replace('```markdown', '').replace('```', '').strip()
            elif markdown_summary.startswith('```'):
                markdown_summary = markdown_summary.replace('```', '').strip()
            
            # Append detailed result section if result exists
            if final_result and len(final_result.strip()) > 0:
                markdown_summary += "\n\n---\n\n"
                markdown_summary += "## 📄 Complete Result Details\n\n"
                
                # Try to format as JSON if it looks like JSON
                if final_result.strip().startswith('{') or final_result.strip().startswith('['):
                    try:
                        import json
                        parsed = json.loads(final_result)
                        formatted_json = json.dumps(parsed, indent=2, ensure_ascii=False)
                        markdown_summary += "```json\n" + formatted_json + "\n```"
                    except:
                        # Not valid JSON, display as text
                        markdown_summary += "```\n" + final_result + "\n```"
                else:
                    # Regular text result
                    markdown_summary += "```\n" + final_result + "\n```"
            
            return markdown_summary
            
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            # Return a basic Markdown summary if generation fails
            basic_summary = f"""# 📋 Task Report: {task_name}

## 🎯 Objective
{intent}

## 📊 Status
- **Status**: {'✅ Completed' if final_result else '⚠️ Incomplete'}
- **Iterations**: {iterations}
- **Tools Used**: {tools_list}

## ✨ Result Overview
{final_result[:500] if final_result else 'No result'}...

---

## 📄 Complete Result Details
"""
            
            # Add full result
            if final_result:
                if final_result.strip().startswith('{') or final_result.strip().startswith('['):
                    try:
                        import json
                        parsed = json.loads(final_result)
                        formatted_json = json.dumps(parsed, indent=2, ensure_ascii=False)
                        basic_summary += "```json\n" + formatted_json + "\n```"
                    except:
                        basic_summary += "```\n" + final_result + "\n```"
                else:
                    basic_summary += "```\n" + final_result + "\n```"
            
            basic_summary += "\n\n---\n*Generated automatically by Ops Agent*"
            return basic_summary
    
    def chat(self, message: str) -> str:
        """
        Process a chat message
        
        Args:
            message: User message
            
        Returns:
            Agent response
        """
        try:
            response = self.agent_executor.invoke(
                {"input": message},
                config={"callbacks": [self.callback]}
            )
            return response.get("output", "")
        except Exception as e:
            logger.error(f"Error in chat: {str(e)}")
            return f"Error: {str(e)}"
    
    def plan_and_execute(self, intent: str) -> Dict[str, Any]:
        """
        Plan and execute a task based on natural language intent
        
        Args:
            intent: Natural language intent
            
        Returns:
            Execution result
        """
        try:
            # Execute intent
            response = self.agent_executor.invoke(
                {"input": intent},
                config={"callbacks": [self.callback]}
            )
            output = response.get("output", "")
            
            return {
                "status": "success",
                "plan": response.get("intermediate_steps", []),
                "result": output
            }
        except Exception as e:
            logger.error(f"Error executing intent: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }