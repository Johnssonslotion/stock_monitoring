# IDEA: Redis Rate-Controlled Dual-Provider Minute Verification
**Status**: 🎓 Graduated → [RFC-008 Appendix D](../governance/rfc/RFC-008-tick-completeness-qa.md)
**Priority**: P1
**Category**: Data + Infrastructure
**Source**: User (2026-01-20)
**Graduated**: 2026-01-20

> [!NOTE]
> 이 아이디어는 **RFC-008: Tick Data Completeness & QA System**의 **Appendix D**로 통합되었습니다.
> 상세 내용은 RFC 문서를 참조하세요.

## 1. 개요 (Abstract)

현재 **단일 API(KIS)**에 의존하는 분봉 검증 구조에서, **Redis 기반 Rate Limiter**를 통해 KIS API 호출을 제한적으로 관리하고, **Kiwoom 분봉 API**를 추가하여 **듀얼 소스 교차 검증** 체계를 구축한다.

### 문제 정의
1. **KIS API 의존성**: 단일 소스 의존으로 장애 시 검증 불가
2. **Rate Limit 리스크**: 무분별한 API 호출로 429 에러 발생 가능
3. **검증 신뢰도**: 단일 소스로는 데이터 오류 탐지 한계

### 해결 방안
```
┌─────────────────────────────────────────────────────────────┐
│                   Redis Rate Limiter (GateKeeper)           │
│              KIS: 30 calls/sec | Kiwoom: 30 calls/sec       │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
      ┌──────────────┐               ┌──────────────┐
      │  KIS REST    │               │ Kiwoom REST  │
      │  분봉 API    │               │  분봉 API    │
      │ FHKST03010200│               │   ka10080    │
      └──────────────┘               └──────────────┘
              │                               │
              └───────────────┬───────────────┘
                              ▼
                    ┌──────────────────┐
                    │  Cross-Validator │
                    │  (Volume Check)  │
                    └──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │   DuckDB/TSDB    │
                    │  (Collected Ticks)│
                    └──────────────────┘
```

## 2. 가설 및 기대 효과 (Hypothesis & Impact)

### 가설
1. **Redis Rate Limiter**가 API 호출을 제어하면 429 에러 발생률 0%
2. **KIS + Kiwoom 듀얼 검증** 시, 한쪽 API 장애에도 검증 지속 가능
3. **분봉 OHLCV 교차 대조**로 수집 틱 데이터의 누락/이상 99% 탐지 가능

### 기대 효과
| 항목 | 현재 (As-Is) | 목표 (To-Be) |
|------|--------------|--------------|
| API 장애 내성 | 단일 실패점 | Failover 가능 |
| Rate Limit 관리 | 수동/없음 | Redis 자동 제어 |
| 검증 신뢰도 | 단일 소스 | 듀얼 소스 교차 |
| API 호출 효율 | 비제어 | Token Bucket 최적화 |

## 3. 구체화 세션 (Elaboration - 6인 페르소나 의견)

### 👔 PM (Project Manager)
> "데이터 검증은 백테스트 신뢰성의 핵심입니다. 듀얼 검증으로 데이터 품질 SLA 99.9%를 목표로 합니다."
> **결정**: ✅ P1 우선순위 승인

### 🏛️ Architect
> "이미 `RedisRateLimiter`가 `src/api_gateway/rate_limiter.py`에 구현되어 있습니다. 이를 분봉 검증 파이프라인에 통합하면 됩니다. 추가 인프라 불필요."
> **제안**: 기존 GateKeeper 재활용, `MinuteVerificationWorker` 신규 구현

### 🔬 Data Scientist
> "Volume Cross-Check(ID-volume-cross-check.md)와 결합하면 최적의 검증 전략입니다. KIS와 Kiwoom의 분봉 데이터가 일치하면 '검증 완료', 불일치 시 'Deep Verification' 트리거."
> **제안**: 3단계 검증 (Volume → OHLCV → Tick Count)

### 🔧 Infrastructure Engineer
> "Zero-Cost 원칙 준수. 현재 A1 인스턴스 + Redis 환경에서 충분히 구현 가능합니다. DuckDB를 집계 엔진으로 활용하면 TimescaleDB 부하 분산도 가능합니다."
> **확인**: 추가 비용 없음

### 👨‍💻 Developer
> "기존 코드 구조:
> - `src/api_gateway/rate_limiter.py`: RedisRateLimiter (Token Bucket)
> - `src/api_gateway/worker.py`: API Worker with Rate Limiting
> 분봉 검증 로직만 추가하면 됩니다."
> **추정**: 구현 복잡도 낮음

