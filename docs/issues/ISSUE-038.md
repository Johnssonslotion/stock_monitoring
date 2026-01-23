# ISSUE-038: Sentinel 및 전역 로깅 표준화 (ISO 8601 적용)

## 1. 문제 정의
- **현상**: Sentinel 및 일부 서비스의 `logging.basicConfig` 설정 시 포맷인자가 누락되어, 로그 메시지에 타임스탬프가 표시되지 않음.
- **영향**: 사고 발생 시 정확한 타임라인 추출이 불가능하며, 서비스 간 Latency 분석이 어려움.

## 2. 해결 방안 (Design)
- **표준 포맷 도입**: `[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s`
- **시간 표준**: ISO 8601 형식 사용.
- **적용 범위**: `sentinel.py`, `kis_main.py`, `kiwoom_sub.py` 등 모든 수집기 및 모니터링 모듈.

## 3. 구현 세부 사항
```python
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S%z'
)
```

## 4. Failure Analysis (ZEVS)
- **원인**: 개별 모듈 로깅 설정 시 프로젝트 표준 포맷을 강제하는 공통 유틸리티 부재.
- **방지책**: `src.core.logger` 유틸리티를 신설하거나 `development.md`에 규정 명시.

## 5. 완료 조건 (DoD)
- [ ] Sentinel 로그에 타임스탬프 표시 확인.
- [ ] KIS/Kiwoom 서비스 로그 포맷 통일.
- [ ] `development.md`에 로그 표준 가이드 추가.
