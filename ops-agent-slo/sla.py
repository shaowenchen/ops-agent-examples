#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
编排逻辑入口 - Ops Agent SLO

此文件包含真实的业务编排逻辑，定义模块的执行顺序和参数传递。
- main.py 和 server.py 都是服务入口，最终都会调用此文件的 main() 函数
- 在此文件中直接编写 Python 代码来组合和执行模块
- 可以传递参数、复用结果、实现复杂的业务流程
"""

import os
import sys
from typing import Dict, Any, Optional
from datetime import datetime

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ops_agent.config import ConfigLoader
from ops_agent.core import Orchestrator
from ops_agent.modules import register_all_modules
from ops_agent.utils.logging import setup_logging, get_logger

logger = get_logger(__name__)


def main(data: Optional[str] = None, key: Optional[str] = None) -> Dict[str, Any]:
    """
    编排逻辑主函数
    
    此函数包含真实的业务编排逻辑，定义：
    1. 模块的初始化顺序
    2. 模块的执行顺序和参数传递
    3. 结果的处理和复用
    4. 错误处理和流程控制
    
    此函数会被 main.py 和 server.py 调用
    
    Args:
        data: 可选，要分析的数据内容（如果提供，会执行动态分析流程）
        key: 可选，标识键，用于区分不同的分析类型
    
    Returns:
        包含执行结果的字典
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
    
    # 如果有传入的 data 和 key，放入上下文
    if data:
        orchestrator.set_context('input_data', data)
    if key is not None:  # 允许空字符串
        orchestrator.set_context('input_key', key)
    
    # 自动注册所有模块
    register_all_modules(orchestrator)
    
    # 执行分析流程
    results = {}
    
    # 如果提供了 data，执行动态分析流程
    if data:
        logger.info(f"Executing dynamic analysis flow: key={key or '(empty)'}, data_length={len(data)}")
        
        # 根据 key 决定分析流程（key 可以为空字符串）
        if key and key.startswith('service_'):
            # 如果是服务相关的 key，提取服务名称
            service_name = key.replace('service_', '') if key.startswith('service_') else data.split()[0] if data else 'unknown'
            
            # 1. 查询 upstream 信息
            upstream_result = orchestrator.execute_module(
                "upstream_query",
                params={
                    "service_name": service_name,
                    "mcp_server": "default",
                    "tool_name": "get-events-from-ops",
                    "additional_args": {
                        "page_size": "50"
                    }
                }
            )
            results['upstream'] = upstream_result.to_dict()
            
            # 2. 查询错误日志
            error_log_result = orchestrator.execute_module(
                "error_log_query",
                params={
                    "service_name": service_name,
                    "index": "logs-*",
                    "time_range": "1h",
                    "mcp_server": "default",
                    "tool_name": "search-logs-from-elasticsearch"
                }
            )
            results['error_log'] = error_log_result.to_dict()
            
            # 3. LLM 分析（结合接收到的 data 和查询结果）
            analysis_prompt = f"""{data}

请结合以下监控数据进行分析：
- Upstream 状态: {upstream_result.status.value}
- 错误日志状态: {error_log_result.status.value}
- 错误日志总数: {error_log_result.data.get('logs', {}).get('summary', {}).get('total_errors', 0) if error_log_result.data else 0}"""
            
            llm_result = orchestrator.execute_module(
                "llm_chat",
                params={
                    "input": analysis_prompt,
                    "prompt": "你是一个专业的运维专家。请用以下格式简洁回答：\n1. 问题：一句话说明问题\n2. 分析：简要分析原因\n3. 建议：给出处理建议"
                }
            )
            results['llm_analysis'] = llm_result.to_dict()
            
        else:
            # 默认流程：直接使用 LLM 分析接收到的 data（key 为空或非 service_ 开头）
            # 针对告警数据的特殊处理
            prompt = "你是一个专业的运维专家。请用以下格式简洁回答：\n1. 问题：一句话说明问题\n2. 分析：简要分析原因\n3. 建议：给出处理建议"
            
            llm_result = orchestrator.execute_module(
                "llm_chat",
                params={
                    "input": data,
                    "prompt": prompt
                }
            )
            results['llm_analysis'] = llm_result.to_dict()
        
        # LLM 分析完成后，发送通知
        if results.get('llm_analysis'):
            llm_result_data = results['llm_analysis']
            if llm_result_data.get('status') == 'success' and llm_result_data.get('data'):
                llm_output = llm_result_data['data'].get('output', '')
                
                # 构建通知内容（markdown 格式）
                notification_content = f"""## 分析结果

{llm_output}

---
*分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"""
                
                # 发送通知（传递 key 和 content）
                xiezuo_result = orchestrator.execute_module(
                    "xiezuo",
                    params={
                        "key": key or "default",
                        "content": notification_content
                    }
                )
                results['xiezuo'] = xiezuo_result.to_dict()
        
        return results
    
    else:
        # 如果没有提供 data，执行默认的示例流程
        # ============================================
        # 在这里编写你的默认编排逻辑
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
                "prompt": "你是一个专业的运维专家。请用以下格式简洁回答：\n1. 问题：一句话说明问题\n2. 分析：简要分析原因\n3. 建议：给出处理建议"
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
        
        return {}


if __name__ == "__main__":
    main()

