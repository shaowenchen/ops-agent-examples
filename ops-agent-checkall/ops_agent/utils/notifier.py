"""
Notification utility for sending summary notifications
"""

import os
import requests
from typing import Dict, Any, Optional

from ..utils.logging import get_logger

logger = get_logger(__name__)


class Notifier:
    """Notification sender for summary results"""
    
    def __init__(self, notify_url: Optional[str] = None):
        """
        Initialize Notifier
        
        Args:
            notify_url: Notification URL (if None, will try to get from environment)
        """
        self.notify_url = notify_url or os.environ.get('NOTIFY_URL') or os.environ.get('NOTIFICATION_URL')
        self.logger = logger
    
    def send_notification(self, summary: str) -> Dict[str, Any]:
        """
        发送告警总结到群聊

        Args:
            summary: 告警总结内容

        Returns:
            发送结果字典
        """
        if not self.notify_url:
            self.logger.warning("通知URL未配置，跳过发送通知")
            return {
                "success": False,
                "error": "通知URL未配置（请设置 NOTIFY_URL 环境变量）"
            }
        
        self.logger.info("=== 开始发送告警通知 ===")

        try:
            # 格式化消息内容
            markdown_text = f"{summary}\n\n>"

            # 构建请求数据
            payload = {"msgtype": "markdown", "markdown": {"text": markdown_text}}

            self.logger.info(f"准备发送到: {self.notify_url}")
            self.logger.info(f"消息内容: {markdown_text}")

            # 发送HTTP请求
            response = requests.post(
                self.notify_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30,
            )

            self.logger.info(f"HTTP响应状态码: {response.status_code}")
            self.logger.info(f"HTTP响应内容: {response.text}")

            if response.status_code == 200:
                self.logger.info("告警通知发送成功")
                return {"success": True, "response": response.text}
            else:
                self.logger.error(f"告警通知发送失败，状态码: {response.status_code}")
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                }

        except requests.exceptions.Timeout:
            self.logger.error("发送告警通知超时")
            return {"success": False, "error": "请求超时"}
        except requests.exceptions.ConnectionError:
            self.logger.error("发送告警通知连接错误")
            return {"success": False, "error": "连接错误"}
        except Exception as e:
            self.logger.error(f"发送告警通知异常: {str(e)}")
            return {"success": False, "error": f"发送异常: {str(e)}"}

