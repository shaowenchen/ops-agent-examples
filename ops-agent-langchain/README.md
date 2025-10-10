# Ops Agent - LangChain Edition

基于 LangChain 和 FastMCP 的智能运维代理，支持自主规划和执行循环。

## 核心特性

### 🚀 动态 MCP 工具加载

- **自动发现**：使用 `fastmcp.Client` 从 MCP 服务器动态获取所有可用工具
- **零配置**：无需在代码中硬编码工具列表
- **实时更新**：MCP 服务器更新工具时，Agent 自动获取最新工具

### 🤖 自主规划执行循环

实现智能的 Agentic Loop：

1. **生成计划**：基于用户 intent 和可用的 MCP 工具生成执行计划
2. **执行计划**：使用 MCP 工具真实调用并获取数据
3. **评估结果**：判断是否达到预期目标
4. **迭代优化**：如未达标，收集更多信息并重新规划
5. **循环直至成功**：最多迭代 5 次，确保完成任务
6. **智能总结**：任务完成后，LLM 生成执行总结

## 快速开始

### 1. 安装依赖

```bash
cd ops-agent-langchain
pip install -r requirements.txt
```

### 2. 配置环境

创建 `.env` 文件或设置环境变量：

```bash
# MCP 服务器配置
export MCP_SERVER_URL="https://your-mcp-server.com/mcp"
export MCP_TOKEN="your-token"

# OpenAI API 配置
export OPENAI_API_KEY="your-api-key"
export OPENAI_API_HOST="https://api.openai.com/v1"
export OPENAI_MODEL="gpt-4"
```

或使用配置文件 `configs/config.yaml`：

```yaml
mcp:
  server_url: "https://your-mcp-server.com/mcp"
  timeout: "30s"
  token: "your-token"

openai:
  api_key: "your-key"
  api_host: "https://api.openai.com/v1"
  model: "gpt-4"
```

### 3. 创建任务文件

创建 `test.yaml`：

```yaml
version: "1.0"

tasks:
  - description: "List available SOPS"
    intent: "Discover what SOPS procedures are available and show them to me"
  
  - description: "Check Kubernetes pod status"
    intent: "Get the status of pods in kube-system namespace"
```

### 4. 运行

```bash
python -m ops_agent.main examples/test.yaml
```

或使用 verbose 模式查看详细日志：

```bash
python -m ops_agent.main examples/test.yaml --verbose
```

## 任务配置说明

每个任务支持以下字段：

```yaml
tasks:
  - description: "任务描述"        # 任务的简短描述
    intent: "用户意图和目标"       # Agent 将基于此生成执行计划（最重要）
```

**关键点**：
- `description`：任务的简短描述，用于标识和展示
- `intent` 字段是**最重要**的，它告诉 Agent 你想要达成什么目标
- Agent 会自动：
  1. 理解 intent
  2. 生成执行计划
  3. 从 MCP 服务器动态获取并调用所需工具
  4. 评估结果是否满足 intent
  5. 如果不满足，重新规划并再次尝试

## 工作原理

### 动态工具加载

```python
# Agent 启动时自动连接 MCP 服务器
async with Client(mcp_server_url) as client:
    # 动态获取所有可用工具
    mcp_tools = await client.list_tools()
    
    # 转换为 LangChain 工具
    for mcp_tool in mcp_tools:
        langchain_tool = convert_to_langchain_tool(mcp_tool)
        
    # 工具可用于 Agent 执行
```

### 自主执行循环

对每个任务，Agent 执行以下循环：

```
迭代 1:
  ├─ 📋 根据 intent 生成计划
  ├─ ⚙️  使用 MCP 工具执行计划
  ├─ ✓  评估结果是否满足 intent
  └─ ❌ 未满足 → 确定需要什么额外信息

迭代 2:
  ├─ 📋 基于前次结果优化计划
  ├─ ⚙️  执行优化后的计划
  ├─ ✓  再次评估
  └─ ✅ 满足 → 完成！

... 最多迭代 5 次
```

## 架构

