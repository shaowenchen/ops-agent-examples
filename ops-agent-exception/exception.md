## 1. 异常分类体系

### 1.1 按故障类型分类

#### 服务故障类（Service Fault）

- failure: 服务完全故障，无法处理请求
- unreachable: 服务网络不可达，连接超时或拒绝

#### 性能问题类（Performance Issue）

- cpu: 服务高 CPU 使用率，导致处理延迟增加
- memory: 服务内存压力，可能引发 OOM 或性能下降
- networklatency: 服务间网络延迟增加
- networkdelay: 网络延迟（节点级别）
- networkloss: 网络丢包
- disk: 磁盘 IO 压力（节点级别）

#### 业务逻辑类（Business Logic）

- largegc: 大规模垃圾回收，导致短暂停顿
- cachefailure: 缓存服务故障，缓存失效或无法访问
- floodhomepage: 对前端首页发起大量请求洪水攻击
- jvmchaos: JVM 混沌注入，模拟 Java 虚拟机异常

#### 基础设施类（Infrastructure）

- nodekiller: 终止指定 Kubernetes 节点进行混沌工程测试
- podkiller: 随机终止服务 Pod，测试服务高可用性

## 2. 命名规范

### 2.1 基本语法

```
<component>.<fault_type>
```

### 2.2 组件命名规则（component）

- 格式：`[a-z0-9-]+`
- 示例：
  - 服务组件：`frontend`, `payment`, `product-catalog`, `ad`, `cart`, `checkout`
  - 节点组件：`i-m5ec00yjg8kxv34hyr0n`, `i-m5e2a4ls4q90u0zi92vk`
  - 系统组件：`load-generator`, `system`

### 2.3 故障类型命名规则（fault_type）

- 格式：`[a-z0-9]*`
- 全部使用小写：`failure`, `unreachable`, `cpu`, `memory`, `networklatency`, `networkdelay`, `networkloss`, `disk`, `largegc`, `cachefailure`, `floodhomepage`, `nodekiller`, `podkiller`, `jvmchaos`

### 2.4 完整示例

```
# 服务级别异常
payment.failure
payment.unreachable
payment.cpu
payment.memory
payment.networklatency
payment.networkloss

# 业务逻辑异常
ad.largegc
recommendation.cachefailure
load-generator.floodhomepage

# 基础设施异常
checkout.podkiller
system.nodekiller
ad.jvmchaos

# 节点级别异常
i-m5ec00yjg8kxv34hyr0n.cpu
i-m5ec00yjg8kxv34hyr0n.memory
i-m5ec00yjg8kxv34hyr0n.disk
i-m5ec00yjg8kxv34hyr0n.networkdelay
i-m5ec00yjg8kxv34hyr0n.networkloss
```

## 3. 异常标记格式

### 3.1 基础标记格式

```json
{
  "root_cause": "<component>.<fault_type>",
  "description": "异常描述",
  "severity": "critical|warning|info",
  "affects": ["告警指标列表"],
  "time_window": {
    "start": "2024-01-01T00:00:00Z",
    "end": "2024-01-01T01:00:00Z"
  }
}
```

### 3.2 告警关联标记

```json
{
  "root_cause": "payment.failure",
  "description": "模拟支付服务完全故障，无法处理任何支付请求",
  "severity": "critical",
  "affects": [
    "latency", // 请求延迟
    "traffic", // 请求流量
    "errors" // 错误率
  ],
  "alerts": [
    {
      "metric": "payment_error_rate",
      "threshold": "> 0.5",
      "duration": "5m"
    },
    {
      "metric": "payment_latency_p99",
      "threshold": "> 1000ms",
      "duration": "5m"
    }
  ],
  "time_window": {
    "start": "2024-01-01T00:00:00Z",
    "end": "2024-01-01T01:00:00Z"
  }
}
```

### 3.3 干扰项标记

```json
{
  "root_cause": "ad.cpu",
  "description": "模拟广告服务高CPU使用率（干扰项）",
  "severity": "info",
  "affects": [],
  "is_noise": true,
  "time_window": {
    "start": "2024-01-01T00:00:00Z",
    "end": "2024-01-01T01:00:00Z"
  }
}
```

### 3.4 多根因标记

```json
{
  "root_causes": [
    {
      "root_cause": "payment.failure",
      "description": "模拟支付服务完全故障",
      "severity": "critical",
      "affects": ["errors", "latency"]
    },
    {
      "root_cause": "checkout.cpu",
      "description": "模拟结算服务高CPU使用率",
      "severity": "warning",
      "affects": ["latency"]
    }
  ],
  "time_window": {
    "start": "2024-01-01T00:00:00Z",
    "end": "2024-01-01T01:00:00Z"
  }
}
```

## 4. 异常严重程度分级

### 4.1 Critical（严重）

- 服务完全故障（failure）
- 服务不可达（unreachable）
- 节点故障（nodekiller）
- 影响范围：直接影响用户请求，触发多个告警指标

### 4.2 Warning（警告）

