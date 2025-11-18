# 环境变量配置多个 MCP 服务器

## 概述

通过环境变量 `MCP_SERVERS_JSON` 可以配置多个 MCP 服务器，支持列表格式和字典格式。

## 方式 1: 列表格式（推荐）

列表格式与配置文件中的格式一致，更清晰易读：

```bash
export MCP_SERVERS_JSON='[
  {
    "name": "MCP1",
    "server_url": "https://mcp-server-1.com/mcp",
    "timeout": "30s",
    "token": "token-for-server-1",
    "default": true
  },
  {
    "name": "MCP2",
    "server_url": "https://mcp-server-2.com/mcp",
    "timeout": "30s",
    "token": "token-for-server-2"
  },
  {
    "name": "prometheus",
    "server_url": "https://prometheus-mcp.example.com/mcp",
    "timeout": "60s",
    "token": "prometheus-token"
  }
]'
```

### 单行格式（适合 Docker/K8s）

```bash
export MCP_SERVERS_JSON='[{"name":"MCP1","server_url":"https://mcp-server-1.com/mcp","timeout":"30s","token":"token1","default":true},{"name":"MCP2","server_url":"https://mcp-server-2.com/mcp","timeout":"30s","token":"token2"}]'
```


## 实际使用示例

### Docker 中使用

```dockerfile
# Dockerfile
ENV MCP_SERVERS_JSON='[{"name":"MCP1","server_url":"https://mcp1.example.com/mcp","timeout":"30s","token":"token1","default":true},{"name":"MCP2","server_url":"https://mcp2.example.com/mcp","timeout":"30s","token":"token2"}]'
```

### Docker Compose 中使用

```yaml
# docker-compose.yml
services:
  ops-agent:
    environment:
      - MCP_SERVERS_JSON=[{"name":"MCP1","server_url":"https://mcp1.example.com/mcp","timeout":"30s","token":"token1","default":true},{"name":"MCP2","server_url":"https://mcp2.example.com/mcp","timeout":"30s","token":"token2"}]
```

### Kubernetes 中使用

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

### 使用 Secret（推荐用于生产环境）

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

### .env 文件中使用

```bash
# .env
MCP_SERVERS_JSON='[
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
]'
```

### Shell 脚本中使用

```bash
#!/bin/bash

# 方式 1: 直接设置
export MCP_SERVERS_JSON='[{"name":"MCP1","server_url":"https://mcp1.example.com/mcp","timeout":"30s","token":"token1","default":true},{"name":"MCP2","server_url":"https://mcp2.example.com/mcp","timeout":"30s","token":"token2"}]'

# 方式 2: 从文件读取
export MCP_SERVERS_JSON=$(cat mcp-servers.json)

# 方式 3: 使用 heredoc（多行）
export MCP_SERVERS_JSON=$(cat <<EOF
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
EOF
)

# 运行应用
python main.py
```

## 配置字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | 是 | 服务器名称，用于在查询中引用 |
| `server_url` | string | 是 | MCP 服务器 URL |
| `token` | string | 是 | 认证 token |
| `timeout` | string | 否 | 超时时间，默认 "30s" |
| `default` | boolean | 否 | 是否作为默认服务器，默认 false（第一个服务器自动成为 default） |

**注意**：只支持列表格式，不再支持字典格式。

## 注意事项

1. **JSON 格式要求**：环境变量必须是有效的 JSON 格式，只支持列表格式
2. **引号转义**：在 shell 中使用时，注意单引号和双引号的转义
3. **默认服务器**：如果设置了 `default: true`，该服务器会成为默认服务器；否则第一个服务器自动成为默认服务器
4. **优先级**：环境变量 `MCP_SERVERS_JSON` 的优先级高于配置文件
5. **合并策略**：环境变量中的配置会与配置文件中的配置合并，环境变量优先

## 验证配置

可以通过以下方式验证配置是否正确加载：

```python
from ops_agent.config import ConfigLoader

config_loader = ConfigLoader()
config_loader.load_config()

# 列出所有配置的服务器
servers = config_loader.list_mcp_servers()
for name, config in servers.items():
    print(f"{name}: {config.server_url}")
```

## 常见问题

### Q: JSON 格式错误怎么办？

A: 确保 JSON 格式正确，可以使用在线 JSON 验证工具检查。注意：
- 字符串必须用双引号
- 最后一个对象后不能有逗号
- 布尔值使用 `true`/`false`（小写）

### Q: 如何在 Docker 中传递多行 JSON？

A: 使用单行格式，或者使用文件挂载：

```yaml
# docker-compose.yml
services:
  ops-agent:
    volumes:
      - ./mcp-servers.json:/app/mcp-servers.json:ro
    environment:
      - MCP_SERVERS_JSON_FILE=/app/mcp-servers.json
```

然后在代码中读取文件（需要额外实现）。

### Q: 环境变量和配置文件同时存在会怎样？

A: 环境变量会覆盖配置文件中的同名服务器配置，但不会完全替换。如果环境变量中定义了新的服务器，会添加到配置中。

