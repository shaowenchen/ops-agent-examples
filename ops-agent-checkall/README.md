# Ops Agent CheckAll

一个用于执行一系列 MCP 数据查询的工具。

## 功能特性

- 🔍 **批量 MCP 查询**: 支持执行多个 MCP 查询
- 📊 **结果可视化**: 使用 Rich 库提供美观的控制台输出
- ⚙️ **灵活配置**: 支持配置文件和环境变量
- 📝 **结果保存**: 自动保存查询结果到 JSON 文件
- 🛠️ **多模块支持**: 支持 SOPS、Events、Metrics、Logs、Traces 等多个运维模块
- 🌐 **HTTP API**: 提供 HTTP 服务接口，支持通过 API 触发任务
- 🔌 **多 MCP 服务器**: 支持配置多个 MCP 服务器，每个查询可指定使用哪个服务器

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

编辑 `configs/config.yaml` 文件，配置 MCP 服务器：

```yaml
# Ops Agent CheckAll Configuration

# MCP Server Configuration
# 支持配置多个 MCP 服务器，使用列表格式并列配置
# 第一个服务器默认为 default，或者可以显式指定 default: true
mcp_servers:
  - name: "MCP1"
    # MCP server URL
    server_url: "https://your-mcp-server-url.com/mcp"
    
    # Request timeout
    timeout: "30s"
    
    # Authentication token
    token: "your-mcp-token-here"
    
    # 是否作为默认服务器（可选，第一个服务器默认为 default）
    default: true
  
  # 可以添加更多服务器配置
  # - name: "MCP2"
  #   server_url: "https://another-mcp-server.com/mcp"
  #   timeout: "30s"
  #   token: "another-token"
  #   default: false
```

### 2. 多 MCP 服务器配置

#### 配置文件方式

在 `configs/config.yaml` 中配置多个服务器，使用列表格式并列配置：

```yaml
mcp_servers:
  - name: "MCP1"
    server_url: "https://mcp-server-1.com/mcp"
    timeout: "30s"
    token: "token-for-server-1"
    default: true  # 可选，标记为默认服务器（第一个服务器默认为 default）
  
  - name: "MCP2"
    server_url: "https://mcp-server-2.com/mcp"
    timeout: "30s"
    token: "token-for-server-2"
  
  - name: "prometheus"
    server_url: "https://prometheus-mcp-server.com/mcp"
    timeout: "60s"
    token: "prometheus-token"
```

#### 环境变量方式

通过 `MCP_SERVERS_JSON` 环境变量配置多个服务器（只支持列表格式）：

```bash
export MCP_SERVERS_JSON='[
  {
    "name": "MCP1",
    "server_url": "https://mcp-server-1.com/mcp",
    "timeout": "30s",
    "token": "token-1",
    "default": true
  },
  {
    "name": "MCP2",
    "server_url": "https://mcp-server-2.com/mcp",
    "timeout": "30s",
    "token": "token-2"
  }
]'
```

**单行格式（适合 Docker/K8s）：**

```bash
export MCP_SERVERS_JSON='[{"name":"MCP1","server_url":"https://mcp-server-1.com/mcp","timeout":"30s","token":"token1","default":true},{"name":"MCP2","server_url":"https://mcp-server-2.com/mcp","timeout":"30s","token":"token2"}]'
```

#### 在查询中使用

在 `default.yaml` 中，每个查询可以指定 `mcp_server` 字段：

```yaml
queries:
  - tool_name: "query-metrics-from-prometheus"
    mcp_server: "prometheus"  # 使用名为 "prometheus" 的服务器
    args:
      query: "up"
    desc: "检查 Prometheus 服务状态"
    formater: "metrics-formatter"
  
  - tool_name: "search-logs-from-elasticsearch"
    mcp_server: "default"  # 使用默认服务器
    args:
      index: "logs-*"
      body: '{"query": {...}}'
    desc: "搜索日志"
    formater: "atms-logs-formatter"
  
  - tool_name: "query-metrics-from-prometheus"
    # 如果不指定 mcp_server，默认使用 "default" 服务器
    args:
      query: "node_cpu_seconds_total"
    desc: "查询 CPU 指标"
    formater: "metrics-formatter"
```

