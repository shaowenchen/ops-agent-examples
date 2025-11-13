# -*- coding: utf-8 -*-
"""
异常类型识别器 - 步骤1: 识别异常类型
输入: 告警事件
输出: 当前告警类型（实体类型 + 异常类型）
"""

from typing import Dict, Any

from ..config import ConfigLoader
from ..core.models import AlarmEvent, AnomalyType
from ..core.anomaly_types import (
    EntityType,
    AnomalyTypeEnum,
)
from ..utils.logging import get_logger

logger = get_logger(__name__)


class AnomalyTypeDetector:
    """
    异常类型识别器

    功能：
    - 根据告警事件的关键字识别异常类型
    - 识别实体类型（Node、Pod、Service 等）
    - 识别具体异常类型（CPU、Memory、Error 等）
    """

    def __init__(self, config_loader: ConfigLoader):
        """
        初始化异常类型识别器

        Args:
            config_loader: 配置加载器
        """
        self.config_loader = config_loader
        logger.info("异常类型识别器初始化完成")

    def detect(self, alarm_event: AlarmEvent) -> AnomalyType:
        """
        识别异常类型

        Args:
            alarm_event: 告警事件

        Returns:
            异常类型对象
        """
        logger.info(f"[步骤1] 开始识别异常类型")
        logger.info(f"  告警事件ID: {alarm_event.event_id}")
        logger.info(f"  告警消息: {alarm_event.message}")
        logger.info(f"  告警来源: {alarm_event.source}")
        logger.info(f"  告警元数据: {alarm_event.metadata}")

        try:
            # 使用关键字匹配进行分类
            logger.info(f"  开始关键字匹配分析...")
            result = self._classify_by_keywords(alarm_event)

            logger.info(f"  关键字匹配结果:")
            logger.info(f"    - 实体类型: {result.get('entity_type', 'unknown')}")
            logger.info(f"    - 异常类型ID: {result.get('type_id', 'unknown')}")
            logger.info(f"    - 置信度: {result.get('confidence', 0.5):.2%}")
            logger.info(f"    - 分析理由: {result.get('reasoning', '')}")

            entity_type = result.get("entity_type", "unknown")
            type_id = result.get("type_id", "unknown")
            confidence = result.get("confidence", 0.5)
            reasoning = result.get("reasoning", "")

            # 验证 entity_type 是否有效
            if entity_type not in [e.value for e in EntityType]:
                logger.warning(
                    f"  警告: 识别的实体类型无效: {entity_type}，从 type_id 提取"
                )
                # 从 type_id 中提取 entity_type（如 node_cpu -> node）
                if "_" in type_id:
                    entity_type = type_id.split("_")[0]
                    logger.info(f"  从 type_id 提取实体类型: {entity_type}")
                else:
                    entity_type = "unknown"

            # 验证 type_id 是否是有效的枚举名称（转换为大写）
            type_id_upper = type_id.upper()
            try:
                anomaly_enum = AnomalyTypeEnum[type_id_upper]
                type_name = anomaly_enum.value
                logger.info(f"  验证通过: 异常类型 {type_id} 在枚举中")
            except KeyError:
                logger.warning(
                    f"  警告: 识别的异常类型不在枚举中: {type_id}，使用默认值"
                )
                anomaly_enum = AnomalyTypeEnum.UNKNOWN
                type_id = "unknown"
                type_name = anomaly_enum.value
                entity_type = "unknown"

            logger.info(
                f"[步骤1] 识别完成: [{entity_type}] {type_name} (置信度: {confidence:.2%})"
            )

            return AnomalyType(
                entity_type=entity_type,
                type_id=type_id.lower(),
                type_name=type_name,
                confidence=confidence,
                description=reasoning,
            )
        except Exception as e:
            logger.error(f"[步骤1] 识别异常类型失败: {str(e)}", exc_info=True)
            # 降级处理：返回默认值
            return AnomalyType(
                entity_type="unknown",
                type_id="unknown",
                type_name=AnomalyTypeEnum.UNKNOWN.value,
                confidence=0.3,
                description=f"无法识别异常类型: {str(e)}",
            )

    def _classify_by_keywords(self, alarm_event: AlarmEvent) -> Dict[str, Any]:
        """
        基于关键字进行异常类型分类

        Args:
            alarm_event: 告警事件

        Returns:
            分类结果字典，包含 entity_type, type_id, confidence, reasoning
        """
        # 获取告警消息
        message = alarm_event.message.lower()
        metadata_str = str(alarm_event.metadata).lower()
        source = alarm_event.source.lower()

        # 合并所有文本用于匹配
        text = f"{message} {metadata_str} {source}".lower()

        # 判断异常类型（返回枚举名称）
        entity_type = "unknown"
        type_id = "unknown"
        confidence = 0.5
        reasoning = "无法从告警消息中明确识别异常类型"

        # Pod 相关
        if any(
            keyword in text
            for keyword in ["pod", "容器", "container", "k8s", "kubernetes"]
        ):
            entity_type = "pod"
            if any(keyword in text for keyword in ["cpu", "算力", "计算", "处理器"]):
                type_id = "pod_cpu"
                confidence = 1
                reasoning = "告警消息包含 Pod 和 CPU 相关关键词"
            elif any(
                keyword in text for keyword in ["内存", "memory", "ram", "mem", "oom"]
            ):
                type_id = "pod_memory"
                confidence = 1
                reasoning = "告警消息包含 Pod 和内存相关关键词"
            elif any(
                keyword in text
                for keyword in ["磁盘io", "diskio", "磁盘i/o", "io压力", "iops"]
            ):
                type_id = "pod_diskio"
                confidence = 1
                reasoning = "告警消息包含 Pod 和磁盘IO相关关键词"
            elif any(
                keyword in text
                for keyword in ["crash", "崩溃", "异常退出", "exit", "terminated"]
            ):
                type_id = "pod_crash"
                confidence = 1
                reasoning = "告警消息包含 Pod 和崩溃相关关键词"
            elif any(
                keyword in text
                for keyword in ["重启", "restart", "restarted", "重启中"]
            ):
                type_id = "pod_restart"
                confidence = 1
                reasoning = "告警消息包含 Pod 和重启相关关键词"
            elif any(
                keyword in text
                for keyword in ["错误", "error", "失败", "fail", "failed"]
            ):
                type_id = "pod_error"
                confidence = 0.7
                reasoning = "告警消息包含 Pod 和错误相关关键词"

        # 节点相关
        elif any(
            keyword in text for keyword in ["node", "节点", "主机", "host", "server"]
        ):
            entity_type = "node"
            if any(
                keyword in text
                for keyword in ["cpu", "算力", "计算", "处理器", "processor"]
            ):
                type_id = "node_cpu"
                confidence = 1
                reasoning = "告警消息包含节点和 CPU 相关关键词"
            elif any(keyword in text for keyword in ["内存", "memory", "ram", "mem"]):
                type_id = "node_memory"
                confidence = 1
                reasoning = "告警消息包含节点和内存相关关键词"
            elif any(
                keyword in text
                for keyword in [
                    "磁盘io",
                    "diskio",
                    "磁盘i/o",
                    "io压力",
                    "iops",
                    "disk io",
                ]
            ):
                type_id = "node_diskio"
                confidence = 1
                reasoning = "告警消息包含节点和磁盘IO相关关键词"
            elif any(
                keyword in text
                for keyword in ["磁盘", "disk", "存储空间", "storage", "空间不足"]
            ):
                type_id = "node_disk"
                confidence = 1
                reasoning = "告警消息包含节点和磁盘相关关键词"
            elif any(
                keyword in text
                for keyword in ["网络", "network", "带宽", "bandwidth", "流量"]
            ):
                type_id = "node_network"
                confidence = 1
                reasoning = "告警消息包含节点和网络相关关键词"

        # 服务相关
        elif any(
            keyword in text
            for keyword in ["service", "服务", "api", "接口", "endpoint"]
        ):
            entity_type = "service"
            if any(
                keyword in text
                for keyword in [
                    "5xx",
                    "500",
                    "502",
                    "503",
                    "504",
                    "服务器错误",
                    "server error",
                ]
            ):
                type_id = "service_http5xx"
                confidence = 0.9
                reasoning = "告警消息包含服务和 HTTP 5xx 错误相关关键词"
            elif any(
                keyword in text
                for keyword in [
                    "4xx",
                    "400",
                    "404",
                    "401",
                    "403",
                    "客户端错误",
                    "client error",
                ]
            ):
                type_id = "service_http4xx"
                confidence = 0.9
                reasoning = "告警消息包含服务和 HTTP 4xx 错误相关关键词"
            elif any(
                keyword in text
                for keyword in ["响应码", "http", "错误", "error", "异常"]
            ):
                type_id = "service_error"
                confidence = 1
                reasoning = "告警消息包含服务和 HTTP 错误相关关键词"
            elif any(
                keyword in text
                for keyword in [
                    "慢",
                    "slow",
                    "响应",
                    "response",
                    "延迟",
                    "latency",
                    "耗时",
                ]
            ):
                type_id = "service_slow"
                confidence = 1
                reasoning = "告警消息包含服务和响应缓慢相关关键词"
            elif any(
                keyword in text
                for keyword in ["timeout", "超时", "请求超时", "连接超时"]
            ):
                type_id = "service_timeout"
                confidence = 0.9
                reasoning = "告警消息包含服务和超时相关关键词"
            elif any(
                keyword in text
                for keyword in ["down", "不可用", "宕机", "unavailable", "offline"]
            ):
                type_id = "service_down"
                confidence = 0.9
                reasoning = "告警消息包含服务不可用相关关键词"

        # 应用相关
        elif any(
            keyword in text
            for keyword in ["application", "应用", "app", "程序", "应用服务"]
        ):
            entity_type = "application"
            if any(
                keyword in text
                for keyword in ["错误", "error", "异常", "exception", "失败"]
            ):
                type_id = "application_error"
                confidence = 1
                reasoning = "告警消息包含应用和错误相关关键词"
            elif any(
                keyword in text
                for keyword in ["慢", "slow", "响应", "性能", "performance"]
            ):
                type_id = "application_slow"
                confidence = 1
                reasoning = "告警消息包含应用和响应缓慢相关关键词"
            elif any(keyword in text for keyword in ["异常", "exception", "异常堆栈"]):
                type_id = "application_exception"
                confidence = 1
                reasoning = "告警消息包含应用和异常相关关键词"
            elif any(
                keyword in text
                for keyword in ["部署", "deployment", "部署失败", "deploy failed"]
            ):
                type_id = "application_deployment"
                confidence = 1
                reasoning = "告警消息包含应用和部署失败相关关键词"

        # 数据库相关
        elif any(
            keyword in text
            for keyword in [
                "database",
                "数据库",
                "db",
                "mysql",
                "postgresql",
                "redis",
                "mongodb",
            ]
        ):
            entity_type = "database"
            if any(
                keyword in text
                for keyword in [
                    "连接",
                    "connection",
                    "连接失败",
                    "connection failed",
                    "无法连接",
                ]
            ):
                type_id = "database_connectionfailure"
                confidence = 0.9
                reasoning = "告警消息包含数据库和连接失败相关关键词"
            elif any(
                keyword in text
                for keyword in ["慢", "slow", "查询慢", "slow query", "性能"]
            ):
                type_id = "database_slow"
                confidence = 1
                reasoning = "告警消息包含数据库和响应缓慢相关关键词"
            elif any(keyword in text for keyword in ["错误", "error", "异常", "失败"]):
                type_id = "database_error"
                confidence = 1
                reasoning = "告警消息包含数据库和错误相关关键词"
            elif any(
                keyword in text
                for keyword in [
                    "数据损坏",
                    "data corruption",
                    "数据完整性",
                    "integrity",
                ]
            ):
                type_id = "database_datacorruption"
                confidence = 0.9
                reasoning = "告警消息包含数据库和数据损坏相关关键词"

        # 网络相关
        elif any(
            keyword in text
            for keyword in ["network", "网络", "网络连接", "network connection"]
        ):
            entity_type = "network"
            if any(
                keyword in text
                for keyword in ["流量", "traffic", "带宽", "bandwidth", "流量异常"]
            ):
                type_id = "network_network"
                confidence = 1
                reasoning = "告警消息包含网络和流量相关关键词"
            elif any(
                keyword in text for keyword in ["延迟", "latency", "延迟过高", "高延迟"]
            ):
                type_id = "network_latency"
                confidence = 1
                reasoning = "告警消息包含网络和延迟相关关键词"
            elif any(
                keyword in text
                for keyword in [
                    "连接失败",
                    "connection failure",
                    "无法连接",
                    "连接断开",
                ]
            ):
                type_id = "network_connectionfailure"
                confidence = 0.9
                reasoning = "告警消息包含网络和连接失败相关关键词"

        # 存储相关
        elif any(
            keyword in text for keyword in ["storage", "存储", "volume", "pv", "pvc"]
        ):
            entity_type = "storage"
            if any(
                keyword in text
                for keyword in ["磁盘", "disk", "空间", "容量", "空间不足"]
            ):
                type_id = "storage_disk"
                confidence = 1
                reasoning = "告警消息包含存储和磁盘相关关键词"
            elif any(
                keyword in text for keyword in ["io", "i/o", "io异常", "io error"]
            ):
                type_id = "storage_io"
                confidence = 1
                reasoning = "告警消息包含存储和 IO 相关关键词"
            elif any(
                keyword in text
                for keyword in ["容量", "capacity", "容量超限", "容量不足"]
            ):
                type_id = "storage_capacity"
                confidence = 1
                reasoning = "告警消息包含存储和容量相关关键词"

        # 如果没有匹配到，尝试通用匹配
        if type_id == "unknown":
            if any(
                keyword in text
                for keyword in ["响应码", "http", "错误", "error", "异常"]
            ):
                entity_type = "service"
                type_id = "service_error"
                confidence = 0.6
                reasoning = "告警消息包含错误相关关键词，推测为服务错误"
            elif any(keyword in text for keyword in ["pod", "容器", "container"]):
                entity_type = "pod"
                type_id = "pod_error"
                confidence = 0.6
                reasoning = "告警消息包含 Pod 相关关键词，推测为 Pod 错误"
            elif any(keyword in text for keyword in ["node", "节点", "主机"]):
                entity_type = "node"
                type_id = "node_cpu"
                confidence = 0.5
                reasoning = "告警消息包含节点相关关键词，推测为节点异常"

        return {
            "entity_type": entity_type,
            "type_id": type_id,
            "confidence": confidence,
            "reasoning": reasoning,
        }
