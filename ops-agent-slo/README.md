# Ops Agent SLO

一个用于服务级别目标（SLO）监控和分析的工具，通过代码编排各个检查模块，传递和复用参数，调用 MCP 或 LLM 服务。

## 功能特性

- 🔧 **模块化设计**: 每个检查模块独立目录，易于扩展和维护
- 🔄 **参数传递和复用**: 模块间通过共享上下文传递参数和数据
- 🎯 **工作流编排**: 支持复杂的工作流定义，包括条件执行和结果复用
- 🔌 **MCP 集成**: 支持调用多个 MCP 服务器
- 🤖 **LLM 支持**: 完整的 LLM 交互模块，支持 WPS AI Gateway 和其他 LLM 提供商，可用于智能分析和决策
- 🌐 **HTTP API**: 提供 HTTP 服务接口，支持通过 API 触发工作流
- 📊 **结果可视化**: 使用 Rich 库提供美观的控制台输出

## 项目结构

```
ops-agent-slo/
├── main.py                 # 主程序入口（执行 run.py）
├── run.py                  # 主要代码区域，直接编写模块组合代码
├── server.py               # HTTP API 服务
├── Dockerfile              # Docker 镜像构建文件
├── .dockerignore           # Docker 忽略文件
├── configs/
│   └── config.yaml        # 配置文件
├── requirements.txt        # Python 依赖
├── README.md              # 说明文档
└── ops_agent/
    ├── __init__.py
    ├── config/             # 配置模块
    │   ├── __init__.py
    │   └── config_loader.py
    ├── core/               # 核心模块
    │   ├── __init__.py
    │   ├── orchestrator.py # 编排器
    │   └── base_module.py  # 模块基类
    ├── modules/            # 检查模块
    │   ├── __init__.py
    │   ├── upstream_query/ # Upstream 查询模块
    │   │   ├── __init__.py
    │   │   └── module.py
    │   └── error_log_query/ # 异常日志查询模块
    │       ├── __init__.py
    │       └── module.py
    │   └── llm_chat/         # LLM 交互模块
    │       ├── __init__.py
    │       └── module.py
    ├── tools/              # 工具模块
    │   ├── __init__.py
    │   └── mcp_tool.py     # MCP 工具封装
    └── utils/              # 工具模块
        ├── __init__.py
        └── logging.py
```

## 安装

1. 进入项目目录：
```bash
cd ops-agent-slo
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

## 配置

### 1. 配置文件

编辑 `configs/config.yaml` 文件，配置 MCP 服务器和 LLM：

```yaml
# Ops Agent SLO Configuration

# MCP Server Configuration
mcp_servers:
  - name: "MCP1"
    server_url: "https://your-mcp-server-url.com/mcp"
    timeout: "30s"
    token: "your-mcp-token-here"
    default: true

# LLM Configuration (optional)
llm:
  token: "your-llm-token-here"
  url: "http://your-llm-gateway.com/api/v2/llm/chat"
  provider: "azure"
  model: "gpt-4o"
  temperature: 0
  headers_json: '{"CUSTOM-HEADER-NAME-1":"value1","CUSTOM-HEADER-NAME-2":"value2","CUSTOM-HEADER-NAME-3":"value3"}'
```

### 1.1 环境变量配置

环境变量会覆盖配置文件中的设置。支持的环境变量：

**LLM 相关：**
- `LLM_TOKEN`: LLM API token（覆盖 config 中的 `llm.token`）
- `LLM_URL`: LLM API URL（覆盖 config 中的 `llm.url`）
- `LLM_HEADERS_JSON`: LLM 请求头（JSON 字符串格式，覆盖 config 中的 `llm.headers_json`）

**配置示例：**

```bash
# 设置 LLM token
export LLM_TOKEN="your-llm-token"

# 设置 LLM URL
export LLM_URL="http://your-llm-gateway.com/api/v2/llm/chat"

# 设置 LLM headers（JSON 字符串格式）
export LLM_HEADERS_JSON='{"CUSTOM-HEADER-NAME-1":"value1","CUSTOM-HEADER-NAME-2":"value2","CUSTOM-HEADER-NAME-3":"value3"}'
```

**注意：** `LLM_HEADERS_JSON` 必须是有效的 JSON 字符串。如果包含特殊字符，建议使用单引号包裹整个 JSON 字符串。

**Docker 中使用：**

```bash
docker run -e LLM_TOKEN="your-token" \
  -e LLM_URL="http://your-llm-gateway.com/api/v2/llm/chat" \
  -e LLM_HEADERS_JSON='{"CUSTOM-HEADER-NAME-1":"value1","CUSTOM-HEADER-NAME-2":"value2","CUSTOM-HEADER-NAME-3":"value3"}' \
  ops-agent-slo:latest
