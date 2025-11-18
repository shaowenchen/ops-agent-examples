# -*- coding: utf-8 -*-
import asyncio
import os
import ssl
from dotenv import load_dotenv
from fastmcp import Client

# 加载 .env 文件
load_dotenv()


async def main():
    print("🚀 初始化 MCP 连接...")
    
    # 从环境变量读取 MCP 服务器配置
    mcp_url = os.getenv("MCP_SERVER_URL")
    mcp_token = os.getenv("MCP_TOKEN")
    
    if not mcp_url:
        print("❌ 错误: 未找到 MCP_SERVER_URL 环境变量")
        print("请在 .env 文件中设置: MCP_SERVER_URL=https://your-server.com/mcp")
        return
    
    print(f"📡 正在连接 MCP Server: {mcp_url}")
    
    try:
        # 使用 fastmcp.Client 连接 (参考 langchain 版本)
        async with Client(mcp_url, auth=mcp_token) as client:
            print("✅ 成功连接到 MCP 服务器")
            
            # 获取工具列表
            print("🔧 正在获取工具列表...")
            mcp_tools = await client.list_tools()
            
            print(f"✅ 成功获取到 {len(mcp_tools)} 个工具:")
            print("=" * 60)
            
            for i, tool in enumerate(mcp_tools, 1):
                print(f"\n🔨 工具 {i}: {tool.name}")
                print(f"   描述: {tool.description or '无描述'}")
                
                # 打印参数信息
                if hasattr(tool, 'inputSchema') and tool.inputSchema:
                    schema = tool.inputSchema
                    properties = schema.get('properties', {})
                    required = schema.get('required', [])
                    
                    if properties:
                        print("   参数:")
                        for param_name, param_info in properties.items():
                            param_type = param_info.get('type', 'unknown')
                            param_desc = param_info.get('description', '无描述')
                            is_required = param_name in required
                            required_text = " (必需)" if is_required else " (可选)"
                            print(f"     - {param_name}: {param_type}{required_text} - {param_desc}")
                    else:
                        print("   参数: 无")
                else:
                    print("   参数: 无")
            
            print("\n" + "=" * 60)
            print(f"📊 总计: {len(mcp_tools)} 个工具")
            
    except asyncio.TimeoutError:
        print("⚠️ 连接超时，SSE 服务可能未响应。")
        print("⚠️ 未获取到任何工具信息。")
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())