#### 默认服务器规则

- 如果配置了 `default: true`，该服务器会被设为默认服务器
- 如果没有显式标记，第一个服务器（列表中的第一个）会自动成为默认服务器
- 默认服务器可以通过名称或 `"default"` 来引用

#### 配置优先级

1. **环境变量 `MCP_SERVERS_JSON`** - 最高优先级
2. **配置文件 `mcp_servers`（列表格式）** - 次优先级

#### 注意事项

1. 如果查询中指定的 `mcp_server` 不存在，会自动回退到 `default` 服务器
2. MCP 工具客户端会被缓存，同一个服务器只会创建一个客户端实例
3. 每个查询可以独立指定使用哪个服务器，实现灵活的多服务器查询
4. 配置只支持列表格式，使用 `name` 字段指定服务器名称
5. 服务器名称建议使用有意义的名称如 `MCP1`、`MCP2`、`prometheus` 等

### 3. 环境变量配置

#### 基本环境变量

```bash
# MCP 服务器配置（多服务器，列表格式）
export MCP_SERVERS_JSON='[{"name":"MCP1","server_url":"https://mcp-server-1.com/mcp","timeout":"30s","token":"token1","default":true}]'


```

#### 环境变量使用场景

**Docker 中使用：**

```dockerfile
# Dockerfile
ENV MCP_SERVERS_JSON='[{"name":"MCP1","server_url":"https://mcp1.example.com/mcp","timeout":"30s","token":"token1","default":true},{"name":"MCP2","server_url":"https://mcp2.example.com/mcp","timeout":"30s","token":"token2"}]'
```

**Docker Compose 中使用：**

```yaml
# docker-compose.yml
services:
  ops-agent:
    environment:
      - MCP_SERVERS_JSON=[{"name":"MCP1","server_url":"https://mcp1.example.com/mcp","timeout":"30s","token":"token1","default":true},{"name":"MCP2","server_url":"https://mcp2.example.com/mcp","timeout":"30s","token":"token2"}]
```

**Kubernetes 中使用：**

```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ops-agent
spec:
  template:
    spec:
      containers:
      - name: ops-agent
        env:
        - name: MCP_SERVERS_JSON
          value: '[{"name":"MCP1","server_url":"https://mcp1.example.com/mcp","timeout":"30s","token":"token1","default":true},{"name":"MCP2","server_url":"https://mcp2.example.com/mcp","timeout":"30s","token":"token2"}]'
```

**使用 Secret（推荐用于生产环境）：**

```yaml
# k8s-secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: mcp-servers-config
type: Opaque
stringData:
  MCP_SERVERS_JSON: |
    [
      {
        "name": "MCP1",
        "server_url": "https://mcp1.example.com/mcp",
        "timeout": "30s",
        "token": "token1",
        "default": true
      },
      {
        "name": "MCP2",
        "server_url": "https://mcp2.example.com/mcp",
        "timeout": "30s",
        "token": "token2"
      }
    ]

# 在 Deployment 中引用
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      containers:
      - name: ops-agent
        env:
        - name: MCP_SERVERS_JSON
          valueFrom:
            secretKeyRef:
              name: mcp-servers-config
              key: MCP_SERVERS_JSON
```

**配置字段说明：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | 是 | 服务器名称，用于在查询中引用 |
| `server_url` | string | 是 | MCP 服务器 URL |
| `token` | string | 是 | 认证 token |
| `timeout` | string | 否 | 超时时间，默认 "30s" |
| `default` | boolean | 否 | 是否作为默认服务器，默认 false（第一个服务器自动成为 default） |

**注意事项：**

1. **JSON 格式要求**：环境变量必须是有效的 JSON 格式，只支持列表格式
2. **引号转义**：在 shell 中使用时，注意单引号和双引号的转义
3. **默认服务器**：如果设置了 `default: true`，该服务器会成为默认服务器；否则第一个服务器自动成为默认服务器
4. **优先级**：环境变量 `MCP_SERVERS_JSON` 的优先级高于配置文件
5. **合并策略**：环境变量中的配置会与配置文件中的配置合并，环境变量优先

