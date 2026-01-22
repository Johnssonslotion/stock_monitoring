"""
Verification Module
===================
RFC-008 Tick Data Completeness & Quality Assurance System

Components:
- api_registry: API Target 중앙 관리
- scheduler: 검증 작업 스케줄링
- worker: Producer/Consumer 기반 비동기 처리
- realtime_verifier: 장 중 실시간 검증

Usage:
    from src.verification import api_registry, VerificationProducer, VerificationConsumer

    # API 타겟 조회
    target = api_registry.get_target(APIEndpointType.MINUTE_CANDLE)

    # 검증 작업 생성
    producer = VerificationProducer()
    await producer.produce_daily_tasks()

    # 검증 작업 소비
    consumer = VerificationConsumer()
    await consumer.start()
"""

from src.verification.api_registry import (
    api_registry,
    APITargetRegistry,
    APITarget,
    APIProvider,
    APIEndpointType
)

from src.verification.scheduler import (
    VerificationSchedule,
    ScheduleType,
    MarketSchedule,
    SimpleIntervalScheduler,
    CronScheduler,
    VerificationSchedulerManager,
    DEFAULT_SCHEDULES
)

from src.verification.worker import (
    VerificationTask,
    VerificationResult,
    VerificationStatus,
    ConfidenceLevel,
    VerificationConfig,
    VerificationProducer,
    VerificationConsumer
)

from src.verification.realtime_verifier import (
    RealtimeConfig,
    RealtimeVerifier
)

__all__ = [
    # API Registry
    "api_registry",
    "APITargetRegistry",
    "APITarget",
    "APIProvider",
    "APIEndpointType",

    # Scheduler
    "VerificationSchedule",
    "ScheduleType",
    "MarketSchedule",
    "SimpleIntervalScheduler",
    "CronScheduler",
    "VerificationSchedulerManager",
    "DEFAULT_SCHEDULES",

    # Worker
    "VerificationTask",
    "VerificationResult",
    "VerificationStatus",
    "ConfidenceLevel",
    "VerificationConfig",
    "VerificationProducer",
    "VerificationConsumer",

    # Realtime
    "RealtimeConfig",
    "RealtimeVerifier"
]
