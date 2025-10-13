#!/usr/bin/env python3
"""
Main entry point for Ops Agent MCP Edition (Simplified)
"""

import os
import sys
import json
import logging

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入依赖的模块
from ops_agent.config import ConfigLoader
from ops_agent.tools.mcp_tool import MCPTool
from ops_agent.utils.logging import setup_logging, get_logger

# 设置日志
setup_logging("INFO")
logger = get_logger(__name__)

def main():
    """简化版主函数，直接调用指定的 MCP 函数"""
    try:
        # 初始化配置加载器
        config_loader = ConfigLoader()
        config_loader.load_config()
        
        # 初始化 MCP 工具
        mcp_tool = MCPTool(config_loader)
        
        # 默认使用配置中的服务器名称，如果配置中没有则使用以下值
        
        # 在这里指定要调用的 MCP 工具名称和参数
        # 用户可以根据需要修改这些值
        tool_name = "get-events-from-ops"
        args = {
            "subject_pattern": "ops.clusters.>",
            "limit": "5"
        }
        
        print(f"调用 MCP 工具: {tool_name}")
        print(f"参数: {args}")
        
        # 调用 MCP 工具 - 直接使用工具名称，不需要服务器名称前缀
        result = mcp_tool.execute(tool_name=tool_name, args=args)
        
        # 打印结果
        print("\n执行结果:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
    except Exception as e:
        print(f"\n错误: {str(e)}")
        logger.error(f"执行失败: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()