### 4. 查询配置

编辑 `default.yaml` 文件，定义要执行的 MCP 查询。每个查询可以包含：

- `tool_name`: MCP 工具名称（必需）
- `mcp_server`: MCP 服务器名称（可选，默认使用 "default" 服务器）
- `args`: 工具参数（可选）
- `desc`: 查询描述（可选），用于标识查询目的，例如："最近10分钟 CPU使用率超过50%的节点"
- `formater`: 格式化器名称（可选），用于指定结果格式化方式

```yaml
queries:
  - tool_name: "get-events-from-ops"
    mcp_server: "default"
    args:
      subject_pattern: "ops.clusters.>"
      limit: "5"
    desc: "获取所有集群的事件信息"
    formater: "events-formatter"
  
  - tool_name: "query-metrics-from-prometheus"
    mcp_server: "prometheus"
    args:
      query: "up"
    desc: "查询 Prometheus 服务状态"
    formater: "metrics-formatter"
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
python main.py -q /path/to/default.yaml
```

### 详细日志

```bash
python main.py --verbose
```

## HTTP API 服务

### 启动服务

**使用 Docker：**

```bash
docker build -t ops-agent:checkall .
docker run -d -p 8080:8080 \
  -v $(pwd)/configs:/app/configs:ro \
  -v $(pwd)/default.yaml:/app/default.yaml:ro \
  -e MCP_SERVERS_JSON='[{"name":"MCP1","server_url":"...","token":"..."}]' \
  ops-agent:checkall
```

**直接运行：**

```bash
python server.py
```

服务默认运行在 `http://0.0.0.0:8080`

### API 端点

#### 1. 健康检查

**GET** `/health`

检查服务是否正常运行。

**响应示例：**
```json
{
  "status": "healthy",
  "service": "ops-agent-checkall",
  "timestamp": "2024-01-01T12:00:00"
}
```

#### 2. 触发任务

**GET** `/trigger`

触发一个任务执行。

**请求示例：**
```
GET /trigger?queries=default.yaml
```

**查询参数说明：**
- `config`: 配置文件路径（可选）
- `queries`: 查询文件路径（可选，默认为 `default.yaml`）
- `verbose`: 是否详细日志（可选，true/false，默认 false）

**响应示例（成功）：**
```json
{
  "success": true,
  "output": "查询结果内容..."
}
```

**响应示例（失败）：**
```json
{
  "success": false,
  "error": "错误信息"
}
```

**状态码：**
- `200 OK`: 任务执行成功并返回结果
- `400 Bad Request`: 请求参数错误（如找不到查询文件）
- `500 Internal Server Error`: 任务执行失败

### API 使用示例

**使用 curl 触发任务：**

```bash
# 使用 GET 请求触发任务
curl "http://localhost:8080/trigger?queries=default.yaml"

# 健康检查
curl http://localhost:8080/health
```

**使用 Python requests：**

```python
import requests

# 触发任务
response = requests.get('http://localhost:8080/trigger', params={
    'queries': 'default.yaml'
})

result = response.json()
if result['success']:
    print(result.get('output', ''))
else:
    print(f"Error: {result.get('error', '')}")
```

**环境变量：**

服务支持以下环境变量：

- `PORT`: HTTP 服务端口（默认：8080）
- `HOST`: HTTP 服务绑定地址（默认：0.0.0.0）
- `MCP_SERVERS_JSON`: MCP 服务器配置（JSON 格式）

**注意事项：**

1. 任务同步执行，接口会等待任务完成后再返回结果
2. 如果任务执行时间较长，建议设置合适的 HTTP 超时时间

## 输出

程序会：

1. 在控制台显示每个查询的执行状态
2. 将结果保存到 `results.json` 文件

## 项目结构