```

**Docker Compose 中使用：**

```yaml
services:
  ops-agent-slo:
    environment:
      - LLM_TOKEN=your-llm-token
      - LLM_URL=http://your-llm-gateway.com/api/v2/llm/chat
      - LLM_HEADERS_JSON={"CUSTOM-HEADER-NAME-1":"value1","CUSTOM-HEADER-NAME-2":"value2","CUSTOM-HEADER-NAME-3":"value3"}
```

### 2. 编写执行代码

**直接编辑 `run.py` 文件来组合和执行模块**，使用 Python 代码：

```python
def main():
    # 初始化配置和编排器
    config_loader = ConfigLoader()
    config_loader.load_config()
    
    orchestrator = Orchestrator(config_loader)
    
    # 注册模块
    orchestrator.register_module(UpstreamQueryModule())
    orchestrator.register_module(ErrorLogQueryModule())
    
    # 直接调用模块并组合
    # 查询 qingqiu 服务的 upstream 信息
    upstream_result = orchestrator.execute_module(
        "upstream_query",
        params={
            "service_name": "qingqiu",
            "mcp_server": "default"
        }
    )
    
    # 使用上一个模块的结果，查询异常日志
    service_name = orchestrator.get_context('last_queried_service', 'qingqiu')
    
    error_log_result = orchestrator.execute_module(
        "error_log_query",
        params={
            "service_name": service_name,
            "index": "logs-*",
            "time_range": "1h"
        }
    )
    
    # 可以添加更多逻辑，如条件判断、循环等
    if upstream_result.status.value == "success":
        # 处理结果...
        pass
```

这种方式完全使用 Python 代码，可以自由组合模块、传递参数、复用结果，支持所有 Python 功能。

## 使用方法

### 基本用法

直接运行主程序，它会执行 `run.py` 中定义的模块组合逻辑：

```bash
python main.py
```

或者直接运行：

```bash
python run.py
```

### 默认执行流程

默认情况下，`run.py` 会执行以下流程：

1. **查询 Upstream 信息** - 查询指定服务的 upstream 配置
2. **查询错误日志** - 基于服务名称查询异常日志
3. **LLM 智能分析** - 使用 LLM 模块分析前面两个模块的结果，生成分析报告

### 执行示例输出

```
Upstream query result: success
Service: qingqiu
Upstreams found: 5

Error log query result: success
Total errors: 12

================================================================================
调用 LLM 模块进行分析...
================================================================================

✅ LLM 分析结果:
--------------------------------------------------------------------------------
根据监控数据分析，服务 qingqiu 当前状态如下：

1. Upstream 配置正常，共发现 5 个 upstream 节点
2. 发现 12 条错误日志，建议进一步排查...

Token 使用情况: 256 tokens
```

### 编辑执行代码

直接编辑 `run.py` 文件，在 `main()` 函数中编写你的代码来组合模块：

```python
def main():
    # 初始化配置和编排器
    config_loader = ConfigLoader()
    config_loader.load_config()
    
    orchestrator = Orchestrator(config_loader)
    
    # 注册模块
    orchestrator.register_module(UpstreamQueryModule())
    orchestrator.register_module(ErrorLogQueryModule())
    orchestrator.register_module(LLMChatModule())
    
    # 直接调用模块并组合
    # 你的代码...
```

### 详细日志

```bash
python main.py --verbose
```

## Docker 部署

### 构建镜像

```bash
docker build -t ops-agent-slo:latest .
```

### 运行容器

```bash
# 运行 HTTP 服务
docker run -d \
  -p 8080:8080 \
  -v $(pwd)/configs:/app/configs:ro \
  -v $(pwd)/run.py:/app/run.py:rw \
  -e MCP_SERVERS_JSON='[{"name":"MCP1","server_url":"...","token":"..."}]' \
  -e LLM_TOKEN="your-llm-token" \
  -e LLM_URL="http://your-llm-gateway.com/api/v2/llm/chat" \
  -e LLM_HEADERS_JSON='{"CUSTOM-HEADER-NAME-1":"value1","CUSTOM-HEADER-NAME-2":"value2","CUSTOM-HEADER-NAME-3":"value3"}' \
  ops-agent-slo:latest

