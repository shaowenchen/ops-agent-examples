# Ops Agent Exception - 异常分析框架

基于流程图的异常分析框架，实现从告警事件到异常点发现的完整流程。

## 目录

- [架构设计](#架构设计)
- [核心组件](#核心组件)
- [数据流](#数据流)
- [使用说明](#使用说明)
- [开发指南](#开发指南)

## 架构设计

根据异常分析流程图，框架采用分层架构设计：

```
┌─────────────────────────────────────────────────────────┐
│                   主入口 (main.py)                      │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│           异常分析引擎 (AnomalyAnalyzer)                 │
│  ┌──────────────────────────────────────────────────┐  │
│  │  步骤1: 异常类型识别 (AnomalyTypeDetector)        │  │
│  │  输入: 告警事件、历史异常、规则                    │  │
│  │  输出: 当前告警类型                                │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  步骤2: 分析相关实体 (EntityAnalyzer)             │  │
│  │  输入: 异常类型、CMDB、异常库                      │  │
│  │  输出: 候选异常点                                  │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  步骤3: 分析异常 (AnomalyAnalyzer)                │  │
│  │  输入: 候选异常点、Events、Trace、Metrics、Log     │  │
│  │  输出: 带置信区间的异常点                          │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  步骤4: 发现异常点 (AnomalyPointDiscoverer)       │  │
│  │  输入: 带置信区间的异常点                          │  │
│  │  输出: 发现的异常点                                │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### 核心流程

1. **告警事件输入** → 异常类型识别
2. **异常类型** → 分析相关实体
3. **相关实体** → 分析异常（使用 Events, Trace, Metrics, Log）
4. **异常分析结果** → 发现异常点

### 目录结构

```
ops-agent-exception/
├── configs/                    # 配置文件
│   └── config.yaml            # 主配置文件
├── ops_agent/                 # 核心代码
│   ├── config/                # 配置模块
│   │   └── config_loader.py   # 配置加载器
│   ├── core/                  # 核心模块
│   │   └── anomaly_analyzer.py # 异常分析引擎
│   ├── processors/            # 处理器模块
│   │   ├── anomaly_type_detector.py      # 异常类型识别器
│   │   ├── entity_analyzer.py            # 实体分析器
│   │   ├── anomaly_analyzer.py           # 异常分析器
│   │   └── anomaly_point_discoverer.py   # 异常点发现器
│   └── utils/                 # 工具模块
│       └── logging.py         # 日志工具
├── logs/                      # 日志目录
├── input.txt                  # 默认告警输入文件
├── main.py                    # 主入口
└── README.md                  # 说明文档
```

## 核心组件

### 1. 异常分析引擎 (AnomalyAnalyzer)

**位置**: `ops_agent/core/anomaly_analyzer.py`

**职责**:
- 协调整个异常分析流程
- 管理各个处理器的调用顺序
- 处理流程中的数据传递

**主要方法**:
- `analyze(alarm_event)`: 执行完整的异常分析流程
- `_detect_anomaly_type()`: 步骤1 - 异常类型识别
- `_analyze_related_entities()`: 步骤2 - 分析相关实体
- `_analyze_anomalies()`: 步骤3 - 分析异常
- `_discover_anomaly_points()`: 步骤4 - 发现异常点

### 2. 处理器模块 (Processors)

#### 2.1 异常类型识别器 (AnomalyTypeDetector)

**位置**: `ops_agent/processors/anomaly_type_detector.py`

**功能**:
- 根据告警事件识别异常类型
- 参考历史异常数据
- 应用规则库中的规则

#### 2.2 实体分析器 (EntityAnalyzer)

**位置**: `ops_agent/processors/entity_analyzer.py`

**功能**:
- 根据异常类型分析相关实体
- 从 CMDB 获取实体信息
- 从异常库获取相关异常模式

#### 2.3 异常分析器 (AnomalyAnalyzer)

**位置**: `ops_agent/processors/anomaly_analyzer.py`

**功能**:
- 对候选异常点进行深入分析
- 收集 Events、Trace、Metrics、Log 数据
- 计算异常置信区间

#### 2.4 异常点发现器 (AnomalyPointDiscoverer)

**位置**: `ops_agent/processors/anomaly_point_discoverer.py`

**功能**:
- 根据置信区间过滤异常点
- 生成异常点报告
- 提供修复建议

## 数据流

```
告警事件
    │
    ▼
[异常类型识别]
    │
    ├─→ 历史异常 ─┐
    └─→ 规则 ────┼─→ 当前告警类型
                 │
                 ▼
        [分析相关实体]
                 │
                 ├─→ CMDB ────────┐
                 └─→ 异常库 ──────┼─→ 候选异常点
                                 │
                                 ▼
                        [分析异常]
                                 │
                                 ├─→ Events ────┐
                                 ├─→ Trace ────┤
                                 ├─→ Metrics ──┼─→ 带置信区间的异常点
                                 └─→ Log ──────┘
                                 │
                                 ▼
                        [发现异常点]
                                 │
                                 └─→ 发现的异常点
```

## 使用说明

### 配置

#### 方式一：配置文件

编辑 `configs/config.yaml` 文件，配置：
- MCP 服务器地址
- LLM 配置

#### 方式二：环境变量（推荐）

环境变量优先级高于配置文件，可以通过环境变量覆盖配置文件中的值。

**MCP 配置环境变量：**
- `MCP_SERVER_URL`: MCP 服务器地址
- `MCP_TIMEOUT`: 超时时间（默认: "30s"）
- `MCP_TOKEN`: MCP 认证令牌

**LLM 配置环境变量：**
- `LLM_API_KEY`: LLM API 密钥
- `LLM_API_HOST`: LLM API 地址
- `LLM_MODEL`: LLM 模型名称
- `LLM_MAX_TOKENS`: 最大 token 数量（整数）

**使用示例：**

```bash
# 设置环境变量
export MCP_SERVER_URL="https://api.example.com/mcp"
export MCP_TOKEN="your-token-here"
export LLM_API_KEY="your-api-key"
export LLM_API_HOST="https://api.openai.com/v1"
export LLM_MODEL="gpt-4"
export LLM_MAX_TOKENS="8000"

# 运行程序
python main.py input.txt
```

**使用 .env 文件：**

创建 `.env` 文件：

```bash
MCP_SERVER_URL=https://api.example.com/mcp
MCP_TIMEOUT=30s
MCP_TOKEN=your-token-here

LLM_API_KEY=your-api-key
LLM_API_HOST=https://api.openai.com/v1
LLM_MODEL=gpt-4
LLM_MAX_TOKENS=8000
```

程序会自动加载 `.env` 文件中的环境变量（如果使用了 `python-dotenv`）。

### 运行

#### 快速开始

```bash
# 使用默认的 input.txt 文件（推荐）
python main.py

# 或显式指定文件
python main.py input.txt
```

#### 运行选项

```bash
# 使用自定义告警文件
python main.py my_alarm.txt

# 指定配置文件
python main.py input.txt -c configs/config.yaml

# 启用详细日志
python main.py input.txt --verbose

# 查看帮助
python main.py --help
```

### 告警事件文件格式

程序支持两种格式的告警文件：

#### 方式一：文本格式（推荐，默认使用 input.txt）

```
Grafana告警 
时间：2025-11-13 14:52:00
标题：[FIRING:1] ATMS应用平均算力超过90% 
应用名: qwen3-235b-a22b-instruct-2507	
详情：
exported_namespace: ai-nlp-llm	exported_pod: qwen3-235b-a22b-instruct-2507-v5-decode-0	prometheus: monitoring/ksyun-bj6-e	平均算力: 99.25
```

#### 方式二：JSON 格式

如果文件是 JSON 格式（以 `{` 开头），程序会自动识别并解析：

```json
{
  "event_id": "alarm-001",
  "timestamp": "2024-01-01T10:00:00Z",
  "source": "monitoring-system",
  "severity": "high",
  "message": "CPU usage exceeds threshold",
  "metadata": {
    "host": "server-01",
    "cpu_usage": 95,
    "threshold": 80,
    "service": "web-service"
  }
}
```

**字段说明：**
- `event_id`: 告警事件唯一标识
- `timestamp`: 时间戳
- `source`: 告警来源
- `severity`: 严重程度（如：low, medium, high, critical）
- `message`: 告警消息
- `metadata`: 额外的元数据（可选）

## 开发指南

### 扩展点

框架设计时考虑了扩展性：

1. **新增处理器**: 在 `processors` 目录下创建新的处理器类
2. **自定义分析算法**: 在各处理器的 TODO 位置实现具体算法
3. **自定义置信度计算**: 在 `AnomalyAnalyzer._calculate_confidence_interval()` 中实现

### 实现处理器

```python
from ops_agent.config import ConfigLoader

class MyProcessor:
    def __init__(self, config_loader: ConfigLoader):
        self.config_loader = config_loader
    
    def process(self, input_data):
        # TODO: 实现处理逻辑
        pass
```

### 流程步骤说明

#### 步骤1: 异常类型识别
- **输入**: 告警事件、历史异常、规则
- **输出**: 当前告警类型
- **实现位置**: `ops_agent/processors/anomaly_type_detector.py`

#### 步骤2: 分析相关实体
- **输入**: 异常类型、CMDB、异常库
- **输出**: 候选异常点
- **实现位置**: `ops_agent/processors/entity_analyzer.py`

#### 步骤3: 分析异常
- **输入**: 候选异常点、Events、Trace、Metrics、Log
- **输出**: 带置信区间的异常点
- **实现位置**: `ops_agent/processors/anomaly_analyzer.py`

#### 步骤4: 发现异常点
- **输入**: 带置信区间的异常点
- **输出**: 发现的异常点
- **实现位置**: `ops_agent/processors/anomaly_point_discoverer.py`

## 注意事项

1. **当前状态**: 框架使用伪代码实现，所有 TODO 标记的地方需要实现具体逻辑
2. **配置**: 配置文件位于 `configs/config.yaml`，支持环境变量覆盖
3. **数据源**: 数据源的连接方式需要根据实际环境配置
4. **算法**: 异常分析算法需要根据业务需求实现
5. **置信度**: 置信度计算可以使用统计方法或机器学习方法

## 后续开发任务

1. 实现异常类型识别算法
2. 实现实体分析和关联逻辑
3. 实现异常分析和置信度计算
4. 实现异常点发现和推荐生成
5. 集成实际的数据源连接
