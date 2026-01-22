# Data Ground Truth Policy

**Version**: 1.0  
**Effective Date**: 2026-01-22  
**Authority**: [RFC-009](rfc/RFC-009-ground-truth-api-control.md)  
**Owner**: Council of Six

---

## 1. Policy Statement

본 프로젝트에서 **REST API 분봉**을 데이터의 유일한 참값(Ground Truth)으로 정의합니다.

---

## 2. 참값 우선순위

### 2.1 계층 구조

| 순위 | 데이터 소스 | 신뢰도 | 사용 조건 |
|:----:|-----------|--------|----------|
| **1** | REST API 분봉 (KIS/Kiwoom) | **100%** | 항상 최우선 |
| **2** | 검증된 틱 집계 분봉 | **95%** | Volume Check 통과 시 (오차 < 0.1%) |
| **3** | 미검증 틱 집계 분봉 | **N/A** | 임시 데이터, 검증 필수 |

### 2.2 REST API 명세

| Provider | TR ID | 용도 | Rate Limit |
|----------|-------|------|------------|
| KIS | `FHKST03010200` | 국내 분봉 조회 | 30 req/s |
| Kiwoom | `ka10080` (opt10080) | 국내 분봉 조회 | 30 req/s |

---

## 3. 사용 시나리오별 정책

### 3.1 백테스팅 (Backtesting)
- **필수**: REST API 분봉 (1순위)
- **근거**: 법적 효력, 재현 가능성
- **예외**: 없음

### 3.2 머신러닝 학습 (ML Training)
- **필수**: REST API 분봉 (1순위)
- **근거**: 모집단 데이터, 완전성 보장
- **예외**: PoC 단계에서만 검증된 틱 집계 허용

### 3.3 실시간 알고리즘 트레이딩
- **허용**: 검증된 틱 집계 분봉 (2순위)
- **근거**: 속도 우선 (< 100ms latency 필요)
- **조건**: 일일 Volume Check 통과 필수

### 3.4 품질 리포팅 (Quality Report)
- **필수**: REST API 분봉 (1순위)
- **근거**: 감사 대응, 재현 가능성
- **예외**: 없음

---

## 4. 구현 가이드

### 4.1 Database 컬럼

모든 분봉 데이터는 `source_type` 컬럼을 포함해야 합니다:

```sql
CREATE TABLE market_candles (
    time TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(12) NOT NULL,
    interval VARCHAR(10) NOT NULL,
    open DOUBLE PRECISION,
    high DOUBLE PRECISION,
    low DOUBLE PRECISION,
    close DOUBLE PRECISION,
    volume BIGINT,
    source_type VARCHAR(50) DEFAULT 'TICK_AGGREGATION_UNVERIFIED',
    PRIMARY KEY (time, symbol, interval)
);

-- Index for Ground Truth queries
CREATE INDEX idx_candles_source_truth 
ON market_candles(symbol, time) 
WHERE source_type IN ('REST_API_KIS', 'REST_API_KIWOOM');
```

### 4.2 쿼리 패턴

```python
# ✅ 백테스팅용 참값 쿼리
SELECT * FROM market_candles 
WHERE source_type IN ('REST_API_KIS', 'REST_API_KIWOOM')
  AND symbol = %(symbol)s
  AND time BETWEEN %(start)s AND %(end)s
ORDER BY time;

# ✅ 실시간 알고리즘용 (검증된 데이터 포함)
SELECT * FROM market_candles 
WHERE source_type IN ('REST_API_KIS', 'TICK_AGGREGATION_VERIFIED')
  AND symbol = %(symbol)s
ORDER BY time DESC LIMIT 100;

# ❌ 잘못된 예시 (미검증 데이터 사용 금지)
SELECT * FROM market_candles 
WHERE source_type = 'TICK_AGGREGATION_UNVERIFIED';  -- 금지
```

### 4.3 Serving Strategy (API/UI)

Backend API 및 Dashboard는 데이터의 출처에 관계없이 최적의 정합성을 가진 데이터를 제공해야 합니다.

**Union Priority Logic**:
- **원칙**: 참값(REST)이 존재하면 이를 우선 노출하고, 없을 경우에만 검증된 틱 데이터를 노출합니다.

```sql
-- 시각화 및 서빙 시 우선순위 쿼리
WITH CombinedCandles AS (
    SELECT *, 1 as priority FROM market_candles WHERE source_type IN ('REST_API_KIS', 'REST_API_KIWOOM')
    UNION ALL
    SELECT *, 2 as priority FROM market_candles WHERE source_type = 'TICK_AGGREGATION_VERIFIED'
    UNION ALL
    SELECT *, 3 as priority FROM market_candles WHERE source_type = 'TICK_AGGREGATION_UNVERIFIED'
)
SELECT DISTINCT ON (time, symbol) * 
FROM CombinedCandles 
ORDER BY time, symbol, priority;
```

---

## 5. 검증 프로세스

### 5.1 Volume Check (Tier-1 검증)

```python
# Validation Threshold
VOLUME_TOLERANCE = 0.001  # 0.1%

def is_verified(tick_volume, api_volume):
    """틱 집계 분봉이 검증 통과 여부 판단"""
    if api_volume == 0:
        return tick_volume == 0
    
    delta = abs(tick_volume - api_volume) / api_volume
    return delta < VOLUME_TOLERANCE
```

### 5.2 검증 주기
- **일일**: 장 마감 후 15:30-16:00 (전체 종목)
- **실시간**: 분 단위 검증 (선택적, 알고리즘 트레이딩 시)

---

## 6. 예외 처리

### 6.1 REST API 장애 시
1. **즉시 알림**: Sentinel 경보 발송
2. **임시 조치**: 검증된 틱 집계 사용
3. **복구**: API 정상화 후 즉시 재조회 및 교체

### 6.2 Volume Check 실패 시
- **Action**: Manual Review 대기열 추가
- **Notification**: QA 팀에 알림
- **Status**: `source_type = 'TICK_AGGREGATION_UNVERIFIED'` 유지

---

## 7. Compliance

### 7.1 필수 준수 사항
- [ ] 모든 백테스팅은 REST API 분봉 사용
- [ ] 모든 ML 학습 데이터는 REST API 분봉 사용
- [ ] 품질 리포트는 REST API 분봉 기준 작성
- [ ] `source_type` 컬럼 누락 금지

### 7.2 위반 시 조치
- **경고**: 첫 위반 시 팀 공유
- **차단**: 반복 위반 시 PR Reject
- **감사**: 분기별 코드 검토

---

## 8. 승인 기록

| Role | Decision | Date |
|------|----------|------|
| PM | ✅ Approved | 2026-01-22 |
| Architect | ✅ Approved | 2026-01-22 |
| Data Scientist | ✅ Approved | 2026-01-22 |
| Infra | ✅ Approved | 2026-01-22 |
| Developer | ✅ Approved | 2026-01-22 |
| QA | ✅ Approved | 2026-01-22 |

---

**Document Owner**: Council of Six  
**Review Cycle**: Quarterly  
**Next Review**: 2026-04-22
