#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTTP Server for triggering Ops Agent SLO workflows
"""
import os
import sys
import json
from typing import Optional, Dict, Any
from flask import Flask, request, jsonify
from datetime import datetime

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ops_agent.config import ConfigLoader
from ops_agent.core import Orchestrator
from ops_agent.modules import UpstreamQueryModule, ErrorLogQueryModule, LLMChatModule, XieZuoModule
from ops_agent.utils.logging import setup_logging, get_logger

app = Flask(__name__)
logger = get_logger(__name__)


@app.route('/health', methods=['GET'])
def health():
    """健康检查端点"""
    return jsonify({
        "status": "healthy",
        "service": "ops-agent-slo",
        "timestamp": datetime.now().isoformat()
    })


@app.route('/trigger', methods=['GET', 'POST'])
def trigger_workflow():
    """
    触发执行分析流程
    
    POST 请求体格式:
    {
        "data": "分析内容或数据",
        "key": "标识键，用于区分不同的分析类型",
        "verbose": false
    }
    """
    try:
        # 支持 GET 和 POST 请求
        if request.method == 'GET':
            verbose = request.args.get('verbose', 'false').lower() == 'true'
            input_data = None
            input_key = None
        else:
            request_data = request.get_json() or {}
            verbose = request_data.get('verbose', False)
            input_data = request_data.get('data')
            input_key = request_data.get('key')
        
        # 设置日志
        log_level = "DEBUG" if verbose else "INFO"
        setup_logging(log_level)
        
        # 初始化配置和编排器
        config_loader = ConfigLoader()
        config_loader.load_config()
        
        orchestrator = Orchestrator(config_loader)
        orchestrator.set_context('config_loader', config_loader)
        
        # 注册模块
        orchestrator.register_module(UpstreamQueryModule())
        orchestrator.register_module(ErrorLogQueryModule())
        orchestrator.register_module(LLMChatModule())
        orchestrator.register_module(XieZuoModule())
        
        # 如果有 POST 请求的 data 和 key，放入上下文
        if input_data:
            orchestrator.set_context('input_data', input_data)
        if input_key is not None:  # 允许空字符串
            orchestrator.set_context('input_key', input_key)
        
        # 执行分析流程
        results = {}
        
        # 如果提供了 data（key 可以为空字符串），执行分析流程
        if input_data:
            logger.info(f"Received analyze request: key={input_key or '(empty)'}, data_length={len(input_data)}")
            
            # 根据 key 决定分析流程（key 可以为空字符串）
            if input_key and input_key.startswith('service_'):
                # 如果是服务相关的 key，提取服务名称
                service_name = input_key.replace('service_', '') if input_key.startswith('service_') else input_data.split()[0] if input_data else 'unknown'
                
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
                analysis_prompt = f"""{input_data}

请结合以下监控数据进行分析：
- Upstream 状态: {upstream_result.status.value}
- 错误日志状态: {error_log_result.status.value}
- 错误日志总数: {error_log_result.data.get('logs', {}).get('summary', {}).get('total_errors', 0) if error_log_result.data else 0}

请给出详细的分析和建议。"""
                
                llm_result = orchestrator.execute_module(
                    "llm_chat",
                    params={
                        "input": analysis_prompt,
                        "prompt": "你是一个专业的运维专家，擅长分析服务监控数据和故障排查。请用简洁明了的语言回答问题。"
                    }
                )
                results['llm_analysis'] = llm_result.to_dict()
                
            else:
                # 默认流程：直接使用 LLM 分析接收到的 data（key 为空或非 service_ 开头）
                # 针对告警数据的特殊处理
                prompt = "你是一个专业的运维专家，擅长分析告警信息和故障排查。请分析以下告警数据并给出处理建议。"
                
                llm_result = orchestrator.execute_module(
                    "llm_chat",
                    params={
                        "input": input_data,
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
                            "key": input_key or "default",
                            "content": notification_content
                        }
                    )
                    results['xiezuo'] = xiezuo_result.to_dict()
        else:
            # 如果没有提供 data 和 key，执行 run.py 中的默认流程
            try:
                from run import main as run_main
                
                # 捕获输出（如果需要）
                import io
                import contextlib
                
                output_buffer = io.StringIO()
                with contextlib.redirect_stdout(output_buffer):
                    with contextlib.redirect_stderr(output_buffer):
                        run_main()
                
                output = output_buffer.getvalue()
                results['output'] = output
                
            except ImportError as e:
                return jsonify({
                    "success": False,
                    "error": f"Failed to import run.py: {str(e)}"
                }), 500
            except Exception as e:
                logger.exception("Failed to execute run.py")
                return jsonify({
                    "success": False,
                    "error": str(e)
                }), 500
        
        # 返回结果 - 只返回最终的输出
        output = ""
        
        # 优先返回 LLM 分析输出
        if results.get('llm_analysis'):
            llm_result = results['llm_analysis']
            if llm_result.get('status') == 'success' and llm_result.get('data'):
                output = llm_result['data'].get('output', '')
        # 如果没有 LLM 分析，返回 run.py 的输出
        elif results.get('output'):
            output = results['output']
        
        response_data = {
            "success": True,
            "output": output
        }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.exception("Failed to execute")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


if __name__ == '__main__':
    # 加载环境变量
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    # 从环境变量获取端口，默认 8080
    port = int(os.environ.get('PORT', 8080))
    host = os.environ.get('HOST', '0.0.0.0')
    
    logger.info(f"Starting Ops Agent SLO HTTP Server on {host}:{port}")
    app.run(host=host, port=port, debug=False)

