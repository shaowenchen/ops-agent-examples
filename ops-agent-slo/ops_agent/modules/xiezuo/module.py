"""
Xiezuo Notification Module

This module sends notifications via Xiezuo (协作) webhook
"""

import requests
import os
from typing import Dict, Any, Tuple, Optional
from ...core.base_module import BaseModule, ModuleResult, ModuleStatus
from ...utils.logging import get_logger

logger = get_logger(__name__)


class XieZuoModule(BaseModule):
    """
    Module for sending notifications via Xiezuo webhook
    
    Simple notification module that sends markdown formatted messages.
    Requires only key and content parameters.
    """
    
    def __init__(self, mcp_tool=None, context: Dict[str, Any] = None):
        """
        Initialize Xiezuo Notification Module
        
        Args:
            mcp_tool: MCP tool instance (not used)
            context: Shared context (not used)
        """
        super().__init__("xiezuo", mcp_tool, context)
    
    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate module parameters
        
        Args:
            params: Parameters to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if 'key' not in params:
            return False, "key parameter is required"
        
        if 'content' not in params:
            return False, "content parameter is required"
        
        return True, None
    
    def execute(self, params: Dict[str, Any]) -> ModuleResult:
        """
        Execute Xiezuo notification
        
        Args:
            params: Module parameters:
                - key: Key for webhook URL (required)
                - content: Message content in markdown format (required)
        
        Returns:
            ModuleResult with notification status
        """
        try:
            # Get parameters
            key = params.get('key')
            content = params.get('content')
            
            if not key:
                return ModuleResult(
                    module_name=self.name,
                    status=ModuleStatus.FAILED,
                    error="key parameter is required"
                )
            
            if not content:
                return ModuleResult(
                    module_name=self.name,
                    status=ModuleStatus.FAILED,
                    error="content parameter is required"
                )
            
            # Get webhook URL template from config or environment variable
            # Priority: XIEZUO_URL > EVENT_WOA > config
            webhook_url_template = None
            
            # Try XIEZUO_URL environment variable first
            xiezuo_url = os.environ.get('XIEZUO_URL')
            if xiezuo_url:
                webhook_url_template = xiezuo_url
                logger.debug("Using XIEZUO_URL environment variable")
            
            # Try EVENT_WOA environment variable (for backward compatibility)
            if not webhook_url_template:
                event_woa = os.environ.get('EVENT_WOA')
                if event_woa:
                    webhook_url_template = event_woa
                    logger.debug("Using EVENT_WOA environment variable")
            
            # Try config
            if not webhook_url_template:
                config_loader = self.get_context_value('config_loader')
                if config_loader:
                    try:
                        xiezuo_config = config_loader._config.get('xiezuo', {})
                        webhook_url_template = xiezuo_config.get('url')
                        if webhook_url_template:
                            logger.debug("Using xiezuo.url from config")
                    except:
                        pass
            
            if not webhook_url_template:
                return ModuleResult(
                    module_name=self.name,
                    status=ModuleStatus.FAILED,
                    error="Webhook URL template is required. Set XIEZUO_URL or EVENT_WOA environment variable, or xiezuo.url in config."
                )
            
            # Replace key in URL template
            # Support multiple patterns:
            # 1. ?key=xxx or &key=xxx
            # 2. ?key= or &key= (append key)
            # 3. {key} placeholder
            webhook_url = webhook_url_template
            
            # Replace ?key=xxx or &key=xxx
            if 'key=xxx' in webhook_url:
                webhook_url = webhook_url.replace('key=xxx', f'key={key}')
            # Replace {key} placeholder
            elif '{key}' in webhook_url:
                webhook_url = webhook_url.replace('{key}', key)
            # Append key if URL ends with ?key= or &key=
            elif webhook_url.endswith('?key=') or webhook_url.endswith('&key='):
                webhook_url = webhook_url + key
            # If URL doesn't have key parameter, append it
            elif '?key=' not in webhook_url and '&key=' not in webhook_url:
                separator = '&' if '?' in webhook_url else '?'
                webhook_url = f"{webhook_url}{separator}key={key}"
            
            logger.info(f"Sending notification to Xiezuo webhook (key: {key})")
            logger.debug(f"Webhook URL: {webhook_url[:80]}...")
            logger.debug(f"Content length: {len(content)}")
            
            # 打印通知内容
            logger.info("Xiezuo notification content:")
            logger.info("-" * 80)
            logger.info(content)
            logger.info("-" * 80)
            
            # Build request body (markdown format)
            request_body = {
                "msgtype": "markdown",
                "markdown": {
                    "text": content
                }
            }
            
            # Make HTTP POST request
            try:
                response = requests.post(
                    webhook_url,
                    json=request_body,
                    headers={
                        "Content-Type": "application/json"
                    },
                    timeout=params.get('timeout', 10)
                )
                response.raise_for_status()
                
                result_data = response.json()
                
                # Check response (Xiezuo typically returns errcode and errmsg)
                errcode = result_data.get('errcode', 0)
                errmsg = result_data.get('errmsg', '')
                
                if errcode == 0:
                    logger.info("Notification sent successfully")
                    return ModuleResult(
                        module_name=self.name,
                        status=ModuleStatus.SUCCESS,
                        data={
                            "message": "Notification sent successfully",
                            "response": result_data
                        }
                    )
                else:
                    error_msg = f"Xiezuo API returned error: {errmsg} (errcode: {errcode})"
                    logger.error(error_msg)
                    return ModuleResult(
                        module_name=self.name,
                        status=ModuleStatus.FAILED,
                        error=error_msg,
                        data={"response": result_data}
                    )
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Xiezuo webhook request failed: {e}")
                return ModuleResult(
                    module_name=self.name,
                    status=ModuleStatus.FAILED,
                    error=f"Xiezuo webhook request failed: {str(e)}"
                )
            
        except Exception as e:
            logger.error(f"Xiezuo notification failed: {e}")
            logger.exception("Full exception traceback:")
            return ModuleResult(
                module_name=self.name,
                status=ModuleStatus.FAILED,
                error=str(e)
            )
