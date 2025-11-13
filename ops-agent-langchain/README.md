# Ops Agent - ReAct Edition

基于 ReAct (Reasoning, Acting, Observing) 模式的智能运维代理，采用最佳实践实现。

## 🚀 核心特性

### 🧠 纯 ReAct 模式实现

- **推理 (Reasoning)**: 智能分析当前情况，决定下一步行动
- **行动 (Acting)**: 调用相应的 MCP 工具执行具体操作
- **观察 (Observing)**: 分析工具执行结果，为下一步推理提供信息
- **循环执行**: 持续进行 ReAct 循环直到完成任务

### 🔧 增强功能

- **错误处理**: 智能错误恢复和重试机制
- **性能监控**: 详细的执行时间和步骤统计
- **参数验证**: 工具参数类型和必需性验证
- **超时控制**: 可配置的步骤超时设置
- **详细日志**: 完整的执行过程记录

### 🌐 动态 MCP 工具加载

- **自动发现**: 从 MCP 服务器动态获取所有可用工具
- **零配置**: 无需在代码中硬编码工具列表
- **实时更新**: MCP 服务器更新工具时，Agent 自动获取最新工具
- **工具验证**: 自动验证工具参数类型和必需性

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

创建 `demo.yaml`：

```yaml
version: "1.0"

tasks:
  - description: "List available SOPS procedures"
    intent: "Discover what SOPS procedures are available and show them to me"
  
  - description: "Get system metrics"
    intent: "Check the current system health by getting available metrics"
```

### 4. 运行

```bash
python main.py examples/demo.yaml
```

或使用高级选项：

```bash
python main.py examples/demo.yaml --verbose --max-steps 15 --step-timeout 45
```

## 命令行选项

- `--verbose`: 启用详细日志输出
- `--max-steps`: 设置最大 ReAct 步骤数 (默认: 10)
- `--step-timeout`: 设置每个步骤的超时时间，秒 (默认: 30.0)
- `--config`: 指定配置文件路径

## ReAct 模式工作原理

### 执行流程

```
问题: "列出可用的 SOPS 程序"

Step 1:
├─ 🧠 Reasoning: "我需要获取 SOPS 程序列表，应该使用 list-sops-from-ops 工具"
├─ ⚙️ Acting: 调用 list-sops-from-ops 工具
└─ 👁️ Observing: 获得 42 个可用程序的列表

Step 2:
├─ 🧠 Reasoning: "我已经获得了完整的 SOPS 程序列表，可以给出最终答案"
├─ ⚙️ Acting: 无需进一步行动
└─ ✅ Final Answer: "有 42 个可用的 SOPS 程序，包括..."
```

### 智能特性

1. **自适应推理**: 根据观察结果调整下一步行动
2. **错误恢复**: 工具调用失败时自动重试或寻找替代方案
3. **参数优化**: 自动调整工具参数以获得最佳结果
4. **超时处理**: 防止长时间等待，确保系统响应性

## 任务配置说明

每个任务支持以下字段：

```yaml
tasks:
  - description: "任务描述"        # 任务的简短描述
    intent: "用户意图和目标"       # Agent 将基于此进行 ReAct 推理（最重要）
```

**关键点**：
- `description`：任务的简短描述，用于标识和展示
- `intent` 字段是**最重要**的，它告诉 Agent 你想要达成什么目标
- Agent 会自动：
  1. 理解 intent
  2. 进行 ReAct 推理循环
  3. 从 MCP 服务器动态获取并调用所需工具
  4. 观察结果并决定下一步行动
  5. 重复直到目标达成

## 性能监控

ReAct Agent 提供详细的性能统计：

- **总步骤数**: 完成任务的 ReAct 步骤数量
- **成功步骤**: 成功执行的步骤数
- **失败步骤**: 失败的步骤数
- **总执行时间**: 整个任务的执行时间
- **平均步骤时间**: 每个步骤的平均执行时间

## 最佳实践

### 1. 任务设计

- **明确意图**: 使用清晰、具体的 intent 描述
- **单一目标**: 每个任务专注于一个明确的目标
- **合理范围**: 避免过于复杂或模糊的任务

### 2. 性能优化

- **合理超时**: 根据工具特性设置适当的超时时间
- **步骤限制**: 设置合理的最大步骤数避免无限循环
- **工具选择**: 优先使用更高效的工具

### 3. 错误处理

- **监控日志**: 关注详细日志中的错误信息
- **参数验证**: 确保工具参数类型和格式正确
- **重试策略**: 对于网络或临时性错误，Agent 会自动重试

## 架构

```
ops-agent-langchain/
├── ops_agent/
│   ├── core/
│   │   └── agent.py          # 核心 ReAct Agent 实现
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
│   └── react-demo.yaml       # 示例任务
└── main.py                   # 主程序入口
```

## 技术栈

- **LangChain**: LLM 集成和工具调用
- **FastMCP**: MCP 服务器连接和工具发现
- **OpenAI**: 大语言模型推理
- **Rich**: 美观的控制台输出
- **Click**: 命令行界面
- **Pydantic**: 数据验证和类型安全

## 贡献

欢迎提交 Issue 和 Pull Request 来改进这个项目！

## 许可证

MIT License