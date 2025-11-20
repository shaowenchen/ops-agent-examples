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
from ops_agent.modules import UpstreamQueryModule, ErrorLogQueryModule
from ops_agent.utils.logging import setup_logging, get_logger

app = Flask(__name__)
logger = get_logger(__name__)

# 存储任务执行状态
task_status = {}


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
    """触发执行 run.py 中的代码"""
    try:
        # 支持 GET 和 POST 请求
        if request.method == 'GET':
            verbose = request.args.get('verbose', 'false').lower() == 'true'
        else:
            data = request.get_json() or {}
            verbose = data.get('verbose', False)
        
        # 设置日志
        log_level = "DEBUG" if verbose else "INFO"
        setup_logging(log_level)
        
        # 执行 run.py 中的 main 函数
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
            
            return jsonify({
                "success": True,
                "message": "Execution completed",
                "output": output
            }), 200
            
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
        
    except Exception as e:
        logger.exception("Failed to execute")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/status/<task_id>', methods=['GET'])
def get_status(task_id):
    """获取任务状态"""
    if task_id not in task_status:
        return jsonify({
            "success": False,
            "error": "Task not found"
        }), 404
    
    status = task_status[task_id].copy()
    
    # 如果任务已完成或失败，包含完整结果
    if status["status"] in ["completed", "failed"]:
        return jsonify({
            "success": True,
            "task_id": task_id,
            **status
        })
    else:
        # 运行中，只返回状态
        return jsonify({
            "success": True,
            "task_id": task_id,
            "status": status["status"],
            "start_time": status.get("start_time"),
            "message": status.get("message", "任务执行中...")
        })


@app.route('/tasks', methods=['GET'])
def list_tasks():
    """列出所有任务"""
    tasks = []
    for task_id, status in task_status.items():
        tasks.append({
            "task_id": task_id,
            "status": status["status"],
            "start_time": status.get("start_time"),
            "end_time": status.get("end_time")
        })
    
    # 按开始时间倒序排列
    tasks.sort(key=lambda x: x.get("start_time", ""), reverse=True)
    
    return jsonify({
        "success": True,
        "tasks": tasks,
        "total": len(tasks)
    })


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