```
ops-agent-langchain/
├── ops_agent/
│   ├── core/
│   │   └── agent.py          # 核心 Agent 实现（自主规划循环）
│   ├── config/
│   │   └── config_loader.py  # 配置加载
│   ├── utils/
│   │   ├── logging.py        # 日志工具
│   │   ├── formatting.py     # 格式化工具
│   │   └── callbacks.py      # LangChain 回调
│   └── main.py               # CLI 入口
├── configs/
│   └── config.yaml           # 配置文件
├── examples/
│   └── test.yaml             # 示例任务
└── requirements.txt
```

## 依赖说明

### 核心依赖

- **langchain**: LangChain 框架，用于构建 Agent
- **langchain-openai**: OpenAI 集成
- **fastmcp**: FastMCP 客户端，用于动态连接 MCP 服务器
- **nest-asyncio**: 支持嵌套异步事件循环

### 为什么使用 FastMCP？

根据 [FastMCP 文档](https://github.com/jlowin/fastmcp)：

1. **动态工具发现**：`Client.list_tools()` 自动获取所有可用工具
2. **简单易用**：
   ```python
   async with Client("https://mcp-server.com/mcp") as client:
       tools = await client.list_tools()
       result = await client.call_tool("tool_name", {"param": "value"})
   ```
3. **认证支持**：内置 OAuth、API Key 等认证方式
4. **传输协议**：支持 STDIO、HTTP、SSE 多种传输方式

## 示例输出

```
================================================================================
🎯 Task 1: List available SOPS
   Intent: Discover what SOPS procedures are available and show them to me
================================================================================

🤔 Starting autonomous planning and execution loop...

--- Iteration 1/5 ---
📋 Step 1: Generating initial execution plan...
   Available MCP Tools:
   1. list-sops-from-ops
      Description: List all available SOPS procedures
      Parameters:
       - random_string: string (required) - Dummy parameter
   ...

⚙️  Step 2: Executing plan with MCP tools...
================================================================================
🔧 MCP TOOL CALL: list-sops-from-ops
================================================================================
📥 Input parameters: {"random_string": "dummy"}
🌐 Connecting to MCP server: https://xxx.com/mcp
✅ Connected to MCP server
📞 Calling tool: list-sops-from-ops with args: {...}
✅ Tool call completed
📤 Extracted result: ["restart-pod", "delete-namespace", ...]
================================================================================

✓  Step 3: Evaluating if goal is achieved...
   Evaluation: Status: SATISFIED
   Reason: Successfully retrieved and displayed all available SOPS procedures

🎉 Goal achieved! Task completed successfully.

================================================================================
📊 TASK SUMMARY - Generating Markdown Report
================================================================================

# 最终输出（美观的 Markdown 格式）：

┌─────────────────────────────────────────────────────────────────────────────┐
│ Task 1: list-sops                                                           │
│ Status: SUCCESS | Iterations: 1                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ## 📋 Task Overview                                                        │
│                                                                             │
│  Successfully retrieved all available SOPS procedures from the MCP server   │
│  using automated discovery.                                                 │
│                                                                             │
│  ## 🎯 Objective                                                            │
│                                                                             │
│  Discover what SOPS procedures are available and display them clearly.     │
│                                                                             │
│  ## 🔧 Execution Process                                                    │
│                                                                             │
│  • Connected to MCP server at https://xxx.com/mcp                          │
│  • Called `list-sops-from-ops` tool with proper parameters                │
│  • Retrieved complete list of 12 SOPS procedures                           │
│                                                                             │
│  ## ✨ Key Findings                                                         │
│                                                                             │
│  Available SOPS procedures:                                                │
│  - restart-pod                                                             │
│  - delete-namespace                                                        │
│  - scale-deployment                                                        │
│  - create-namespace                                                        │
│  - ... (8 more procedures)                                                 │
│                                                                             │
│  ## 📊 Summary                                                              │
│                                                                             │
│  Task completed successfully in 1 iteration. All SOPS procedures were      │
│  discovered using real-time MCP server data. The intent was fully          │
│  satisfied with accurate, actionable information.                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

================================================================================
                            📈 OVERALL SUMMARY
================================================================================

  ✅ Successful Tasks: 1
  ❌ Failed Tasks:     0
  📊 Total Tasks:      1

================================================================================
```

## 贡献

欢迎提交 Issue 和 Pull Request！

## License

Apache-2.0