### 📝 Doc Specialist
> "RFC-008(Tick Completeness QA)과의 관계를 명확히 해야 합니다. 이 아이디어는 RFC-008의 '검증 인프라' 확장으로 보입니다."
> **제안**: RFC-008 Amendment 또는 별도 RFC-009 생성

## 4. 기술 구현 방안

### 4.1 Redis Rate Limiter 활용

**현재 구현** (`src/api_gateway/rate_limiter.py`):
```python
class RedisRateLimiter:
    config = {
        "KIS": (30, 5),    # 30 calls/sec, burst 5
        "KIWOOM": (30, 5)  # 30 calls/sec, burst 5
    }

    async def acquire(self, api_name: str) -> bool:
        # Token Bucket Algorithm (Lua Script)
        ...
```

### 4.2 Dual-Provider Verification Flow

```python
async def verify_minute_data(symbol: str, minute: datetime):
    """듀얼 소스 분봉 검증"""

    # 1. Redis Rate Limit 획득
    if not await gatekeeper.wait_acquire("KIS", timeout=5.0):
        logger.warning("KIS rate limit exceeded, falling back to Kiwoom only")
        kis_data = None
    else:
        kis_data = await fetch_kis_minute(symbol, minute)

    if not await gatekeeper.wait_acquire("KIWOOM", timeout=5.0):
        logger.warning("Kiwoom rate limit exceeded")
        kiwoom_data = None
    else:
        kiwoom_data = await fetch_kiwoom_minute(symbol, minute)

    # 2. 교차 검증
    db_volume = await get_tick_volume_from_db(symbol, minute)

    if kis_data and kiwoom_data:
        # 듀얼 검증: 두 소스 일치 여부 확인
        if kis_data.volume == kiwoom_data.volume:
            api_volume = kis_data.volume
        else:
            logger.warning(f"API mismatch: KIS={kis_data.volume}, Kiwoom={kiwoom_data.volume}")
            api_volume = max(kis_data.volume, kiwoom_data.volume)  # 보수적 선택
    else:
        # 단일 소스 폴백
        api_volume = (kis_data or kiwoom_data).volume

    # 3. DB 데이터와 비교
    delta = abs(api_volume - db_volume) / max(api_volume, 1)
    if delta > 0.001:  # 0.1% 임계값
        await trigger_recovery(symbol, minute)
```

### 4.3 Rate Limit 전략

| 시나리오 | KIS 호출 | Kiwoom 호출 | 합계 TPS |
|----------|----------|-------------|----------|
| 정상 검증 | 50% | 50% | 60 |
| KIS 장애 | 0% | 100% | 30 |
| Kiwoom 장애 | 100% | 0% | 30 |
| 피크 시간대 | 30% | 70% | 60 |

## 5. 관련 문서 (Related Ideas/RFCs)

| 문서 | 관계 | 설명 |
|------|------|------|
| `ID-volume-cross-check.md` | 상위 전략 | Volume 기반 검증 알고리즘 |
| `ID-dual-provider-minute-collection.md` | 유사 아이디어 | 듀얼 수집 (이 아이디어는 '검증'에 초점) |
| `ID-background-cross-validation.md` | 확장 가능 | 장 중 실시간 검증으로 확장 |
| `RFC-008-tick-completeness-qa.md` | 상위 RFC | QA 시스템의 인프라 기반 |
| `src/api_gateway/rate_limiter.py` | 구현 기반 | 이미 구현된 Rate Limiter |

## 6. 로드맵 연동 시나리오

### Pillar 연결
- **Pillar 2**: 고정밀 데이터 인입 파이프라인 (Data Integrity)
- **관련 Phase**: Phase 4.5 (Daily Gap-Filler) 확장

### 구현 우선순위
1. [ ] 분봉 검증 워커 (`MinuteVerificationWorker`) 구현
2. [ ] Kiwoom 분봉 API (`ka10080`) 클라이언트 추가
3. [ ] GateKeeper 통합 (기존 Rate Limiter 활용)
4. [ ] DuckDB 기반 Volume 집계 쿼리 최적화
5. [ ] 검증 결과 리포트 자동화

## 7. 승격 기준 (Promotion Rules)

### 💡 Seed → 🌿 Sprouting
- [ ] Kiwoom 분봉 API (`ka10080`) 테스트 완료
- [ ] Rate Limiter 통합 PoC 완료

### 🌿 Sprouting → 🌳 Mature
- [ ] 1일치 데이터 듀얼 검증 테스트 완료
- [ ] 오차율 < 0.1% 달성

### 🌳 Mature → RFC
- [ ] Council 만장일치 승인
- [ ] RFC-008 Amendment 또는 RFC-009 생성

---

**작성일**: 2026-01-20
**작성자**: Claude Code
**버전**: v0.1 (Seed)
