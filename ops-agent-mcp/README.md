# Ops Agent - MCP Edition (Simplified)

一个简单的 MCP（Management Control Plane）客户端工具，直接调用指定的 MCP 函数。

## 项目简介

Ops Agent MCP Edition (Simplified) 是一个极简的 MCP 客户端，它直接在代码中调用指定的 MCP 函数，无需命令行参数。这个版本专注于简单性和易用性，适合快速集成到其他项目中。

## 核心特性

- **极致简单**：直接在代码中设置参数，无需命令行接口
- **灵活配置**：支持通过配置文件和环境变量进行配置
- **完整的日志记录**：详细的日志输出，方便调试和问题排查
- **错误处理**：完善的错误处理机制

## 快速开始

### 1. 安装依赖

```bash
cd ops-agent-mcp
pip install -r requirements.txt
```

### 2. 配置环境

可以通过以下两种方式之一配置环境：

#### 使用配置文件

编辑 `configs/config.yaml` 文件：

```yaml
# Ops Agent MCP Edition Configuration

# MCP Server Configuration
mcp:
  # MCP server URL
  server_url: "https://your-mcp-server.com/mcp"
  
  # MCP server name
  server_name: "mcp-server"
  
  # Request timeout
  timeout: "30s"
  
  # Authentication token
  token: "your-mcp-token"
```

#### 使用环境变量

创建 `.env` 文件或直接设置环境变量：

```bash
# 复制示例文件
cp .env.example .env

# 编辑 .env 文件
```

### 3. 使用方法

1. 修改根目录下的 `main.py` 文件中的以下参数：
   ```python
   # 在这里直接指定要调用的 MCP 服务器名称、工具名称和参数
   server_name = "mcp.config.usrlocalmcp.ops-mcp-server-sse"
   tool_name = "get-events-from-ops"
   args = {
       "subject_pattern": "ops.clusters.*",
       "limit": "5"
   }
   ```

2. 运行程序：
   ```bash
   python main.py
   ```

程序将直接调用你在代码中指定的 MCP 函数并显示结果。

## 项目结构

```
ops-agent-mcp/
├── .env.example        # 环境变量示例文件
├── .gitignore          # Git 忽略文件
├── README.md           # 项目说明文档
├── configs/            # 配置文件目录
│   └── config.yaml     # 主配置文件
├── main.py             # 主入口文件（根目录）
├── ops_agent/          # 核心代码模块目录
│   ├── __init__.py     # 包初始化文件
│   ├── config/         # 配置相关模块
│   │   └── config_loader.py  # 配置加载器
│   ├── core/           # 核心功能模块
│   │   └── mcp_client.py     # MCP 客户端实现
│   ├── tools/          # 工具模块
│   │   └── mcp_tool.py       # MCP 工具封装
│   └── utils/          # 工具函数
│       └── logging.py        # 日志工具
└── requirements.txt    # 项目依赖
```

## 依赖说明

- **fastmcp**：用于与 MCP 服务器进行交互的核心库
- **pyyaml**：用于解析 YAML 配置文件
- **python-dotenv**：用于加载环境变量
- **colorlog**：用于彩色日志输出
- **click**：用于创建命令行接口
- **rich**：用于增强命令行输出

## 注意事项

- 请确保 MCP 服务器地址和认证令牌正确配置
- 日志文件会保存在 `logs/ops-agent.log` 中
- 对于复杂的参数，建议使用 JSON 格式通过 `--args` 参数传递

## 许可证

[MIT](LICENSE)