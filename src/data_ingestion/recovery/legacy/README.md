# Legacy Recovery Modules

**Deprecated Date**: 2026-01-28
**Reason**: ISSUE-044 아키텍처 통합 (옵션 A)
**Superseded By**: `RealtimeVerifier` + `VerificationConsumer`

---

## 포함된 모듈

| 모듈 | 원래 역할 | 대체 방안 |
|------|----------|----------|
| `backfill_manager.py` | KIS REST API를 통한 틱 데이터 복구 → DuckDB 저장 | `VerificationConsumer._handle_recovery_task()` → TimescaleDB 직접 저장 |
| `merge_worker.py` | DuckDB 임시 파일 → 메인 DuckDB 병합 | 불필요 (TimescaleDB 직접 저장) |
| `recovery_orchestrator.py` | Log Recovery + Gap Detection + Backfill 조율 | `RealtimeVerifier` + `VerificationConsumer` 통합 |

---

## 폐기 사유

### 기존 문제점
1. **이중 저장소 운영**: DuckDB(분석) + TimescaleDB(실시간) 별도 관리
2. **수동 2단계 실행**: BackfillManager → merge_worker 순차 실행 필요
3. **Continuous Aggregates 연동 불가**: DuckDB에 저장되므로 View 갱신 안 됨
4. **코드 중복**: RealtimeVerifier + VerificationConsumer와 80% 기능 중복

### 새로운 아키텍처 (ISSUE-044)
```
RealtimeVerifier (실시간 + 배치)
       │ Gap 감지
       ▼
VerificationProducer.produce_recovery_task()
       │ Redis 큐
       ▼
VerificationConsumer._handle_recovery_task()
       │ KIS API 호출
       ▼
TimescaleDB (market_ticks) ← 직접 저장
       │
       ▼
refresh_continuous_aggregate()
       │
       ▼
market_candles_1m_view (자동 갱신)
```

---

## DuckDB 역할 변경

**기존**: 복구 중간 저장소 + 분석용
**변경 후**: **완결된(Verified) 틱 데이터만 장기 보관** (Cold Storage)

```
TimescaleDB (Hot)  →  검증 완료  →  DuckDB/Parquet (Cold)
   (실시간)              ↓              (분석/백테스팅)
                   일일 배치 아카이빙
```

---

## 재사용 시 주의사항

이 모듈들은 레거시로 분류되었으나, 특수 상황에서 재사용 가능:
- 대규모 과거 데이터 일괄 복구 (수개월치)
- TimescaleDB 장애 시 DuckDB 백업 복구
- 오프라인 분석용 데이터 추출

**사용 전 반드시 Ground Truth Policy 확인 필수**

---

## 관련 문서
- [ISSUE-044](../../../../docs/issues/ISSUE-044.md)
- [Ground Truth Policy](../../../../docs/governance/ground_truth_policy.md)
- [RFC-009](../../../../docs/governance/rfc/RFC-009-ground-truth-api-control.md)
