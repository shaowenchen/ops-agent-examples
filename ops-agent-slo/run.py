#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main execution script for Ops Agent SLO

Edit this file to directly compose and execute modules.
You can write Python code here to combine modules, pass parameters, and reuse results.
"""

import os
import sys
from typing import Dict, Any

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ops_agent.config import ConfigLoader
from ops_agent.core import Orchestrator
from ops_agent.modules import UpstreamQueryModule, ErrorLogQueryModule
from ops_agent.utils.logging import setup_logging, get_logger

logger = get_logger(__name__)


def main():
    """
    在这里编写你的代码来组合和执行模块
    
    示例：
    1. 初始化配置和编排器
    2. 注册需要的模块
    3. 直接调用模块并传递参数
    4. 使用模块返回的结果进行后续操作
    """
    # 设置日志
    setup_logging("INFO")
    
    # 初始化配置
    config_loader = ConfigLoader()
    config_loader.load_config()
    
    # 初始化编排器
    orchestrator = Orchestrator(config_loader)
    
    # 注册模块
    orchestrator.register_module(UpstreamQueryModule())
    orchestrator.register_module(ErrorLogQueryModule())
    
    # ============================================
    # 在这里编写你的代码来组合模块
    # ============================================
    
    # 示例 1: 查询 qingqiu 服务的 upstream 信息
    upstream_result = orchestrator.execute_module(
        "upstream_query",
        params={
            "service_name": "qingqiu",
            "mcp_server": "default",
            "tool_name": "get-events-from-ops",
            "additional_args": {
                "page_size": "50"
            }
        }
    )
    
    print(f"Upstream query result: {upstream_result.status.value}")
    if upstream_result.data:
        print(f"Service: {upstream_result.data.get('service_name')}")
        print(f"Upstreams found: {upstream_result.data.get('upstream_info', {}).get('summary', {}).get('total_upstreams', 0)}")
    
    # 示例 2: 使用上一个模块的结果，查询异常日志
    # 从上下文获取服务名称（upstream_query 模块会自动设置）
    service_name = orchestrator.get_context('last_queried_service', 'qingqiu')
    
    error_log_result = orchestrator.execute_module(
        "error_log_query",
        params={
            "service_name": service_name,  # 可以复用上一个模块的结果
            "index": "logs-*",
            "time_range": "1h",
            "mcp_server": "default",
            "tool_name": "search-logs-from-elasticsearch"
        }
    )
    
    print(f"\nError log query result: {error_log_result.status.value}")
    if error_log_result.data:
        log_summary = error_log_result.data.get('logs', {}).get('summary', {})
        print(f"Total errors: {log_summary.get('total_errors', 0)}")
    
    # 示例 3: 可以添加更多逻辑
    # if upstream_result.status.value == "success":
    #     # 根据 upstream 结果决定下一步操作
    #     pass
    
    # 示例 4: 循环处理多个服务
    # services = ["qingqiu", "service2", "service3"]
    # for service in services:
    #     result = orchestrator.execute_module(
    #         "upstream_query",
    #         params={"service_name": service}
    #     )
    #     # 处理结果...
    
    # ============================================
    # 代码编写区域结束
    # ============================================


if __name__ == "__main__":
    main()

