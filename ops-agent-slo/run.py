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
from ops_agent.modules import UpstreamQueryModule, ErrorLogQueryModule, LLMChatModule, XieZuoModule
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
    
    # 将 config_loader 放入上下文，供模块使用（如 LLM 模块读取配置）
    orchestrator.set_context('config_loader', config_loader)
    
    # 注册模块
    orchestrator.register_module(UpstreamQueryModule())
    orchestrator.register_module(ErrorLogQueryModule())
    orchestrator.register_module(LLMChatModule())
    orchestrator.register_module(XieZuoModule())
    
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
    
    # 示例 3: 使用 LLM 模块分析前面模块的结果
    print("\n" + "="*80)
    print("调用 LLM 模块进行分析...")
    print("="*80)
    
    # 准备分析数据
    analysis_data = {
        "service_name": service_name,
        "upstream_status": upstream_result.status.value,
        "upstream_summary": upstream_result.data.get('upstream_info', {}).get('summary', {}) if upstream_result.data else {},
        "error_log_status": error_log_result.status.value,
        "error_log_summary": error_log_result.data.get('logs', {}).get('summary', {}) if error_log_result.data else {}
    }
    
    # 构建 LLM 输入
    llm_input = f"""请分析服务 {service_name} 的监控情况：

1. Upstream 查询状态: {analysis_data['upstream_status']}
   - 找到的 upstream 数量: {analysis_data['upstream_summary'].get('total_upstreams', 0)}

2. 错误日志查询状态: {analysis_data['error_log_status']}
   - 错误日志总数: {analysis_data['error_log_summary'].get('total_errors', 0)}
   - 错误类型分布: {analysis_data['error_log_summary'].get('error_types', {})}

请给出简要的分析和建议。"""
    
    llm_result = orchestrator.execute_module(
        "llm_chat",
        params={
            "input": llm_input,
            "prompt": "你是一个专业的运维专家，擅长分析服务监控数据和故障排查。请用简洁明了的语言回答问题。"
        }
    )
    
    if llm_result.status.value == "success":
        print(f"\n✅ LLM 分析结果:")
        print("-" * 80)
        print(llm_result.data.get('output', ''))
        print("-" * 80)
        if llm_result.data.get('usage'):
            usage = llm_result.data.get('usage', {})
            print(f"\nToken 使用情况: {usage.get('total_tokens', 0)} tokens")
    else:
        print(f"\n❌ LLM 分析失败: {llm_result.error}")
        print("提示: 请确保已配置 LLM token 和 URL（在 config.yaml 或环境变量中）")
    
    # ============================================
    # 代码编写区域结束
    # ============================================


if __name__ == "__main__":
    main()

