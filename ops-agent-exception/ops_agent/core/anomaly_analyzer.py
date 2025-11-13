# -*- coding: utf-8 -*-
"""
异常分析引擎 - 核心异常分析流程控制器
"""

from typing import List

from ..config import ConfigLoader
from ..processors.anomaly_type_detector import AnomalyTypeDetector
from ..processors.entity_analyzer import EntityAnalyzer
from ..processors.anomaly_analyzer import AnomalyAnalyzer as AnomalyProcessor
from ..processors.anomaly_point_discoverer import AnomalyPointDiscoverer
from ..utils.logging import get_logger
from .models import (
    AlarmEvent,
    AnomalyType,
    CandidateAnomalyPoint,
    AnomalyPointWithConfidence,
    DiscoveredAnomalyPoint
)

logger = get_logger(__name__)


class AnomalyAnalyzer:
    """
    异常分析引擎
    
    实现异常分析流程：
    1. 告警事件 -> 异常类型识别
    2. 异常类型 -> 分析相关实体
    3. 相关实体 -> 分析异常（使用 Events, Trace, Metrics, Log）
    4. 异常分析结果 -> 发现异常点
    """
    
    def __init__(self, config_loader: ConfigLoader):
        """
        初始化异常分析引擎
        
        Args:
            config_loader: 配置加载器
        """
        self.config_loader = config_loader
        
        # 初始化各个处理器
        self.anomaly_type_detector = AnomalyTypeDetector(config_loader)
        self.entity_analyzer = EntityAnalyzer(config_loader)
        self.anomaly_processor = AnomalyProcessor(config_loader)
        self.anomaly_point_discoverer = AnomalyPointDiscoverer(config_loader)
        
        logger.info("异常分析引擎初始化完成")
    
    def analyze(self, alarm_event: AlarmEvent) -> List[DiscoveredAnomalyPoint]:
        """
        执行完整的异常分析流程
        
        Args:
            alarm_event: 告警事件
            
        Returns:
            发现的异常点列表
        """
        logger.info("=" * 80)
        logger.info(f"开始异常分析流程 - 告警事件ID: {alarm_event.event_id}")
        logger.info(f"告警时间: {alarm_event.timestamp}")
        logger.info(f"告警来源: {alarm_event.source}")
        logger.info(f"告警级别: {alarm_event.severity}")
        logger.info(f"告警消息: {alarm_event.message}")
        logger.info("=" * 80)
        
        # 步骤1: 异常类型识别
        logger.info("\n" + "-" * 80)
        logger.info("步骤1: 异常类型识别")
        logger.info("-" * 80)
        logger.info(f"输入: 告警事件 (ID: {alarm_event.event_id})")
        current_alarm_type = self._detect_anomaly_type(alarm_event)
        logger.info(f"输出: 异常类型识别完成")
        logger.info(f"  - 实体类型: {current_alarm_type.entity_type}")
        logger.info(f"  - 异常类型ID: {current_alarm_type.type_id}")
        logger.info(f"  - 异常类型名称: {current_alarm_type.type_name}")
        logger.info(f"  - 置信度: {current_alarm_type.confidence:.2%}")
        logger.info(f"  - 描述: {current_alarm_type.description}")
        logger.info(f"步骤1完成: 识别到异常类型 [{current_alarm_type.entity_type}] {current_alarm_type.type_name}")
        
        # 步骤2: 分析相关实体
        logger.info("\n" + "-" * 80)
        logger.info("步骤2: 分析相关实体")
        logger.info("-" * 80)
        logger.info(f"输入: 告警事件 (ID: {alarm_event.event_id}), 异常类型 ({current_alarm_type.type_name})")
        candidate_points = self._analyze_related_entities(alarm_event, current_alarm_type)
        logger.info(f"输出: 相关实体分析完成")
        logger.info(f"  - 候选异常点数量: {len(candidate_points)}")
        for i, point in enumerate(candidate_points, 1):
            logger.info(f"  - 候选点 {i}: {point.entity_type}/{point.entity_name} (ID: {point.entity_id})")
        logger.info(f"步骤2完成: 找到 {len(candidate_points)} 个候选异常点")
        
        # 步骤3: 分析异常
        logger.info("\n" + "-" * 80)
        logger.info("步骤3: 分析异常")
        logger.info("-" * 80)
        logger.info(f"输入: {len(candidate_points)} 个候选异常点, 告警事件 (ID: {alarm_event.event_id})")
        anomaly_points_with_confidence = self._analyze_anomalies(candidate_points, alarm_event)
        logger.info(f"输出: 异常分析完成")
        logger.info(f"  - 异常点数量（带置信区间）: {len(anomaly_points_with_confidence)}")
        for i, point in enumerate(anomaly_points_with_confidence, 1):
            logger.info(f"  - 异常点 {i}: {point.entity_type}/{point.entity_name}")
            logger.info(f"    置信度: {point.confidence:.2%}, 置信区间: {point.confidence_interval}")
            logger.info(f"    异常指标数量: {len(point.anomaly_indicators)}")
        logger.info(f"步骤3完成: 分析得到 {len(anomaly_points_with_confidence)} 个异常点（带置信区间）")
        
        # 步骤4: 发现异常点
        logger.info("\n" + "-" * 80)
        logger.info("步骤4: 发现异常点")
        logger.info("-" * 80)
        logger.info(f"输入: {len(anomaly_points_with_confidence)} 个异常点（带置信区间）, 异常类型 ({current_alarm_type.type_name})")
        discovered_points = self._discover_anomaly_points(anomaly_points_with_confidence, current_alarm_type)
        logger.info(f"输出: 异常点发现完成")
        logger.info(f"  - 发现的异常点数量: {len(discovered_points)}")
        for i, point in enumerate(discovered_points, 1):
            logger.info(f"  - 异常点 {i}: {point.entity_type}/{point.entity_name} (ID: {point.entity_id})")
            logger.info(f"    置信度: {point.confidence:.2%}, 异常类型: {point.anomaly_type}")
            logger.info(f"    时间戳: {point.timestamp}")
            logger.info(f"    异常指标数量: {len(point.indicators)}")
            logger.info(f"    推荐建议数量: {len(point.recommendations)}")
        logger.info(f"步骤4完成: 最终发现 {len(discovered_points)} 个异常点")
        
        logger.info("\n" + "=" * 80)
        logger.info(f"异常分析流程完成 - 告警事件ID: {alarm_event.event_id}")
        logger.info(f"总结: 识别异常类型 [{current_alarm_type.entity_type}] {current_alarm_type.type_name}, "
                   f"找到 {len(candidate_points)} 个候选点, "
                   f"分析得到 {len(anomaly_points_with_confidence)} 个异常点, "
                   f"最终发现 {len(discovered_points)} 个异常点")
        logger.info("=" * 80 + "\n")
        
        return discovered_points
    
    def _detect_anomaly_type(
        self, 
        alarm_event: AlarmEvent
    ) -> AnomalyType:
        """
        步骤1: 异常类型识别
        
        Args:
            alarm_event: 告警事件
            
        Returns:
            当前告警类型
        """
        # TODO: 实现异常类型识别逻辑
        # 1. 调用 AnomalyTypeDetector.detect()
        # 2. 传入告警事件
        # 3. 返回 AnomalyType 对象
        return self.anomaly_type_detector.detect(alarm_event)
    
    def _analyze_related_entities(
        self,
        alarm_event: AlarmEvent,
        anomaly_type: AnomalyType
    ) -> List[CandidateAnomalyPoint]:
        """
        步骤2: 分析相关实体
        
        Args:
            alarm_event: 告警事件
            anomaly_type: 异常类型
            
        Returns:
            候选异常点列表
        """
        # TODO: 实现相关实体分析逻辑
        # 1. 调用 EntityAnalyzer.analyze()
        # 2. 传入告警事件和异常类型
        # 3. 从 CMDB 和异常库获取相关实体
        # 4. 返回候选异常点列表
        return self.entity_analyzer.analyze(alarm_event, anomaly_type)
    
    def _analyze_anomalies(
        self,
        candidate_points: List[CandidateAnomalyPoint],
        alarm_event: AlarmEvent
    ) -> List[AnomalyPointWithConfidence]:
        """
        步骤3: 分析异常
        
        Args:
            candidate_points: 候选异常点列表
            alarm_event: 告警事件
            
        Returns:
            带置信区间的异常点列表
        """
        # TODO: 实现异常分析逻辑
        # 1. 调用 AnomalyProcessor.analyze()
        # 2. 对每个候选异常点，收集 Events、Trace、Metrics、Log 数据
        # 3. 进行异常分析，计算置信区间
        # 4. 返回带置信区间的异常点列表
        return self.anomaly_processor.analyze(candidate_points, alarm_event)
    
    def _discover_anomaly_points(
        self,
        anomaly_points: List[AnomalyPointWithConfidence],
        anomaly_type: AnomalyType
    ) -> List[DiscoveredAnomalyPoint]:
        """
        步骤4: 发现异常点
        
        Args:
            anomaly_points: 带置信区间的异常点列表
            anomaly_type: 异常类型
            
        Returns:
            发现的异常点列表
        """
        # TODO: 实现异常点发现逻辑
        # 1. 调用 AnomalyPointDiscoverer.discover()
        # 2. 根据置信区间和阈值过滤异常点
        # 3. 生成推荐建议
        # 4. 返回发现的异常点列表
        return self.anomaly_point_discoverer.discover(anomaly_points, anomaly_type)

