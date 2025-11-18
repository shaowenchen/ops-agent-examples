# -*- coding: utf-8 -*-
import asyncio
import os
from dotenv import load_dotenv
from autogen_core.models import ModelFamily
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import TextMentionTermination
from autogen_core import CancellationToken
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.tools.mcp import SseServerParams, mcp_server_tools

load_dotenv()

# ------------------- MCP 工具获取 -------------------
async def get_mcp_tools(mcp_url: str):
    """使用 autogen 直接获取 MCP 工具"""
    print(f"🔧 连接 MCP: {mcp_url}")
    try:
        # 创建 MCP 服务器参数
        mcp_params = SseServerParams(
            url=mcp_url,
            headers={"content-type": "text/event-stream; charset=utf-8"},
            timeout=30,
            sse_read_timeout=60
        )
        
        # 获取工具
        tools = await mcp_server_tools(mcp_params)
        print(f"✅ 获取 {len(tools)} 个工具")
        return tools
    except Exception as e:
        print(f"❌ 获取工具失败: {e}")
        return []

# ------------------- 主逻辑 -------------------
async def main():
    events_mcp_url = os.getenv("MCP_SERVER_URL_EVENTS")
    sops_mcp_url = os.getenv("MCP_SERVER_URL_SOPS")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    openai_api_host = os.getenv("OPENAI_API_HOST")
    openai_model_name = os.getenv("OPENAI_MODEL", "custom-llm")

    if not events_mcp_url or not sops_mcp_url or not openai_api_key or not openai_api_host:
        raise ValueError("请确保 .env 中配置了 MCP_SERVER_URL_EVENTS/SOPS、OPENAI_API_KEY、OPENAI_API_HOST")

    # 获取 MCP 工具
    print("🔧 获取 Events 工具...")
    events_tools = await get_mcp_tools(events_mcp_url)
    
    print("🔧 获取 SOPS 工具...")
    sops_tools = await get_mcp_tools(sops_mcp_url)

    openai_client = OpenAIChatCompletionClient(
        model=openai_model_name,
        api_key=openai_api_key,
        base_url=openai_api_host,
        model_info={
        "vision": False,
        "function_calling": True,
        "json_output": False,
        "family": ModelFamily.R1,
        "structured_output": True,
        },
    )

    # ------------------- 创建 Agents -------------------
    events_agent = AssistantAgent(
        name="events_agent",
        model_client=openai_client,
        tools=events_tools,
        system_message="你是事件查询助手，使用 MCP Events 工具查询系统事件。"
    )

    sops_agent = AssistantAgent(
        name="sops_agent",
        model_client=openai_client,
        tools=sops_tools,
        system_message="你是标准操作助手，使用 MCP SOPS 工具执行系统操作。"
    )

    # ------------------- 创建团队并执行任务 -------------------
    termination = TextMentionTermination("TERMINATE")
    team = RoundRobinGroupChat([events_agent, sops_agent], termination_condition=termination)

    task_description = (
        "使用 MCP Events 工具查询系统事件，并使用 MCP SOPS 工具执行相关操作，"
        "目标节点为 kcs-jinshan-wh-s-l6bhn。"
    )

    result = await team.run(task=task_description, cancellation_token=CancellationToken())
    print("\n✅ 任务完成，输出结果:")
    print(result.messages[-1].content if result.messages else "无输出内容")

if __name__ == "__main__":
    asyncio.run(main())
