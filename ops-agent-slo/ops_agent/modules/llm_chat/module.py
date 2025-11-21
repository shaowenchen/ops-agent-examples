"""
LLM Chat Module

This module interacts with LLM models (e.g., WPS AI Gateway, OpenAI, etc.)
"""

import json
import requests
from typing import Dict, Any, List, Tuple, Optional
from ...core.base_module import BaseModule, ModuleResult, ModuleStatus
from ...utils.logging import get_logger

logger = get_logger(__name__)


class LLMChatModule(BaseModule):
    """
    Module for interacting with LLM models

    This module can call LLM APIs to get AI responses.
    Supports WPS AI Gateway and other LLM providers.
    """

    def __init__(self, mcp_tool=None, context: Dict[str, Any] = None):
        """
        Initialize LLM Chat Module

        Args:
            mcp_tool: MCP tool instance (not used for LLM)
            context: Shared context
        """
        super().__init__("llm_chat", mcp_tool, context)

    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate module parameters

        Args:
            params: Parameters to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Input is required
        if "input" not in params and "messages" not in params:
            return False, "Either 'input' or 'messages' parameter is required"

        return True, None

    def execute(self, params: Dict[str, Any]) -> ModuleResult:
        """
        Execute LLM chat

        Args:
            params: Module parameters:
                - input: User input text (required if messages not provided)
                - messages: List of messages (optional, alternative to input)
                - prompt: System prompt (optional)
                - history: Chat history (optional, can use context from other modules)
                - token: API token (optional, can use config)
                - url: LLM API URL (optional, default: WPS AI Gateway)
                - model: Model name (optional, default: "gpt-4o")
                - provider: Provider name (optional, default: "azure")
                - temperature: Temperature (optional, default: 0)
                - use_context: Whether to use history from context (optional, default: False)
                - context_key: Context key to get history from (optional, default: "llm_history")

        Returns:
            ModuleResult with LLM response
        """
        try:
            # Get parameters
            user_input = params.get("input")
            messages = params.get("messages")
            prompt = params.get("prompt", "")
            history = params.get("history", [])
            token = params.get("token")
            url = params.get("url")
            model = params.get("model", "gpt-4o")
            provider = params.get("provider", "azure")
            temperature = params.get("temperature", 0)
            use_context = params.get("use_context", False)
            context_key = params.get("context_key", "llm_history")

            # Get token from environment variable, context, or config (priority order)
            if not token:
                import os

                token = os.environ.get("LLM_TOKEN")
            if not token:
                token = self.get_context_value("llm_token")
            if not token:
                config_loader = self.get_context_value("config_loader")
                if config_loader:
                    try:
                        llm_config = config_loader._config.get("llm", {})
                        token = llm_config.get("token") or llm_config.get("api_key")
                    except:
                        pass

            # Get URL from environment variable, params, or config (priority order)
            if not url:
                import os

                url = os.environ.get("LLM_URL")
            if not url:
                config_loader = self.get_context_value("config_loader")
                if config_loader:
                    try:
                        llm_config = config_loader._config.get("llm", {})
                        url = llm_config.get("url")
                    except:
                        pass
            # Default URL if still not set
            if not url:
                raise ValueError("LLM URL is required. Provide it in params or config.")

            if not token:
                return ModuleResult(
                    module_name=self.name,
                    status=ModuleStatus.FAILED,
                    error="LLM token is required. Provide it in params or config.",
                )

            # Get history from context if requested
            if use_context:
                context_history = self.get_context_value(context_key, [])
                if context_history:
                    history = context_history

            # Build messages
            if messages:
                # Use provided messages directly
                message_list = messages
            else:
                # Build messages from history and input
                message_list = []

                # Add system prompt if provided
                if prompt:
                    message_list.append({"role": "system", "content": prompt})

                # Add history messages
                for msg in history:
                    if isinstance(msg, dict):
                        message_list.append(
                            {
                                "role": msg.get("role", "user"),
                                "content": msg.get("content", ""),
                            }
                        )
                    elif isinstance(msg, str):
                        # Simple string format, assume user message
                        message_list.append({"role": "user", "content": msg})

                # Add current user input
                if user_input:
                    message_list.append({"role": "user", "content": user_input})

            logger.info(f"Calling LLM API: {url}")
            logger.debug(f"Model: {model}, Provider: {provider}")
            logger.debug(f"Messages count: {len(message_list)}")

            # Build request body
            request_body = {
                "stream": False,
                "provider": provider,
                "messages": message_list,
                "base_llm_arguments": {"temperature": temperature},
                "extended_llm_arguments": {f"azure_{model}": {}},
                "context": prompt,
                "model": model,
                "examples": [],
                "version": "2024-05-13",
            }

            # Prepare headers
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }

            # Get custom headers with priority: params > environment variable > config
            custom_headers = {}

            # Step 1: Try to get from config first (as default/base)
            config_loader = self.get_context_value("config_loader")
            if config_loader:
                try:
                    llm_config = config_loader._config.get("llm", {})
                    # Support both headers_json (JSON string) and headers (dict) for backward compatibility
                    headers_json_str = llm_config.get("headers_json")
                    if headers_json_str:
                        try:
                            config_headers = json.loads(headers_json_str)
                            custom_headers = config_headers.copy()
                            logger.debug(
                                "Loaded headers from config file (headers_json)"
                            )
                        except json.JSONDecodeError as e:
                            logger.warning(
                                f"Failed to parse headers_json in config: {e}"
                            )
                    # Fallback to headers dict format (for backward compatibility)
                    elif llm_config.get("headers"):
                        config_headers = llm_config.get("headers", {})
                        if isinstance(config_headers, dict):
                            custom_headers = config_headers.copy()
                            logger.debug(
                                "Loaded headers from config file (headers dict)"
                            )
                except Exception as e:
                    logger.debug(f"Error loading headers from config: {e}")

            # Step 2: Environment variable overrides config
            import os

            llm_headers_json = os.environ.get("LLM_HEADERS_JSON")
            if llm_headers_json:
                try:
                    env_headers = json.loads(llm_headers_json)
                    custom_headers.update(env_headers)  # Override config with env vars
                    logger.debug(
                        "Loaded headers from LLM_HEADERS_JSON environment variable (overrides config)"
                    )
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse LLM_HEADERS_JSON: {e}")

            # Step 3: Params override everything
            params_headers = params.get("headers", {})
            if params_headers:
                custom_headers.update(params_headers)  # Override with params
                logger.debug("Using headers from params (overrides env and config)")

            # Update headers with custom headers
            if custom_headers:
                headers.update(custom_headers)

            # Make HTTP request
            try:
                response = requests.post(
                    url,
                    json=request_body,
                    headers=headers,
                    timeout=params.get("timeout", 60),
                )
                response.raise_for_status()

                result_data = response.json()

                # Parse response
                choices = result_data.get("choices", [])
                if not choices:
                    error_msg = result_data.get("message", "No choices in response")
                    logger.error(f"LLM API error: {error_msg}")
                    return ModuleResult(
                        module_name=self.name,
                        status=ModuleStatus.FAILED,
                        error=f"LLM API returned no choices: {error_msg}",
                        data={"raw_response": result_data},
                    )

                # Get response text
                output = choices[0].get("text", "")

                # Extract usage information
                usage = result_data.get("usage", {})

                # Update history in context if requested
                if use_context:
                    # Add current interaction to history
                    new_history = list(history) if history else []
                    new_history.append({"role": "user", "content": user_input or ""})
                    new_history.append({"role": "assistant", "content": output})
                    self.set_context_value(context_key, new_history)

                return ModuleResult(
                    module_name=self.name,
                    status=ModuleStatus.SUCCESS,
                    data={
                        "output": output,
                        "model": model,
                        "provider": provider,
                        "usage": usage,
                        "raw_response": result_data,
                    },
                    metadata={"url": url, "message_count": len(message_list)},
                )

            except requests.exceptions.RequestException as e:
                logger.error(f"LLM API request failed: {e}")
                return ModuleResult(
                    module_name=self.name,
                    status=ModuleStatus.FAILED,
                    error=f"LLM API request failed: {str(e)}",
                )

        except Exception as e:
            logger.error(f"LLM chat failed: {e}")
            logger.exception("Full exception traceback:")
            return ModuleResult(
                module_name=self.name, status=ModuleStatus.FAILED, error=str(e)
            )
