# -*- coding: utf-8 -*-
"""
异常类型定义常量
异常类型枚举，value 为异常描述
"""

from enum import Enum
from typing import Dict, List


class EntityType(str, Enum):
    """实体类型枚举"""
    NODE = "node"
    POD = "pod"
    SERVICE = "service"
    APPLICATION = "application"
    DATABASE = "database"
    NETWORK = "network"
    STORAGE = "storage"
    UNKNOWN = "unknown"


class AnomalyTypeEnum(str, Enum):
    """异常类型枚举（value 为异常描述）"""
    
    # 节点相关
    NODE_CPU = "节点 CPU 使用率过高"
    NODE_MEMORY = "节点内存使用率过高"
    NODE_DISK = "节点磁盘使用率过高"
    NODE_DISKIO = "节点磁盘IO压力过高"
    NODE_NETWORK = "节点网络异常"
    
    # Pod 相关
    POD_CPU = "Pod CPU 使用率过高"
    POD_MEMORY = "Pod 内存使用率过高"
    POD_DISKIO = "Pod 磁盘IO压力过高"
    POD_CRASH = "Pod 崩溃"
    POD_RESTART = "Pod 重启"
    POD_ERROR = "Pod 错误"
    
    # 服务相关
    SERVICE_DOWN = "服务不可用"
    SERVICE_SLOW = "服务响应缓慢"
    SERVICE_LATENCY = "服务延迟过高"
    SERVICE_ERROR = "服务错误"
    SERVICE_HTTP4XX = "服务 HTTP 4xx 错误"
    SERVICE_HTTP5XX = "服务 HTTP 5xx 错误"
    SERVICE_TIMEOUT = "服务超时"
    
    # 应用相关
    APPLICATION_SLOW = "应用响应缓慢"
    APPLICATION_ERROR = "应用错误"
    APPLICATION_EXCEPTION = "应用异常"
    APPLICATION_DEPLOYMENT = "应用部署失败"
    
    # 数据库相关
    DATABASE_CONNECTIONFAILURE = "数据库连接失败"
    DATABASE_SLOW = "数据库响应缓慢"
    DATABASE_ERROR = "数据库错误"
    DATABASE_DATACORRUPTION = "数据库数据损坏"
    
    # 网络相关
    NETWORK_NETWORK = "网络流量异常"
    NETWORK_LATENCY = "网络延迟过高"
    NETWORK_CONNECTIONFAILURE = "网络连接失败"
    
    # 存储相关
    STORAGE_DISK = "存储磁盘使用率过高"
    STORAGE_IO = "存储 IO 异常"
    STORAGE_CAPACITY = "存储容量超限"
    
    # 其他
    UNKNOWN = "未知异常"


def get_all_anomaly_types() -> List[Dict[str, str]]:
    """
    获取所有异常类型列表
    
    Returns:
        异常类型列表，每个元素包含 type_id, type_name
    """
    return [
        {
            "type_id": anomaly_type.name.lower(),
            "type_name": anomaly_type.value
        }
        for anomaly_type in AnomalyTypeEnum
    ]
