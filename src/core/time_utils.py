"""
타임스탬프 통합 관리 유틸리티

멀티 브로커 환경에서 시간 동기화를 보장하고,
브로커별 상이한 시간 포맷을 UTC로 정규화합니다.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional
import pytz
import logging

logger = logging.getLogger(__name__)

# 한국 표준시 (KST)
KST = pytz.timezone('Asia/Seoul')


class TimestampValidationError(Exception):
    """타임스탬프 검증 실패 예외"""
    pass


class TimestampManager:
    """
    브로커별 타임스탬프를 통합 관리하는 유틸리티 클래스
    
    Features:
    - UTC 기준 시간 생성
    - 브로커별 시간 포맷 파싱
    - Clock Skew 검증
    - 타임존 변환
    """
    
    @staticmethod
    def now_utc() -> datetime:
        """
        현재 서버 시간을 UTC로 반환
        
        Returns:
            datetime: UTC 기준 현재 시간 (timezone-aware)
        """
        return datetime.now(timezone.utc)
    
    @staticmethod
    def now_kst() -> datetime:
        """
        현재 서버 시간을 KST로 반환
        
        Returns:
            datetime: KST 기준 현재 시간 (timezone-aware)
        """
        return datetime.now(KST)
    
    @staticmethod
    def parse_broker_time(
        broker_str: str, 
        broker_name: str,
        base_date: Optional[datetime] = None
    ) -> datetime:
        """
        브로커별 시간 문자열을 UTC datetime으로 파싱
        
        Args:
            broker_str: 브로커가 제공한 시간 문자열
            broker_name: 브로커 이름 ('kis', 'kiwoom_re', 'mirae')
            base_date: 기준 날짜 (시간만 제공되는 경우 사용, 기본값: 오늘)
        
        Returns:
            datetime: UTC로 변환된 시간
        
        Raises:
            TimestampValidationError: 파싱 실패 시
        """
        try:
            # 기본 날짜 설정 (시간만 제공되는 경우)
            if base_date is None:
                base_date = TimestampManager.now_kst().date()
            
            # 브로커별 포맷 처리
            if broker_name in ('kis', 'kiwoom_re', 'mirae'):
                # 모두 HHMMSS 포맷 사용 (예: "153045" = 15:30:45)
                if len(broker_str) != 6:
                    raise ValueError(f"Invalid time format: {broker_str}")
                
                hour = int(broker_str[0:2])
                minute = int(broker_str[2:4])
                second = int(broker_str[4:6])
                
                # KST 기준으로 datetime 생성
                kst_time = KST.localize(
                    datetime.combine(
                        base_date,
                        datetime.min.time().replace(
                            hour=hour, minute=minute, second=second
                        )
                    )
                )
                
                # UTC로 변환
                return kst_time.astimezone(timezone.utc)
            
            else:
                raise ValueError(f"Unknown broker: {broker_name}")
        
        except Exception as e:
            logger.error(f"Failed to parse broker time: broker={broker_name}, str={broker_str}, error={e}")
            raise TimestampValidationError(f"Time parsing failed: {e}")
    
    @staticmethod
    def validate_skew(
        broker_time: datetime, 
        tolerance_sec: int = 5,
        reference_time: Optional[datetime] = None
    ) -> bool:
        """
        브로커 시간과 서버 시간의 차이(Skew)를 검증
        
        Args:
            broker_time: 브로커가 제공한 시간 (UTC)
            tolerance_sec: 허용 오차 (초), 기본값 5초
            reference_time: 비교 기준 시간 (기본값: 현재 서버 시간)
        
        Returns:
            bool: 오차가 허용 범위 내이면 True
        """
        if reference_time is None:
            reference_time = TimestampManager.now_utc()
        
        # 시간 차이 계산 (절댓값)
        delta = abs((broker_time - reference_time).total_seconds())
        
        if delta > tolerance_sec:
            logger.warning(
                f"Clock skew detected: delta={delta:.2f}s (tolerance={tolerance_sec}s)"
            )
            return False
        
        return True
    
    @staticmethod
    def to_kst(utc_time: datetime) -> datetime:
        """
        UTC 시간을 KST로 변환
        
        Args:
            utc_time: UTC 시간
        
        Returns:
            datetime: KST로 변환된 시간
        """
        if utc_time.tzinfo is None:
            # Naive datetime은 UTC로 가정
            utc_time = utc_time.replace(tzinfo=timezone.utc)
        
        return utc_time.astimezone(KST)
    
    @staticmethod
    def to_utc(kst_time: datetime) -> datetime:
        """
        KST 시간을 UTC로 변환
        
        Args:
            kst_time: KST 시간
        
        Returns:
            datetime: UTC로 변환된 시간
        """
        if kst_time.tzinfo is None:
            # Naive datetime은 KST로 가정
            kst_time = KST.localize(kst_time)
        
        return kst_time.astimezone(timezone.utc)
    
    @staticmethod
    def format_iso(dt: datetime) -> str:
        """
        datetime을 ISO 8601 포맷으로 변환
        
        Args:
            dt: 변환할 시간
        
        Returns:
            str: ISO 8601 문자열 (예: '2026-01-16T12:00:00+00:00')
        """
        return dt.isoformat()
    
    @staticmethod
    def parse_iso(iso_str: str) -> datetime:
        """
        ISO 8601 문자열을 datetime으로 파싱
        
        Args:
            iso_str: ISO 8601 포맷 문자열
        
        Returns:
            datetime: 파싱된 시간
        """
        return datetime.fromisoformat(iso_str)
