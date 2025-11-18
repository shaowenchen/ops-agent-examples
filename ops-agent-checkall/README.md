# Ops Agent CheckAll

一个用于执行一系列 MCP 数据查询并使用 LLM 进行总结的工具。

## 功能特性

- 🔍 **批量 MCP 查询**: 支持执行多个 MCP 查询
- ⏰ **自动时间范围**: 自动为查询添加默认时间范围（默认最近3小时，可在配置中修改）
- 🤖 **LLM 智能总结**: 使用 LLM 对查询结果进行智能分析和总结
- 📊 **结果可视化**: 使用 Rich 库提供美观的控制台输出
- ⚙️ **灵活配置**: 支持配置文件和环境变量
- 📝 **结果保存**: 自动保存查询结果和总结到 JSON 文件
- 🛠️ **多模块支持**: 支持 SOPS、Events、Metrics、Logs、Traces 等多个运维模块
- 📢 **通知功能**: 支持在分析完成后发送通知到群聊（通过环境变量配置）

## 安装

1. 克隆或进入项目目录：
```bash
cd ops-agent-checkall
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

## 配置

### 1. 配置文件

编辑 `configs/config.yaml` 文件，配置 MCP 服务器和 OpenAI API：

```yaml
mcp:
  server_url: "https://your-mcp-server-url.com/mcp"
  timeout: "30s"
  token: "your-mcp-token-here"

query:
  # Default time range for queries (e.g., "10m" for 10 minutes)
  # This will be automatically added to queries that don't specify time parameters
  default_time_range: "10m"
  
  # Time parameter names to use (comma-separated)
  # Common options: "start_time,end_time", "since", "duration"
  time_param_names: "start_time,end_time"

openai:
  api_key: "your-openai-api-key"
  api_host: "https://api.openai.com/v1"
  model: "gpt-4"
  max_tokens: 4000
```

### 2. 环境变量（可选）

也可以通过环境变量配置：

```bash
export MCP_SERVERURL="https://your-mcp-server-url.com/mcp"
export MCP_TOKEN="your-mcp-token"
export MCP_TIMEOUT="30s"
export QUERY_DEFAULT_TIME_RANGE="10m"
export QUERY_TIME_PARAM_NAMES="start_time,end_time"
export OPENAI_API_KEY="your-openai-api-key"
export OPENAI_API_HOST="https://api.openai.com/v1"
export OPENAI_MODEL="gpt-4"
export OPENAI_MAX_TOKENS="4000"

# Notification configuration (optional)
export NOTIFY_URL="https://your-notification-webhook-url.com"
# 或
export NOTIFICATION_URL="https://your-notification-webhook-url.com"
```

### 3. 查询配置

编辑 `queries.yaml` 文件，定义要执行的 MCP 查询。每个查询可以包含：

- `tool_name`: MCP 工具名称（必需）
- `args`: 工具参数（可选）
- `desc`: 查询描述（可选），用于大模型总结时理解查询目的，例如："最近10分钟 CPU使用率超过50%的节点"

**注意**：`desc` 字段是给大模型看的描述，用于帮助 LLM 更好地理解每个查询的目的和上下文，从而生成更准确的总结。

```yaml
queries:
  - tool_name: "get-events-from-ops"
    args:
      subject_pattern: "ops.clusters.>"
      limit: "5"
  
  - tool_name: "another-tool-name"
    args:
      param1: "value1"
      param2: "value2"
```

可选：自定义总结提示词：

```yaml
summary_prompt: "请用中文总结以下查询结果，重点关注..."
```

## 使用方法

### 基本用法

```bash
python main.py
```

### 指定配置文件

```bash
python main.py -c /path/to/config.yaml
```

### 指定查询文件

```bash
python main.py -q /path/to/queries.yaml
```

### 使用示例查询文件

项目提供了多个示例查询文件，可以根据不同场景使用：

- `queries-example-minimal.yaml`: 最小示例，包含基本查询
- `queries-example-comprehensive.yaml`: 全面示例，覆盖所有模块
- `queries-example-logs-focused.yaml`: 日志聚焦示例，用于故障排查
- `queries-example-metrics-focused.yaml`: 指标聚焦示例，用于系统监控

使用示例：

```bash
# 使用最小示例
python main.py -q queries-example-minimal.yaml

# 使用全面示例
python main.py -q queries-example-comprehensive.yaml

# 使用日志聚焦示例
python main.py -q queries-example-logs-focused.yaml

# 使用指标聚焦示例
python main.py -q queries-example-metrics-focused.yaml
```

### 详细日志

```bash
python main.py --verbose
```

### 生成 LLM 总结

```bash
# 生成总结（不发送通知）
python main.py --summary
```

### 生成 LLM 总结并发送通知

```bash
# 设置通知 URL 环境变量
export NOTIFY_URL="https://your-webhook-url.com"

