"""
LLM Summarizer for summarizing MCP query results
"""

import json
from typing import Dict, Any, List

from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

from ..config import ConfigLoader
from ..utils.logging import get_logger

logger = get_logger(__name__)


class LLMSummarizer:
    """LLM-based summarizer for MCP query results"""
    
    def __init__(self, config_loader: ConfigLoader):
        """
        Initialize LLM Summarizer
        
        Args:
            config_loader: Configuration loader instance
        """
        self.config_loader = config_loader
        openai_config = config_loader.openai_config
        
        # Initialize LLM
        llm_kwargs = {
            "model": openai_config.model,
            "api_key": openai_config.api_key,
            "base_url": openai_config.api_host,
            "temperature": 0.3,  # Lower temperature for more focused summaries
        }
        
        if openai_config.max_tokens:
            llm_kwargs["max_tokens"] = openai_config.max_tokens
        
        self.llm = ChatOpenAI(**llm_kwargs)
        
        logger.info(f"Initialized LLM Summarizer")
        logger.info(f"Model: {openai_config.model}")
        logger.info(f"API Host: {openai_config.api_host}")
    
    def summarize(self, query_results: List[Dict[str, Any]], summary_prompt: str = None) -> str:
        """
        Generate a summary of MCP query results using LLM
        
        Args:
            query_results: List of MCP query results
            summary_prompt: Optional custom prompt for summarization
        
        Returns:
            Summary text
        """
        try:
            logger.info("Generating summary using LLM...")
            
            # Format query results for the prompt
            results_text = self._format_query_results(query_results)
            
            # Create prompt
            if summary_prompt is None:
                summary_prompt = """请对以下MCP查询结果进行总结和分析。总结应该包括：
1. 查询的整体情况（成功/失败数量）
2. 每个查询的关键发现
3. 数据中的关键指标和趋势
4. 任何需要注意的问题或异常
5. 总体结论和建议

请用中文回答，结构清晰，重点突出。"""
            
            system_message = SystemMessage(content="你是一个专业的数据分析助手，擅长总结和分析技术数据。")
            human_message = HumanMessage(content=f"{summary_prompt}\n\n查询结果：\n{results_text}")
            
            logger.debug("Sending request to LLM...")
            response = self.llm.invoke([system_message, human_message])
            
            summary = response.content
            logger.info("Summary generated successfully")
            logger.debug(f"Summary length: {len(summary)} characters")
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            return f"生成总结时出错: {str(e)}"
    
    def _format_query_results(self, query_results: List[Dict[str, Any]]) -> str:
        """
        Format query results into a readable text format
        
        Args:
            query_results: List of query results
        
        Returns:
            Formatted text
        """
        formatted_parts = []
        
        for result in query_results:
            query_index = result.get('query_index', '?')
            tool_name = result.get('tool_name', 'unknown')
            desc = result.get('desc', '')
            success = result.get('success', False)
            
            formatted_parts.append(f"\n{'='*80}")
            formatted_parts.append(f"查询 {query_index}: {tool_name}")
            if desc:
                formatted_parts.append(f"描述: {desc}")
            formatted_parts.append(f"状态: {'成功' if success else '失败'}")
            formatted_parts.append(f"{'='*80}")
            
            if success:
                result_data = result.get('result', {})
                args = result.get('args', {})
                
                if args:
                    formatted_parts.append(f"查询参数: {json.dumps(args, ensure_ascii=False, indent=2)}")
                
                # Format result content
                if isinstance(result_data, dict):
                    if 'content' in result_data:
                        # Handle content array
                        content = result_data['content']
                        if isinstance(content, list):
                            for idx, item in enumerate(content):
                                if isinstance(item, str):
                                    formatted_parts.append(f"结果 {idx + 1}: {item[:1000]}...")  # Limit length
                                else:
                                    formatted_parts.append(f"结果 {idx + 1}: {json.dumps(item, ensure_ascii=False, indent=2)[:1000]}...")
                        else:
                            formatted_parts.append(f"结果: {str(content)[:1000]}...")
                    else:
                        formatted_parts.append(f"结果: {json.dumps(result_data, ensure_ascii=False, indent=2)[:2000]}...")
                else:
                    formatted_parts.append(f"结果: {str(result_data)[:1000]}...")
            else:
                error = result.get('error', 'Unknown error')
                formatted_parts.append(f"错误: {error}")
        
        return "\n".join(formatted_parts)