# 或者直接执行 main.py（一次性执行）
docker run --rm \
  -v $(pwd)/configs:/app/configs:ro \
  -v $(pwd)/run.py:/app/run.py:rw \
  -e MCP_SERVERS_JSON='[{"name":"MCP1","server_url":"...","token":"..."}]' \
  -e LLM_TOKEN="your-llm-token" \
  -e LLM_HEADERS_JSON='{"CUSTOM-HEADER-NAME-1":"value1","CUSTOM-HEADER-NAME-2":"value2","CUSTOM-HEADER-NAME-3":"value3"}' \
  ops-agent-slo:latest python main.py
```

### 使用 Docker Compose

创建 `docker-compose.yml`:

```yaml
version: '3.8'

services:
  ops-agent-slo:
    build: .
    ports:
      - "8080:8080"
    volumes:
      - ./configs:/app/configs:ro
      - ./run.py:/app/run.py:rw
    environment:
      - MCP_SERVERS_JSON=[{"name":"MCP1","server_url":"...","token":"..."}]
      - LLM_TOKEN=your-llm-token
      - LLM_URL=http://your-llm-gateway.com/api/v2/llm/chat
      - LLM_HEADERS_JSON={"CUSTOM-HEADER-NAME-1":"value1","CUSTOM-HEADER-NAME-2":"value2","CUSTOM-HEADER-NAME-3":"value3"}
    restart: unless-stopped
```

运行：
```bash
docker-compose up -d
```

## HTTP API 服务

### 启动服务

```bash
python server.py
```

服务默认运行在 `http://0.0.0.0:8080`

### API 端点

#### 1. 健康检查

**GET** `/health`

检查服务是否正常运行。

#### 2. 触发工作流

**GET/POST** `/trigger`

触发执行分析流程。支持两种模式：
1. 如果提供 `data` 和 `key` 参数，执行完整的分析流程
2. 如果不提供，执行 `run.py` 中的默认代码

**请求示例（GET）：**
```
GET /trigger?verbose=false
```

**请求示例（POST - 带 data 和 key）：**
```json
{
  "data": "分析内容或数据",
  "key": "标识键，用于区分不同的分析类型",
  "verbose": false
}
```

**请求示例（POST - 不带参数，执行 run.py）：**
```json
{
  "verbose": false
}
```

**参数说明：**
- `data` (可选): 分析内容或数据，会传递给 LLM 进行分析
- `key` (可选): 标识键，用于区分不同的分析类型
  - 如果 `key` 以 `service_` 开头，会自动提取服务名称并执行完整的监控分析流程
  - 其他 `key` 值会直接使用 LLM 分析 `data` 内容
- `verbose` (可选): 是否启用详细日志，默认 false

**响应示例（带 data 和 key）：**
```json
{
  "success": true,
  "key": "service_qingqiu",
  "results": {
    "upstream": {
      "module_name": "upstream_query",
      "status": "success",
      "data": {...}
    },
    "error_log": {
      "module_name": "error_log_query",
      "status": "success",
      "data": {...}
    },
    "llm_analysis": {
      "module_name": "llm_chat",
      "status": "success",
      "data": {
        "output": "分析结果...",
        "usage": {...}
      }
    }
  },
  "context": {...}
}
```

**响应示例（不带参数）：**
```json
{
  "success": true,
  "results": {
    "output": "执行输出..."
  },
  "context": {...}
}
```

**分析流程（当提供 data 和 key 时）：**
1. 如果 `key` 以 `service_` 开头：
   - 提取服务名称（从 key 中，如 `service_qingqiu` → `qingqiu`）
   - 执行 upstream 查询
   - 执行错误日志查询
   - 将查询结果和接收到的 `data` 一起传递给 LLM 进行综合分析
2. 其他情况：
   - 直接使用 LLM 分析接收到的 `data` 内容

**使用示例：**
```bash
# 服务分析（完整流程）
curl -X POST http://localhost:8080/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "data": "请分析服务 qingqiu 的健康状况",
    "key": "service_qingqiu"
  }'

# 直接 LLM 分析
curl -X POST http://localhost:8080/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "data": "分析这段日志数据...",
    "key": "log_analysis"
  }'

# 执行 run.py 默认流程
curl -X POST http://localhost:8080/trigger \
  -H "Content-Type: application/json" \
  -d '{}'
```

## 模块开发

### 创建新模块

1. 在 `ops_agent/modules/` 下创建新目录，例如 `my_module/`
2. 创建 `__init__.py` 和 `module.py`
3. 继承 `BaseModule` 并实现 `execute()` 方法

示例：