# 生成总结并发送通知
python main.py --summary --notify
```

注意：
- 通知功能需要同时使用 `--summary` 和 `--notify` 选项
- 如果未设置 `NOTIFY_URL` 环境变量，程序会跳过通知发送并显示警告
- 默认情况下不会发送通知，需要明确指定 `--notify` 选项

## 输出

程序会：

1. 在控制台显示每个查询的执行状态
2. 使用 LLM 生成总结（除非使用 `--no-summary`）
3. 将结果保存到 `results.json` 文件

## 项目结构

```
ops-agent-checkall/
├── main.py                 # 主程序入口
├── configs/
│   └── config.yaml         # 配置文件
├── queries.yaml            # 查询配置文件
├── requirements.txt        # Python 依赖
├── README.md              # 说明文档
└── ops_agent/
    ├── __init__.py
    ├── config/             # 配置模块
    │   ├── __init__.py
    │   └── config_loader.py
    ├── core/               # 核心模块
    │   ├── __init__.py
    │   ├── mcp_query_executor.py  # MCP 查询执行器
    │   └── llm_summarizer.py      # LLM 总结器
    └── utils/              # 工具模块
        ├── __init__.py
        └── logging.py
```

## 支持的 MCP 工具

本项目支持以下运维模块的 MCP 工具：

### 1. SOPS Operations (3 个工具)
- `list-sops-from-ops`: 列出所有可用的 SOPS 标准操作流程
- `execute-sops-from-ops`: 执行指定的 SOPS 流程
- `list-sops-parameters-from-ops`: 列出指定 SOPS 流程所需的参数

### 2. Kubernetes Events (2 个工具)
- `list-events-from-ops`: 列出可用的事件类型
- `get-events-from-ops`: 根据 NATS subject 模式查询事件（支持通配符）

### 3. Elasticsearch Logs (4 个工具)
- `list-log-indices-from-elasticsearch`: 列出所有 Elasticsearch 索引
- `search-logs-from-elasticsearch`: 全文搜索日志消息
- `get-path-logs-from-elasticsearch`: 查询特定路径的日志
- `get-pod-logs-from-elasticsearch`: 查询特定 Kubernetes Pod 的日志

### 4. Prometheus Metrics (3 个工具)
- `list-metrics-from-prometheus`: 列出所有可用的 Prometheus 指标
- `query-metrics-from-prometheus`: 执行 PromQL 即时查询
- `query-metrics-range-from-prometheus`: 执行 PromQL 范围查询

### 5. Jaeger Traces (4 个工具)
- `get-services-from-jaeger`: 获取所有服务名称
- `get-operations-from-jaeger`: 获取指定服务的操作列表
- `find-traces-from-jaeger`: 根据条件搜索追踪
- `get-trace-from-jaeger`: 根据追踪 ID 获取追踪详情

## 示例

### 示例 1: 基本查询（自动添加时间范围）

```yaml
queries:
  - tool_name: "get-events-from-ops"
    args:
      subject_pattern: "ops.clusters.>"
      page_size: "10"
    desc: "获取所有集群的事件信息"
```

注意：如果查询中没有指定时间参数（如 `start_time`, `end_time`, `since` 等），程序会自动根据配置中的 `default_time_range` 添加时间范围参数。

### 示例 2: 多模块综合查询

```yaml
queries:
  # SOPS 模块
  - tool_name: "list-sops-from-ops"
    args: {}
    desc: "列出所有可用的 SOPS 操作流程"
  
  # Events 模块
  - tool_name: "get-events-from-ops"
    args:
      subject_pattern: "ops.clusters.*.nodes.*.event"
      page_size: "50"
    desc: "获取所有节点的 Kubernetes 事件"
  
  # Logs 模块
  - tool_name: "search-logs-from-elasticsearch"
    args:
      search_term: "error"
      size: "50"
    desc: "搜索最近一段时间内的错误日志"
  
  # Metrics 模块
  - tool_name: "query-metrics-from-prometheus"
    args:
      query: "up"
    desc: "查询 Prometheus 中所有服务的运行状态"
  
  # Traces 模块
  - tool_name: "get-services-from-jaeger"
    args: {}
    desc: "获取 Jaeger 中所有服务名称"
```

### 示例 3: Elasticsearch 日志查询

```yaml
queries:
  # 列出所有索引
  - tool_name: "list-log-indices-from-elasticsearch"
    args:
      format: "table"
      health: "green"
    group: "logs"
    description: "List Elasticsearch indices"
  
  # 查询特定路径的日志
  - tool_name: "get-path-logs-from-elasticsearch"
    args:
      path: "/api/v1/users"
      method: "GET"
      status_code: "200"
      size: "100"
    group: "logs"
    description: "Get logs for /api/v1/users endpoint"
  
  # 查询特定 Pod 的日志
  - tool_name: "get-pod-logs-from-elasticsearch"
    args:
      pod: "my-app-5d8f9b7c4-abc123"
      size: "50"
    group: "logs"
    description: "Get logs for specific pod"