- 高 CPU/内存使用率（cpu, memory）
- 网络延迟（networklatency, networkdelay）
- Pod 故障（podkiller）
- 影响范围：影响性能，可能触发延迟或流量告警

### 4.3 Info（信息）

- 干扰项异常（is_noise: true）
- 轻微性能波动
- 影响范围：不触发告警或仅触发轻微告警

## 5. 告警分类体系

### 5.1 告警规则分类

根据赛题中的告警规则，告警可以分为以下几类：

#### 延迟类告警（Latency Alarms）

- **frontend_avg_rt**: 前端平均响应时间告警
  - 描述：监控前端服务的平均响应时间，超过阈值时触发
  - 影响指标：latency
  - 典型场景：前端服务响应变慢，用户体验下降

- **service_avg_rt**: 服务平均响应时间告警
  - 描述：监控后端服务的平均响应时间，超过阈值时触发
  - 影响指标：latency
  - 典型场景：后端服务处理延迟增加，影响整体性能

#### 错误类告警（Error Alarms）

- **overall_error_count**: 总体错误数告警
  - 描述：监控系统总体错误请求数量，超过阈值时触发
  - 影响指标：errors
  - 典型场景：系统错误率上升，服务可用性下降

#### 灰度故障类告警（Grey Failure Alarms）

- **greyFailure**: 灰度故障告警
  - 描述：检测灰度环境或部分服务的故障，可能不会立即影响全部流量
  - 影响指标：errors, latency
  - 典型场景：灰度发布中的问题，部分用户受影响

### 5.2 告警规则命名规范

- 格式：全小写，使用下划线分隔
- 命名模式：`<scope>_<metric_type>_<aggregation>`
  - scope: 作用域（如 `frontend`, `service`, `overall`）
  - metric_type: 指标类型（如 `rt` 响应时间, `error` 错误, `count` 计数）
  - aggregation: 聚合方式（如 `avg` 平均, `count` 计数, `p99` 99分位）

### 5.3 告警规则示例

```
# 延迟类告警
frontend_avg_rt      # 前端平均响应时间
service_avg_rt       # 服务平均响应时间

# 错误类告警
overall_error_count  # 总体错误数

# 灰度故障类告警
greyFailure          # 灰度故障
```

### 5.4 告警规则与黄金三指标映射

| 告警规则            | 对应指标 | 说明                           |
| ------------------- | -------- | ------------------------------ |
| frontend_avg_rt     | latency  | 前端响应时间，影响用户体验     |
| service_avg_rt      | latency  | 服务响应时间，影响系统性能     |
| overall_error_count | errors   | 总体错误数，影响服务可用性    |
| greyFailure         | errors   | 灰度故障，可能影响部分用户     |

### 5.5 题目标记中的告警规则

在赛题输入文件中，每道题目包含 `alarm_rules` 字段，表示该题目触发的告警规则：

```json
{
  "problem_id": "002",
  "time_range": "2025-09-16 23:20:33 ~ 2025-09-16 23:30:33",
  "candidate_root_causes": ["checkout.failure", "payment.cpu", ...],
  "alarm_rules": ["service_avg_rt"]
}
```

- **alarm_rules**: 数组类型，包含该题目触发的所有告警规则
- 一道题目可能触发多个告警规则（如同时触发延迟和错误告警）
- 告警规则帮助选手理解问题的表现和影响范围

### 5.6 告警规则与根因分析

不同告警规则可能指向不同类型的根因：

| 告警规则            | 常见根因类型                           | 分析重点           |
| ------------------- | -------------------------------------- | ------------------ |
| frontend_avg_rt     | cpu, memory, networklatency, failure   | 前端性能问题       |
| service_avg_rt      | cpu, memory, networklatency, failure   | 后端服务性能问题   |
| overall_error_count | failure, unreachable, podkiller        | 服务可用性问题     |
| greyFailure         | failure, unreachable, 部分服务故障    | 灰度环境特定问题   |

## 6. 异常类型与告警指标映射

### 6.1 黄金三指标

- latency（延迟）: 请求处理延迟增加
- traffic（流量）: 请求流量异常
- errors（错误率）: 请求错误率上升

### 6.2 异常类型与告警指标映射表

| 故障类型       | 主要影响指标             | 次要影响指标 |
| -------------- | ------------------------ | ------------ |
| failure        | errors, latency          | traffic      |
| unreachable    | errors, latency          | traffic      |
| cpu            | latency                  | traffic      |
| memory         | latency, errors          | traffic      |
| networklatency | latency                  | errors       |
| networkdelay   | latency                  | errors       |
| networkloss    | errors, latency          | traffic      |
| disk           | latency                  | errors       |
| largegc        | latency                  | errors       |
| cachefailure   | latency, errors          | traffic      |
| floodhomepage  | traffic                  | latency      |
| podkiller      | errors, latency          | traffic      |
| nodekiller     | errors, latency, traffic | -            |
| jvmchaos       | latency, errors          | traffic      |
