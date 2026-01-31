# RFC-010 Integration Test Plan (TDD Spec)

**Context**: RFC-010(데이터 파이프라인 고도화)의 기술적 완성도를 사전에 검증하기 위한 통합 테스트 계획입니다.
**Authority**: [development.md](../governance/development.md), [ground_truth_policy.md](../governance/ground_truth_policy.md)

## 1. Test Scope & Strategy

본 테스트 계획은 RFC-010의 3가지 Phase(Streaming, Whale, Compression)가 기존 Governance 정책을 준수하는지 "Implementation First"가 아닌 "**Test First**" 방식으로 검증합니다.

### 1.1 Compliance Checkpoints
- **Schema Triple-Lock**: DB 스키마 변경 시 API Spec 및 Model 동기화 확인.
- **Ground Truth**: Whale 감지 시 사용된 Tick 데이터가 신뢰할 수 있는 소스(`REST_API_KIS` or `VERIFIED`)인지 확인.
- **Zero-Cost**: 압축 정책 적용 후 스토리지 절감 효율(%) 측정.

## 2. Test Cases (TDD Spec)

### Phase 1: Streaming
- **TC-010-01 (`test_orderbook_streaming_flow`)**
    - **Step**: 10단계 호가 데이터 Redis 발행 -> `ws://...` 구독 클라이언트 수신.
    - **Verify**:
        - 수신된 데이터가 10단계 Depth를 유지하는가?
        - 델타 압축 해제 후 스냅샷이 온전한가? (Integrity)
    - **Policy**: `ground_truth_policy.md`의 `source_type` 필드 확인.

### Phase 2: Whale Detection
- **TC-010-02 (`test_whale_alert_trigger`)**
    - **Step**: 1.5억 원 상당의 대형 체결 Mock 데이터 주입.
    - **Verify**: `WhaleDetector`가 정확히 트리거되는가?
    - **Constraint**: `price * volume` 계산 시 정밀도 손실(Float) 방지.

### Phase 3: Storage Efficiency
- **TC-010-03 (`test_compression_policy`)**
    - **Step**: 25시간 전의 `market_orderbook` 데이터 Mocking -> Sentinel 압축 Job 수행.
    - **Verify**:
        - 해당 청크가 압축 상태(`compressed`)로 전환되었는가?
        - 압축 후에도 SQL 조회(`SELECT *`)가 정상 동작하는가? (Transparent)

## 3. Implementation Plan (Files)
1. `tests/integration/test_rfc010_pipeline.py`: 통합 테스트 코드 (Pytest)
2. `src/data_ingestion/pipeline/rfc010_mock.py`: 정책 준수용 Mock 객체
