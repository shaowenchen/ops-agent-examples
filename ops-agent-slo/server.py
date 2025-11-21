#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTTP 服务入口 - Ops Agent SLO

此文件是 HTTP API 服务入口，提供：
1. /health - 健康检查接口
2. /trigger - 触发分析流程接口

当 /trigger 接口没有提供 data 和 key 参数时，会调用 sla.py 中的编排逻辑。
真实的业务编排逻辑在 sla.py 中定义。
"""
import os
import sys
from typing import Optional, Dict, Any
from flask import Flask, request, jsonify
from datetime import datetime

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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
    
    从 POST 请求的 body 中接收数据：
    {
        "data": "分析内容或数据",
        "key": "标识键，用于区分不同的分析类型",
        "verbose": false
    }
    
    所有处理逻辑都在 sla.py 中，server.py 只负责接收请求和调用 sla.py
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
        
        # 调用 sla.py 中的编排逻辑
        # sla.py 包含所有真实的业务编排逻辑，包括动态分析流程
        try:
            from sla import main as sla_main
            
            # 调用 sla.py 的 main 函数，传递 data 和 key 参数
            results = sla_main(data=input_data, key=input_key)
            
            # 返回结果 - 只返回最终的输出
            output = ""
            
            # 优先返回 LLM 分析输出
            if results.get('llm_analysis'):
                llm_result = results['llm_analysis']
                if llm_result.get('status') == 'success' and llm_result.get('data'):
                    output = llm_result['data'].get('output', '')
            
            response_data = {
                "success": True,
                "output": output
            }
            
            return jsonify(response_data), 200
                
        except ImportError as e:
            return jsonify({
                "success": False,
                "error": f"Failed to import sla.py: {str(e)}"
            }), 500
        except Exception as e:
            logger.exception("Failed to execute sla.py")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500
        
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