```
ops-agent-checkall/
├── main.py                 # 主程序入口
├── server.py               # HTTP API 服务
├── build.sh                # 构建脚本
├── Dockerfile              # Docker 镜像构建文件
├── configs/
│   └── config.yaml         # 配置文件
├── default.yaml            # 默认查询配置文件
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
    │   └── formatters.py          # 结果格式化器
    ├── tools/              # 工具模块
    │   ├── __init__.py
    │   └── mcp_tool.py     # MCP 工具封装
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

### 示例 1: 基本查询

```yaml
queries:
  - tool_name: "get-events-from-ops"
    mcp_server: "default"
    args:
      subject_pattern: "ops.clusters.>"
      page_size: "10"
    desc: "获取所有集群的事件信息"
```

### 示例 2: 多模块综合查询

```yaml
queries:
  # SOPS 模块
  - tool_name: "list-sops-from-ops"
    mcp_server: "default"
    args: {}
    desc: "列出所有可用的 SOPS 操作流程"
  
  # Events 模块
  - tool_name: "get-events-from-ops"
    mcp_server: "default"
    args:
      subject_pattern: "ops.clusters.*.nodes.*.event"
      page_size: "50"
    desc: "获取所有节点的 Kubernetes 事件"
  
  # Logs 模块
  - tool_name: "search-logs-from-elasticsearch"
    mcp_server: "default"
    args:
      index: "logs-*"
      body: '{"query": {"match": {"message": "error"}}}'
    desc: "搜索最近一段时间内的错误日志"
    formater: "atms-logs-formatter"
  
  # Metrics 模块
  - tool_name: "query-metrics-from-prometheus"
    mcp_server: "prometheus"
    args:
      query: "up"
    desc: "查询 Prometheus 中所有服务的运行状态"
    formater: "metrics-formatter"
  
  # Traces 模块
  - tool_name: "get-services-from-jaeger"
    mcp_server: "default"
    args: {}
    desc: "获取 Jaeger 中所有服务名称"
```

### 示例 3: 多 MCP 服务器查询

```yaml
queries:
  # 使用 prometheus 服务器
  - tool_name: "query-metrics-from-prometheus"
    mcp_server: "prometheus"
    args:
      query: "cpu_usage_percent > 80"
    desc: "查询 CPU 使用率超过 80% 的节点"
    formater: "metrics-formatter"
  
  # 使用默认服务器
  - tool_name: "search-logs-from-elasticsearch"
    mcp_server: "default"
    args:
      index: "logs-*"
      body: '{"query": {"match": {"level": "ERROR"}}}'
    desc: "搜索错误日志"
    formater: "atms-logs-formatter"
  
  # 不指定 mcp_server，使用默认服务器
  - tool_name: "get-events-from-ops"
    args:
      subject_pattern: "ops.clusters.>"
    desc: "获取集群事件"
```

### 示例 4: Prometheus 指标查询

```yaml
queries:
  # 即时查询
  - tool_name: "query-metrics-from-prometheus"
    mcp_server: "prometheus"
    args:
      query: "cpu_usage_percent"
    desc: "查询当前 CPU 使用率"
    formater: "metrics-formatter"
  
  # 范围查询
  - tool_name: "query-metrics-range-from-prometheus"
    mcp_server: "prometheus"
    args:
      query: "rate(http_requests_total[5m])"
      time_range: "1h"
      step: "60s"
    desc: "查询 HTTP 请求速率（1小时范围）"
    formater: "metrics-formatter"
```

### 示例 5: 自定义时间范围

如果某个查询需要特定的时间范围，可以在查询中明确指定：

```yaml
queries:
  - tool_name: "get-events-from-ops"
    mcp_server: "default"
    args:
      subject_pattern: "ops.clusters.>"
      start_time: "1758928888000"  # 时间戳格式
      page_size: "10"
    desc: "获取指定时间范围的事件"
```

## 注意事项

1. 确保 MCP 服务器可访问且 token 有效
2. 查询会按顺序执行，如果某个查询失败，会继续执行后续查询
3. 结果会保存到 `results.json`，包含所有查询结果
4. 多 MCP 服务器配置时，确保每个服务器名称唯一
5. 如果查询中指定的 `mcp_server` 不存在，会自动回退到 `default` 服务器

## 许可证

（根据项目需要添加许可证信息）
