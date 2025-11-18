# Ops Agent CheckAll HTTP API 文档

## 启动服务

### 使用 Docker Compose

```bash
docker-compose up -d
```

### 使用 Docker

```bash
docker build -t ops-agent-checkall:latest .
docker run -d -p 8080:8080 \
  -v $(pwd)/configs:/app/configs:ro \
  -v $(pwd)/queries.yaml:/app/queries.yaml:ro \
  -v $(pwd)/logs:/app/logs \
  -e MCP_SERVERURL=your-mcp-server-url \
  -e MCP_TOKEN=your-mcp-token \
  ops-agent-checkall:latest
```

### 直接运行

```bash
python server.py
```

服务默认运行在 `http://0.0.0.0:8080`

## API 端点

### 1. 健康检查

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

### 2. 触发任务

**GET** `/trigger`

触发一个任务执行。

**请求示例：**
```
GET /trigger?queries=queries.yaml&summary=true
```

**查询参数说明：**
- `config`: 配置文件路径（可选）
- `queries`: 查询文件路径（可选）
- `verbose`: 是否详细日志（可选，true/false，默认 false）
- `summary`: 是否生成 LLM 总结（可选，true/false，默认 false，不总结）

**响应示例（成功）：**
```json
{
  "success": true,
  "output": "查询结果内容...",
  "summary": "AI 总结内容（如果启用了总结）"
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

### 3. 查询任务状态

**GET** `/status/<task_id>`

查询指定任务的状态和结果。

**响应示例（运行中）：**
```json
{
  "success": true,
  "task_id": "task_20240101_120000_123456",
  "status": "running",
  "start_time": "2024-01-01T12:00:00",
  "message": "任务执行中..."
}
```

**响应示例（已完成）：**
```json
{
  "success": true,
  "task_id": "task_20240101_120000_123456",
  "status": "completed",
  "start_time": "2024-01-01T12:00:00",
  "end_time": "2024-01-01T12:05:00",
  "output": "查询结果...",
  "summary": "AI 总结..."
}
```

**响应示例（失败）：**
```json
{
  "success": true,
  "task_id": "task_20240101_120000_123456",
  "status": "failed",
  "start_time": "2024-01-01T12:00:00",
  "end_time": "2024-01-01T12:01:00",
  "error": "错误信息"
}
```

**状态码：**
- `200 OK`: 查询成功
- `404 Not Found`: 任务不存在

### 4. 列出所有任务

**GET** `/tasks`

列出所有任务及其状态。

**响应示例：**
```json
{
  "success": true,
  "tasks": [
    {
      "task_id": "task_20240101_120000_123456",
      "status": "completed",
      "start_time": "2024-01-01T12:00:00",
      "end_time": "2024-01-01T12:05:00"
    },
    {
      "task_id": "task_20240101_110000_123456",
      "status": "running",
      "start_time": "2024-01-01T11:00:00"
    }
  ],
  "total": 2
}
```

## 使用示例

### 使用 curl 触发任务

```bash
# 使用 GET 请求触发任务（默认不总结，直接返回结果）
curl "http://localhost:8080/trigger?queries=queries.yaml"

# 需要总结时，添加 summary=true
curl "http://localhost:8080/trigger?queries=queries.yaml&summary=true"

# 健康检查
curl http://localhost:8080/health
```

### 使用 Python requests

```python
import requests

# 触发任务（默认不总结，直接返回结果）
response = requests.get('http://localhost:8080/trigger', params={
    'queries': 'queries.yaml'
})

result = response.json()
if result['success']:
    print(f"Output: {result.get('output', '')}")
    if result.get('summary'):
        print(f"Summary: {result['summary']}")
else:
    print(f"Error: {result.get('error', '')}")

# 需要总结时
response = requests.get('http://localhost:8080/trigger', params={
    'queries': 'queries.yaml',
    'summary': 'true'
})

result = response.json()
if result['success']:
    print(result.get('output', ''))
    if result.get('summary'):
        print(f"\n## AI 总结\n{result['summary']}")
```

## 环境变量

服务支持以下环境变量：

- `PORT`: HTTP 服务端口（默认：8080）
- `HOST`: HTTP 服务绑定地址（默认：0.0.0.0）
- `MCP_SERVERURL`: MCP 服务器 URL
- `MCP_TOKEN`: MCP 认证令牌
- `OPENAI_API_KEY`: OpenAI API 密钥（用于总结功能）
- `OPENAI_API_HOST`: OpenAI API 主机（默认：https://api.openai.com/v1）
- `OPENAI_MODEL`: OpenAI 模型名称（默认：gpt-4）

## 注意事项

1. 任务同步执行，接口会等待任务完成后再返回结果
2. 任务状态保存在内存中，服务重启后会丢失
3. 如果任务执行时间较长，建议设置合适的 HTTP 超时时间

