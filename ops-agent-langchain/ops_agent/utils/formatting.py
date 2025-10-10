"""
Formatting utilities for Ops Agent
"""

from typing import Dict, Any
from datetime import datetime


def format_task_result(task_name: str, status: str, result: Any) -> Dict[str, Any]:
    """
    Format task execution result
    
    Args:
        task_name: Name of the task
        status: Task status (success, failed, skipped)
        result: Task result or error message
        
    Returns:
        Formatted result dictionary
    """
    return {
        "task_name": task_name,
        "status": status,
        "result": result,
        "timestamp": datetime.now().isoformat()
    }


def format_prompt_with_context(prompt: str, context: Dict[str, Any] = None) -> str:
    """
    Format prompt with context variables
    
    Args:
        prompt: Prompt template string
        context: Context dictionary for variable substitution
        
    Returns:
        Formatted prompt string
    """
    if not context:
        return prompt
    
    # Simple variable substitution
    formatted_prompt = prompt
    for key, value in context.items():
        placeholder = f"{{{key}}}"
        if placeholder in formatted_prompt:
            formatted_prompt = formatted_prompt.replace(placeholder, str(value))
    
    return formatted_prompt

