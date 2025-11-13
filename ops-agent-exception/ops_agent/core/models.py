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
    type_id: str
    type_name: str
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

