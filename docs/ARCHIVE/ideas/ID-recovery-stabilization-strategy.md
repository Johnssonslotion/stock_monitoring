# IDEA: 장중 장애 복구 및 데이터 정합성 강화 전략
**Status**: 🌿 Sprouting (Drafting)
**Priority**: P1

## 1. 개요 (Abstract)
- **문제**: 2026-01-20 장중 `tick-archiver`(DuckDB)의 타입 오류 및 `timescale-archiver`의 Kiwoom 채널 구독 누락으로 인한 데이터 적재 장애 발생.
- **기회**: `RawLogger`에 저장된 원본 JSONL 로그를 활용하여 100% 데이터 복구를 실현하고, 향후 유사 장애 방지를 위한 아카이버 아키텍처 정규화.

## 2. 가설 및 기대 효과 (Hypothesis & Impact)
- **가설**: Raw 로그(JSONL)는 소켓 수신 즉시 파일로 기록되므로, 소비단(Archiver)의 장애와 무관하게 데이터 소스는 안전하며 이를 재처리하는 스크립트로 완벽한 복구가 가능하다.
- **기대 효과**:
    - 장중 장애 발생 시에도 데이터 유실 제로(Zero Leak) 달성.
    - KIS/Kiwoom 간 상이한 메시지 규격 및 채널 구조의 통합 관리.

## 3. 구체화 세션 (Elaboration)
- **Developer**: `RawLogger`의 JSONL 포맷은 검증되었으므로, 이를 읽어 Redis Pub/Sub을 에뮬레이션하거나 DB에 직접 Bulk Insert하는 도구가 필요함.
- **Architect**: `timescale-archiver`가 `tick:*`와 `ticker.*`를 모두 수용하도록 정규화하고, DuckDB 변환 로직에 `datetime` 객체 처리를 강화해야 함.
- **SRE**: `recovery-worker`의 `httpx` 누락과 같은 의존성 문제는 빌드 타임에 체크되도록 CI 보강 필요.

## 4. 로드맵 연동 시나리오
- **Pillar 2: Data Excellence** 항목의 "Robust Data Pipeline" 강화 과제로 포함.
- 정기적인 Raw 로그 백업 및 복구 테스트 프로세스(DR Test) 수립.