```python
from ...core.base_module import BaseModule, ModuleResult, ModuleStatus
from ...utils.logging import get_logger

logger = get_logger(__name__)

class MyModule(BaseModule):
    def __init__(self, mcp_tool=None, context=None):
        super().__init__("my_module", mcp_tool, context)
    
    def execute(self, params):
        # 获取参数
        service_name = params.get('service_name')
        
        # 从上下文获取值
        previous_result = self.get_context_value('upstream_query_result')
        
        # 调用 MCP 工具
        result = self.call_mcp_tool(
            tool_name="some-tool",
            args={"key": "value"},
            server_name="default"
        )
        
        # 设置上下文值供其他模块使用
        self.set_context_value('my_result', result)
        
        # 返回结果
        return ModuleResult(
            module_name=self.name,
            status=ModuleStatus.SUCCESS,
            data={"result": result}
        )
```

4. 在 `ops_agent/modules/__init__.py` 中注册模块

5. 在 `run.py` 中直接调用和使用

## 工作流特性

### 参数传递和复用

模块可以通过共享上下文传递参数和复用结果：

```python
# 执行第一个模块
upstream_result = orchestrator.execute_module(
    "upstream_query",
    params={"service_name": "qingqiu"}
)
# 结果会自动保存到上下文: upstream_query_result

# 从上下文获取服务名称
service_name = orchestrator.get_context('last_queried_service', 'qingqiu')

# 使用上一个模块的结果执行第二个模块
error_log_result = orchestrator.execute_module(
    "error_log_query",
    params={"service_name": service_name}
)
```

### 条件执行

可以使用 Python 的条件语句：

```python
upstream_result = orchestrator.execute_module(
    "upstream_query",
    params={"service_name": "qingqiu"}
)

# 仅在成功时执行
if upstream_result.status.value == "success":
    error_log_result = orchestrator.execute_module(
        "error_log_query",
        params={"service_name": "qingqiu"}
    )
```

### 使用 Python 功能

由于是纯 Python 代码，你可以使用所有 Python 功能：

```python
# 从环境变量读取
service_name = os.environ.get('SERVICE_NAME', 'qingqiu')

# 循环处理多个服务
services = ['qingqiu', 'service2', 'service3']
for service in services:
    result = orchestrator.execute_module(
        "upstream_query",
        params={"service_name": service}
    )
    # 处理结果...
    if result.status.value == "success":
        # 继续处理...
        pass

# 使用函数封装逻辑
def check_service(service_name):
    upstream_result = orchestrator.execute_module(
        "upstream_query",
        params={"service_name": service_name}
    )
    if upstream_result.status.value == "success":
        return orchestrator.execute_module(
            "error_log_query",
            params={"service_name": service_name}
        )
    return None
```

### 上下文访问

模块可以通过 `self.get_context_value()` 和 `self.set_context_value()` 访问和设置上下文。

## 示例模块

### 1. Upstream Query Module

查询服务的 upstream 信息。

**参数：**
- `service_name`: 服务名称（必需）
- `mcp_server`: MCP 服务器名称（可选）
- `tool_name`: MCP 工具名称（可选）
- `additional_args`: 额外参数（可选）

### 2. Error Log Query Module

查询异常日志。

**参数：**
- `service_name`: 服务名称（可选，可从上下文获取）
- `index`: Elasticsearch 索引（可选）
- `query_body`: 自定义查询体（可选）
- `time_range`: 时间范围（可选）
- `use_context`: 是否使用上下文中的 service_name（可选）

### 3. LLM Chat Module

与 LLM 模型交互，支持 WPS AI Gateway 和其他 LLM 提供商。可用于智能分析、决策支持、报告生成等场景。

**参数：**
- `input`: 用户输入文本（必需，如果未提供 messages）
- `messages`: 消息列表（可选，input 的替代方案）
- `prompt`: 系统提示词（可选）
- `history`: 聊天历史（可选，可从上下文获取）
- `token`: API token（可选，可从配置或环境变量读取）
- `url`: LLM API URL（可选，可从配置或环境变量读取）
- `model`: 模型名称（可选，默认："gpt-4o"）
- `provider`: 提供商名称（可选，默认："azure"）
- `temperature`: 温度参数（可选，默认：0）
- `use_context`: 是否使用上下文中的历史（可选，默认：False）
- `context_key`: 从上下文获取历史的键名（可选，默认："llm_history"）
- `headers`: 自定义 HTTP 头（可选，会覆盖配置和环境变量）

**配置优先级：**
- `params` > 环境变量 > `config.yaml`
- Token: `params.token` > `LLM_TOKEN` > `config.llm.token`
- URL: `params.url` > `LLM_URL` > `config.llm.url`
- Headers: `params.headers` > `LLM_HEADERS_JSON` > `config.llm.headers_json`

**使用示例：**

