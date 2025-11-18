import os
import asyncio
import traceback
import logging
import httpx
from dotenv import load_dotenv
from autogen_ext.tools.mcp import SseServerParams, mcp_server_tools, SseMcpToolAdapter

load_dotenv()

# 配置日志以显示HTTP请求和响应的headers
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# 创建自定义的HTTP客户端来捕获headers
class HeaderLoggingTransport(httpx.BaseTransport):
    def __init__(self, transport):
        self.transport = transport
    
    async def aclose(self):
        await self.transport.aclose()
    
    async def arequest(self, method, url, headers=None, stream=None, ext=None):
        print(f"\n🚀 发送请求:")
        print(f"   Method: {method}")
        print(f"   URL: {url}")
        print(f"   Headers: {dict(headers) if headers else {}}")
        
        response = await self.transport.arequest(method, url, headers, stream, ext)
        
        print(f"\n📥 收到响应:")
        print(f"   Status: {response.status_code}")
        print(f"   Headers: {dict(response.headers)}")
        
        return response

async def main():
    mcp_url = os.getenv("MCP_SERVER_URL111", "http://localhost:8081/api/mcp/sse")
    print(f"📡 正在连接 MCP Server: {mcp_url}")

    try:
        # 创建HTTP客户端来记录请求和响应的headers
        # 使用两种方法确保headers被正确记录：
        # 1. 自定义Transport (作为备用)
        # 2. httpx事件钩子 (主要方法)
        
        transport = httpx.AsyncHTTPTransport()
        logging_transport = HeaderLoggingTransport(transport)
        client = httpx.AsyncClient(transport=logging_transport)
        
        # 添加事件钩子来记录请求和响应
        def log_request(request):
            print(f"\n🚀 发送请求:")
            print(f"   Method: {request.method}")
            print(f"   URL: {request.url}")
            print(f"   Headers: {dict(request.headers)}")
        
        def log_response(response):
            print(f"\n📥 收到响应:")
            print(f"   Status: {response.status_code}")
            print(f"   Headers: {dict(response.headers)}")
        
        client.event_hooks = {
            "request": [log_request],
            "response": [log_response]
        }
        
        server_params = SseServerParams(
            url=mcp_url, 
            sse_read_timeout=30,  # 增加SSE读取超时时间
            timeout=10,           # 增加HTTP请求超时时间
            http_client=client
            )
            # Get the translation tool from the server
        # adapter = await SseMcpToolAdapter.from_server_params(server_params, "get_alerts")

        # print(adapter)

        # ✅ 获取工具列表
        tools = await mcp_server_tools(server_params)

        # ✅ 打印工具信息
        print(f"✅ 成功获取 {len(tools)} 个工具:\n")
        for i, tool in enumerate(tools, 1):
            print(f"{i}. {tool.name} - {tool.description or '无描述'}")

    except Exception as e:
        print(f"❌ 获取工具失败: {e}")
        print("详细错误信息:")
        traceback.print_exc()
    finally:
        # 清理HTTP客户端
        if 'client' in locals():
            await client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
