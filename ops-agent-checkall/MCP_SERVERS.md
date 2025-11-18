# 多 MCP 服务器配置说明

## 概述

现在支持配置多个 MCP 服务器，每个查询可以指定使用哪个服务器。

## 配置文件方式

在 `configs/config.yaml` 中配置多个服务器，使用列表格式并列配置：

```yaml
# MCP Server Configuration
# 支持配置多个 MCP 服务器，使用列表格式并列配置
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

## 环境变量方式

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

## 在查询中使用

在 `queries.yaml` 中，每个查询可以指定 `mcp_server` 字段：

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

## 配置优先级

1. **环境变量 `MCP_SERVERS_JSON`** - 最高优先级
2. **配置文件 `mcp_servers`（列表格式）** - 次优先级

## 默认服务器规则

- 如果配置了 `default: true`，该服务器会被设为默认服务器
- 如果没有显式标记，第一个服务器（列表中的第一个）会自动成为默认服务器
- 默认服务器可以通过名称或 `"default"` 来引用

## 示例配置

### 完整配置示例

```yaml
# configs/config.yaml
mcp_servers:
  - name: "MCP1"
    server_url: "https://ops-mcp-server.com/mcp"
    timeout: "30s"
    token: "default-token"
    default: true
  
  - name: "MCP2"
    server_url: "https://prometheus-mcp.example.com/mcp"
    timeout: "60s"
    token: "prometheus-token"
  
  - name: "MCP3"
    server_url: "https://es-mcp.example.com/mcp"
    timeout: "45s"
    token: "es-token"
```

### 查询文件示例

```yaml
queries:
  - tool_name: "query-metrics-from-prometheus"
    mcp_server: "MCP2"  # 使用名为 MCP2 的服务器
    args:
      query: "up"
    desc: "Prometheus 服务状态"
    formater: "metrics-formatter"
  
  - tool_name: "search-logs-from-elasticsearch"
    mcp_server: "MCP3"  # 使用名为 MCP3 的服务器
    args:
      index: "logs-*"
      body: '{"query": {...}}'
    desc: "搜索日志"
    formater: "atms-logs-formatter"
  
  - tool_name: "get-events"
    mcp_server: "MCP1"  # 或使用 "default"（指向 MCP1）
    args:
      subject: "ops.clusters.>"
    desc: "获取事件"
```

## 注意事项

1. 如果查询中指定的 `mcp_server` 不存在，会自动回退到 `default` 服务器
2. MCP 工具客户端会被缓存，同一个服务器只会创建一个客户端实例
3. 每个查询可以独立指定使用哪个服务器，实现灵活的多服务器查询
4. 配置只支持列表格式，使用 `name` 字段指定服务器名称
5. 服务器名称建议使用有意义的名称如 `MCP1`、`MCP2`、`prometheus` 等