```

### 示例 4: Prometheus 指标查询

```yaml
queries:
  # 即时查询
  - tool_name: "query-metrics-from-prometheus"
    args:
      query: "cpu_usage_percent"
    group: "metrics"
    description: "Query current CPU usage"
  
  # 范围查询
  - tool_name: "query-metrics-range-from-prometheus"
    args:
      query: "rate(http_requests_total[5m])"
      time_range: "1h"
      step: "60s"
    group: "metrics"
    description: "Query HTTP request rate over 1 hour"
```

### 示例 5: Jaeger 追踪查询

```yaml
queries:
  # 获取所有服务
  - tool_name: "get-services-from-jaeger"
    args: {}
    group: "traces"
    description: "Get all services"
  
  # 获取服务的操作列表
  - tool_name: "get-operations-from-jaeger"
    args:
      service: "user-service"
      spanKind: "server"
    group: "traces"
    description: "Get operations for user-service"
  
  # 搜索追踪（需要指定时间范围）
  - tool_name: "find-traces-from-jaeger"
    args:
      serviceName: "user-service"
      startTimeMin: "2024-01-01T00:00:00Z"
      startTimeMax: "2024-01-01T23:59:59Z"
      operationName: "GetUser"
    group: "traces"
    description: "Find traces for user-service"
```

### 示例 6: 自定义时间范围

如果某个查询需要特定的时间范围，可以在查询中明确指定：

```yaml
queries:
  - tool_name: "get-events-from-ops"
    args:
      subject_pattern: "ops.clusters.>"
      start_time: "1758928888000"  # 时间戳格式
      page_size: "10"
    group: "events"
    description: "Get events for specific time range"
```

如果查询中已经指定了时间参数，程序不会覆盖它们。

## 时间范围配置

### 默认时间范围

程序会自动为没有指定时间参数的查询添加默认时间范围。默认值为最近 10 分钟（`10m`），可以在 `config.yaml` 中配置：

```yaml
query:
  default_time_range: "10m"  # 支持: "30s", "5m", "1h", "2d" 等格式
```

### 时间参数名称

默认使用 `start_time` 和 `end_time` 作为时间参数名称。如果你的 MCP 工具使用不同的参数名称，可以在配置中指定：

```yaml
query:
  time_param_names: "since"  # 单个参数
  # 或
  time_param_names: "from,to"  # 两个参数
```

### 时间格式

时间范围支持以下格式：
- `30s` - 30 秒
- `5m` - 5 分钟
- `1h` - 1 小时
- `2d` - 2 天

生成的时间戳使用 ISO 8601 格式（UTC 时间），例如：`2024-01-01T12:00:00Z`

## 通知功能

程序支持在生成 LLM 总结后发送通知到群聊。通知功能是可选的，默认关闭。

### 启用通知

1. **配置通知 URL**（环境变量）：
```bash
export NOTIFY_URL="https://your-webhook-url.com"
# 或
export NOTIFICATION_URL="https://your-webhook-url.com"
```

2. **运行程序时启用通知**：
```bash
python main.py --summary --notify
```

### 通知格式

通知使用 Markdown 格式发送，包含完整的 LLM 总结内容。通知会在以下情况发送：
- 同时使用 `--summary` 和 `--notify` 参数
- 总结生成成功
- `NOTIFY_URL` 环境变量已配置

### 通知失败处理

如果通知发送失败，程序会：
- 在控制台显示警告信息
- 继续正常完成程序执行
- 不会影响查询结果和总结的保存

### 使用示例

```bash
# 只生成总结，不发送通知（默认行为）
python main.py --summary

# 生成总结并发送通知
python main.py --summary --notify

# 如果只使用 --notify 但没有 --summary，会提示需要先生成总结
python main.py --notify  # 会提示需要 --summary
```

## 注意事项

1. 确保 MCP 服务器可访问且 token 有效
2. 确保 OpenAI API 配置正确且有足够的配额
3. 查询会按顺序执行，如果某个查询失败，会继续执行后续查询
4. 结果会保存到 `results.json`，包含所有查询结果和总结
5. 如果查询中已经指定了时间参数，程序不会覆盖它们
6. 时间范围基于当前 UTC 时间计算
7. 通知功能是可选的，未配置 `NOTIFY_URL` 时不会发送通知

## 许可证

（根据项目需要添加许可证信息）

