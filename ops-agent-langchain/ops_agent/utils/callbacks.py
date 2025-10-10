"""
Callback utilities for Ops Agent
"""

import logging
from typing import Any, Dict, List, Optional
from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema import AgentAction, AgentFinish, LLMResult

logger = logging.getLogger(__name__)


class DetailedLoggingCallback(BaseCallbackHandler):
    """
    Detailed logging callback for LangChain agent execution
    """
    
    def __init__(self, verbose: bool = True):
        """
        Initialize callback
        
        Args:
            verbose: Enable verbose logging
        """
        super().__init__()
        self.verbose = verbose
        self.step_count = 0
    
    def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> None:
        """Run when LLM starts"""
        logger.info("=" * 80)
        logger.info("🤖 LLM CALL - REQUEST")
        logger.info("=" * 80)
        
        # Print model info
        model_name = serialized.get("name", "Unknown")
        logger.info(f"Model: {model_name}")
        
        # Print prompts
        logger.info(f"\n📝 Prompts ({len(prompts)} prompt(s)):")
        for idx, prompt in enumerate(prompts, 1):
            logger.info(f"\n--- Prompt {idx} ---")
            logger.info(prompt)
        
        logger.info("=" * 80)
    
    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Run when LLM ends"""
        logger.info("=" * 80)
        logger.info("🤖 LLM CALL - RESPONSE")
        logger.info("=" * 80)
        
        # Print generations
        if response.generations:
            logger.info(f"\n💬 Generations ({len(response.generations)} generation(s)):")
            for idx, generation_list in enumerate(response.generations, 1):
                logger.info(f"\n--- Generation {idx} ---")
                for gen_idx, generation in enumerate(generation_list):
                    if hasattr(generation, 'text'):
                        logger.info(f"\nText {gen_idx + 1}:")
                        logger.info(generation.text)
                    if hasattr(generation, 'message'):
                        logger.info(f"\nMessage {gen_idx + 1}:")
                        logger.info(generation.message.content if hasattr(generation.message, 'content') else str(generation.message))
        
        # Print token usage if available
        if hasattr(response, 'llm_output') and response.llm_output:
            token_usage = response.llm_output.get('token_usage', {})
            if token_usage:
                logger.info(f"\n📊 Token Usage:")
                logger.info(f"  - Prompt tokens: {token_usage.get('prompt_tokens', 'N/A')}")
                logger.info(f"  - Completion tokens: {token_usage.get('completion_tokens', 'N/A')}")
                logger.info(f"  - Total tokens: {token_usage.get('total_tokens', 'N/A')}")
        
        logger.info("=" * 80)
    
    def on_llm_error(
        self, error: Exception, **kwargs: Any
    ) -> None:
        """Run when LLM errors"""
        logger.error(f"LLM error: {str(error)}")
    
    def on_chain_start(
        self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs: Any
    ) -> None:
        """Run when chain starts"""
        if self.verbose:
            logger.debug(f"Chain started with inputs: {inputs}")
    
    def on_chain_end(self, outputs: Dict[str, Any], **kwargs: Any) -> None:
        """Run when chain ends"""
        if self.verbose:
            logger.debug(f"Chain completed with outputs")
    
    def on_chain_error(
        self, error: Exception, **kwargs: Any
    ) -> None:
        """Run when chain errors"""
        logger.error(f"Chain error: {str(error)}")
    
    def on_tool_start(
        self, serialized: Dict[str, Any], input_str: str, **kwargs: Any
    ) -> None:
        """Run when tool starts"""
        self.step_count += 1
        tool_name = serialized.get("name", "Unknown")
        logger.info(f"🔧 Step {self.step_count}: Calling tool '{tool_name}'")
        logger.info(f"   Input: {input_str[:200]}...")
    
    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        """Run when tool ends"""
        logger.info(f"✓ Tool completed")
        if self.verbose:
            logger.info(f"   Output: {output[:200]}...")
    
    def on_tool_error(
        self, error: Exception, **kwargs: Any
    ) -> None:
        """Run when tool errors"""
        logger.error(f"✗ Tool error: {str(error)}")
    
    def on_agent_action(self, action: AgentAction, **kwargs: Any) -> None:
        """Run on agent action"""
        if self.verbose:
            logger.debug(f"Agent action: {action.tool}")
    
    def on_agent_finish(self, finish: AgentFinish, **kwargs: Any) -> None:
        """Run on agent finish"""
        logger.info(f"✅ Agent finished with output")
        if self.verbose:
            output = finish.return_values.get("output", "")
            logger.debug(f"   Final output: {output[:200]}...")
        self.step_count = 0  # Reset counter
    
    def on_text(self, text: str, **kwargs: Any) -> None:
        """Run on arbitrary text"""
        if self.verbose and text.strip():
            logger.debug(f"Text: {text[:100]}...")

