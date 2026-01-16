# 순환매 검출 및 수집단 개편 구현 계획 (v2.2)

## 1. 목표
- 섹터 ETF 및 거래량 모니터링 기반의 순환매 검출 시스템 구축.
- 리눅스 네이티브 기반의 가변적 멀티 브로커(한투, 키움, 미래) 수집단 구현.

## 2. 주요 작업
- **수집단 개편**: 기존 구독/알림 체재를 유지한 채 Collector 레이어 신규 개발.
- **실험 영구화**: 모든 백테스트 및 분석 결과를 `experiments/`에 기록.
- **품질 보증**: 각 수집 유닛별 독립적인 유닛 테스트(Mock 기반) 수행.

## 3. 검증 계획 (Verification Strategy)
- **Phase 1 (Static Mock)**: 문서 기반 샘플 패킷으로 Pydantic 스키마 및 파서 검증.
- **Phase 2 (Traffic Recording)**: 서버 연결 시작 시 모든 Raw Packet을 `.jsonl`로 기록하여 'Golden Dataset' 구축.
- **Phase 3 (Cross Validation)**: 기록된 실제 데이터를 스키마에 재주입하여 타입 불일치, 누락 필드 등을 자동 검출 (`scripts/validate_recorded_data.py`).
- **QA**: Chaos Engineering(연결 단절) 및 Failure Mode 대응 로직 검증.
