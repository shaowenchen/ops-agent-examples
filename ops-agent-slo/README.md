# Ops Agent SLO

一个用于服务级别目标（SLO）监控和分析的工具，通过代码编排各个检查模块，传递和复用参数，调用 MCP 或 LLM 服务。

## 功能特性

- 🔧 **模块化设计**: 每个检查模块独立目录，易于扩展和维护
- 🔄 **参数传递和复用**: 模块间通过共享上下文传递参数和数据
- 🎯 **工作流编排**: 支持复杂的工作流定义，包括条件执行和结果复用
- 🔌 **MCP 集成**: 支持调用多个 MCP 服务器
- 🤖 **LLM 支持**: 预留 LLM 接口（可扩展）
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

编辑 `configs/config.yaml` 文件，配置 MCP 服务器：

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
# llm:
#   provider: "openai"
#   api_key: "your-api-key"
#   model: "gpt-4"
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

```bash
python main.py
```

### 指定配置文件

```bash
python main.py -c /path/to/config.yaml
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
  -e MCP_SERVERS_JSON='[{"name":"MCP1","server_url":"...","token":"..."}]' \
  ops-agent-slo:latest

# 或者直接执行 main.py（一次性执行）
docker run --rm \
  -v $(pwd)/configs:/app/configs:ro \
  -v $(pwd)/run.py:/app/run.py:rw \
  -e MCP_SERVERS_JSON='[{"name":"MCP1","server_url":"...","token":"..."}]' \
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

触发一个工作流执行。

**请求示例（GET）：**
```
GET /trigger?verbose=false
```

**请求示例（POST）：**
```json
{
  "verbose": false
}
```

注意：API 会执行 `run.py` 中的代码。

**响应示例：**
```json
{
  "success": true,
  "summary": {
    "total": 2,
    "success": 2,
    "failed": 0,
    "skipped": 0,
    "success_rate": 1.0
  },
  "results": [...],
  "context": {...}
}
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

## 输出

程序会：

1. 在控制台显示工作流执行状态和结果
2. 将结果保存到 `results.json` 文件

## 注意事项

1. 确保 MCP 服务器可访问且 token 有效
2. 模块按顺序执行，如果某个模块失败，可以配置是否继续
3. 结果会保存到 `results.json`，包含所有模块结果和上下文
4. 模块间通过共享上下文传递数据，注意键名冲突

## 许可证

（根据项目需要添加许可证信息）

