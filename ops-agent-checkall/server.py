#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTTP Server for triggering Ops Agent CheckAll tasks
"""
import os
import sys
import json
import threading
from typing import Optional, Dict, Any
from flask import Flask, request, jsonify
from datetime import datetime

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ops_agent.config import ConfigLoader
from ops_agent.core import MCPQueryExecutor, LLMSummarizer
from ops_agent.core.formatters import format_query_result
from ops_agent.utils.logging import setup_logging, get_logger
from ops_agent.utils.time_utils import add_time_params_to_query

app = Flask(__name__)
logger = get_logger(__name__)

# 存储任务执行状态
task_status = {}




@app.route('/health', methods=['GET'])
def health():
    """健康检查端点"""
    return jsonify({
        "status": "healthy",
        "service": "ops-agent-checkall",
        "timestamp": datetime.now().isoformat()
    })


@app.route('/trigger', methods=['GET'])
def trigger_task():
    """触发任务执行并直接返回结果"""
    try:
        # GET 请求从查询参数获取
        config = request.args.get('config')
        queries = request.args.get('queries')
        verbose = request.args.get('verbose', 'false').lower() == 'true'
        # 默认不总结，可以通过 summary=true 参数覆盖
        summary = request.args.get('summary', 'false').lower() == 'true'
        
        # 设置日志
        log_level = "DEBUG" if verbose else "INFO"
        setup_logging(log_level)
        
        # 初始化配置
        config_loader = ConfigLoader(config_file=config)
        config_loader.load_config()
        
        # 加载查询文件
        if queries:
            queries_file = queries
        else:
            # 尝试默认位置
            default_locations = [
                os.path.join(os.path.dirname(__file__), "default.yaml"),
                "./default.yaml",
            ]
            queries_file = None
            for loc in default_locations:
                if os.path.exists(loc):
                    queries_file = loc
                    break
            
            if not queries_file:
                return jsonify({
                    "success": False,
                    "error": "No queries file found. Please specify with queries parameter"
                }), 400
        
        import yaml
        with open(queries_file, 'r', encoding='utf-8') as f:
            queries_config = yaml.safe_load(f)
        
        query_list = queries_config.get('queries', [])
        summary_prompt = queries_config.get('summary_prompt')
        
        if not query_list:
            return jsonify({
                "success": False,
                "error": "No queries found in queries file"
            }), 400
        
        # 获取查询配置
        query_config = config_loader.query_config
        default_time_range = query_config.default_time_range
        time_param_names = query_config.time_param_names
        
        # 添加默认时间范围
        modified_queries = []
        for query in query_list:
            modified_query = add_time_params_to_query(
                query,
                default_time_range,
                time_param_names
            )
            modified_queries.append(modified_query)
        
        query_list = modified_queries
        
        # 初始化组件
        query_executor = MCPQueryExecutor(config_loader)
        
        # 执行查询
        results = query_executor.execute_queries(query_list)
        
        # 格式化结果
        output_lines = []
        for result in results:
            if result.get('success', False):
                tool_name = result.get('tool_name', 'unknown')
                desc = result.get('desc', '')
                result_data = result.get('result', {})
                formater_name = result.get('formater')
                
                # 检查是否有数据
                has_data = False
                if result_data:
                    if isinstance(result_data, dict):
                        if 'content' in result_data:
                            content = result_data['content']
                            if isinstance(content, list) and len(content) > 0:
                                has_data = True
                            elif isinstance(content, str) and content.strip():
                                has_data = True
                            elif content:
                                has_data = True
                        elif result_data:
                            has_data = True
                    elif result_data:
                        has_data = True
                
                if not has_data:
                    continue
                
                formatted_result = format_query_result(result_data, formatter_name=formater_name, tool_name=tool_name)
                
                if desc:
                    output_lines.append(f"### {desc}")
                    output_lines.append("")
                
                if formatted_result and formatted_result.strip():
                    output_lines.append(formatted_result)
                    output_lines.append("")
        
        output = "\n".join(output_lines).strip()
        
        # 生成总结
        summary_result = None
        if summary and output:
            summarizer = LLMSummarizer(config_loader)
            summary_result = summarizer.summarize(results, summary_prompt)
            if summary_result:
                output += f"\n\n## AI 总结\n\n{summary_result}"
        
        # 直接返回执行结果
        return jsonify({
            "success": True,
            "output": output,
            "summary": summary_result
        }), 200
        
    except Exception as e:
        logger.exception("Failed to execute task")
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
    
    logger.info(f"Starting Ops Agent CheckAll HTTP Server on {host}:{port}")
    app.run(host=host, port=port, debug=False)