```python
# 基本使用（token 和 url 从配置读取）
llm_result = orchestrator.execute_module(
    "llm_chat",
    params={
        "input": "分析服务 qingqiu 的健康状况",
        "prompt": "你是一个运维专家"
    }
)

# 使用上下文历史进行连续对话
llm_result = orchestrator.execute_module(
    "llm_chat",
    params={
        "input": "继续分析",
        "use_context": True,  # 使用上下文中的对话历史
    }
)

# 结合其他模块的结果进行智能分析
upstream_result = orchestrator.execute_module(
    "upstream_query",
    params={"service_name": "qingqiu"}
)

error_log_result = orchestrator.execute_module(
    "error_log_query",
    params={"service_name": "qingqiu", "time_range": "1h"}
)

# 将多个模块的结果传递给 LLM 进行综合分析
analysis_prompt = f"""请分析服务 qingqiu 的监控情况：

1. Upstream 状态: {upstream_result.status.value}
   - Upstream 数量: {upstream_result.data.get('upstream_info', {}).get('summary', {}).get('total_upstreams', 0) if upstream_result.data else 0}

2. 错误日志状态: {error_log_result.status.value}
   - 错误总数: {error_log_result.data.get('logs', {}).get('summary', {}).get('total_errors', 0) if error_log_result.data else 0}

请给出简要的分析和建议。"""

llm_result = orchestrator.execute_module(
    "llm_chat",
    params={
        "input": analysis_prompt,
        "prompt": "你是一个专业的运维专家，擅长分析服务监控数据和故障排查。请用简洁明了的语言回答问题。"
    }
)

if llm_result.status.value == "success":
    print(f"分析结果: {llm_result.data.get('output')}")
    print(f"Token 使用: {llm_result.data.get('usage', {}).get('total_tokens', 0)}")
```

**完整工作流示例：**

```python
# 1. 查询服务信息
upstream_result = orchestrator.execute_module("upstream_query", ...)

# 2. 查询错误日志
error_log_result = orchestrator.execute_module("error_log_query", ...)

# 3. LLM 智能分析
llm_result = orchestrator.execute_module(
    "llm_chat",
    params={
        "input": f"分析服务监控数据：{upstream_result.data} 和 {error_log_result.data}",
        "prompt": "你是运维专家"
    }
)

# 4. 根据 LLM 分析结果决定下一步操作
if llm_result.status.value == "success":
    analysis = llm_result.data.get('output')
    # 根据分析结果执行后续操作...
```

## 输出

程序会：

1. 在控制台显示工作流执行状态和结果
2. 将结果保存到 `results.json` 文件

## 完整使用示例

### 示例：服务健康检查和分析

```python
# run.py 中的完整示例
def main():
    setup_logging("INFO")
    
    config_loader = ConfigLoader()
    config_loader.load_config()
    
    orchestrator = Orchestrator(config_loader)
    orchestrator.set_context('config_loader', config_loader)
    
    # 注册所有模块
    orchestrator.register_module(UpstreamQueryModule())
    orchestrator.register_module(ErrorLogQueryModule())
    orchestrator.register_module(LLMChatModule())
    
    # 1. 查询 upstream 信息
    upstream_result = orchestrator.execute_module(
        "upstream_query",
        params={"service_name": "qingqiu"}
    )
    
    # 2. 查询错误日志
    service_name = orchestrator.get_context('last_queried_service', 'qingqiu')
    error_log_result = orchestrator.execute_module(
        "error_log_query",
        params={"service_name": service_name, "time_range": "1h"}
    )
    
    # 3. LLM 智能分析
    llm_input = f"""分析服务 {service_name}：
    - Upstream: {upstream_result.status.value}
    - 错误日志: {error_log_result.data.get('logs', {}).get('summary', {})}
    请给出分析和建议。"""
    
    llm_result = orchestrator.execute_module(
        "llm_chat",
        params={
            "input": llm_input,
            "prompt": "你是运维专家"
        }
    )
    
    # 4. 输出结果
    if llm_result.status.value == "success":
        print(f"✅ 分析完成: {llm_result.data.get('output')}")
```

## 注意事项

1. **MCP 服务器配置**: 确保 MCP 服务器可访问且 token 有效
2. **LLM 配置**: 确保配置了 LLM token 和 URL（在 `config.yaml` 或环境变量中）
3. **模块执行顺序**: 模块按代码顺序执行，如果某个模块失败，可以添加条件判断决定是否继续
4. **上下文数据**: 模块间通过共享上下文传递数据，注意键名冲突
5. **环境变量优先级**: 环境变量会覆盖配置文件中的设置，适合生产环境使用
6. **LLM Token 使用**: LLM 模块会返回 token 使用情况，可用于监控和成本控制

## 许可证

（根据项目需要添加许可证信息）

