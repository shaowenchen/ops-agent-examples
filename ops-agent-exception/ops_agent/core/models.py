# -*- coding: utf-8 -*-
"""
数据模型定义
"""

from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class AlarmEvent:
    """告警事件"""
    event_id: str
    timestamp: str
    source: str
    severity: str
    message: str
    metadata: Dict[str, Any]


@dataclass
class AnomalyType:
    """异常类型"""
    entity_type: str  # 实体类型：node, pod, service 等
    type_id: str  # 异常类型ID：node_cpu, pod_memory 等
    type_name: str  # 异常类型名称（描述）
    confidence: float
    description: str


@dataclass
class CandidateAnomalyPoint:
    """候选异常点"""
    entity_id: str
    entity_type: str
    entity_name: str
    related_alarms: List[str]
    metadata: Dict[str, Any]


@dataclass
class AnomalyPointWithConfidence:
    """带置信区间的异常点"""
    entity_id: str
    entity_type: str
    entity_name: str
    confidence: float
    confidence_interval: tuple  # (lower, upper)
    anomaly_indicators: List[Dict[str, Any]]
    metadata: Dict[str, Any]


@dataclass
class DiscoveredAnomalyPoint:
    """发现的异常点"""
    entity_id: str
    entity_type: str
    entity_name: str
    confidence: float
    anomaly_type: str
    timestamp: str
    indicators: List[Dict[str, Any]]
    recommendations: List[str]
    metadata: Dict[str, Any]

