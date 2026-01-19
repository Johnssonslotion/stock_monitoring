# IDEA: Daily Minute Recovery & Quality Assurance System

**Status**: 🌿 Sprouting (Drafting)  
**Priority**: P1  
**Category**: Infrastructure + Data  
**Source**: User (2026-01-19)  

## 1. 개요 (Abstract)

현재 시스템은 KIS/Kiwoom WebSocket을 통해 **실시간 틱 데이터**를 수집하지만, 네트워크 장애, API 제한, 서버 다운타임 등으로 인한 데이터 누락 가능성이 존재합니다.

**해결 방안**: 
- **장 마감 후** KIS/Kiwoom REST API를 통해 당일 **분봉 데이터(1분, 3분, 5분 등)**를 수집
- 실시간 틱과 분봉을 **교차 검증**하여 데이터 품질 평가
- 누락 구간 자동 탐지 및 복구

## 2. 가설 및 기대 효과 (Hypothesis & Impact)

### 가설
1. **분봉 데이터는 틱 데이터보다 안정적이다** (서버 측 집계 완료 상태)
2. **분봉 OHLCV를 틱에서 재구성**하여 비교 시, 불일치 구간 = 틱 누락 구간
3. **일 1회 분봉 수집**만으로도 99%+ 데이터 무결성 보장 가능

### 기대 효과
- **데이터 무결성**: 틱 누락 자동 탐지 및 보정
- **신뢰성**: 백테스팅 및 학습 데이터 품질 향상
- **운영 효율**: 수동 확인 불필요, 자동화된 품질 보증

## 3. 기술 구현 방안 (Technical Design)

### 3.1 데이터 수집 파이프라인

```
09:00 ~ 15:30  → 실시간 틱 수집 (WebSocket)
15:30 ~ 16:00  → 분봉 데이터 수집 (REST API)
16:00 ~ 16:30  → 품질 검증 (틱 vs 분봉)
16:30 ~ 17:00  → 누락 구간 복구 및 리포트 생성
```

### 3.2 품질 평가 메트릭

#### A. **Coverage (커버리지)**
```
Coverage = (실제 틱 레코드 수 / 예상 틱 레코드 수) × 100%

예상 레코드 수 = 거래 시간(분) × 예상 TPS (종목당)
- 고변동성: 10-50 ticks/min
- 저변동성: 1-5 ticks/min
```

#### B. **Consistency (일관성)**
```
분봉 OHLCV vs 틱 집계 OHLCV 비교

일관성 점수 = Σ(분봉[i] == 틱_집계[i]) / 총 분봉 수
```

#### C. **Latency (지연시간)**
```
지연 = (DB 저장 시각 - 실제 체결 시각)

P99 지연 < 500ms = Excellent
P99 지연 < 1000ms = Good
P99 지연 > 1000ms = Needs Improvement
```

### 3.3 KIS vs Kiwoom 비교 분석

| 메트릭 | KIS | Kiwoom | 비고 |
|--------|-----|--------|------|
| **분봉 개수** | 391개 (09:00-15:30) | 900개 (전일 포함?) | Kiwoom이 더 많은 데이터 제공 |
| **API 안정성** | 토큰 캐싱 필수 (EGW00133) | `requests` 사용 필수 | KIS가 더 까다로움 |
| **과거 데이터** | ❌ 당일만 | ❌ 당일만 | 둘 다 제한적 |
| **실시간 틱** | ✅ WebSocket | ✅ WebSocket | 둘 다 지원 |
| **추천 용도** | 백업 (KIS 틱 누락 시) | 주 데이터 소스 | Kiwoom 우선, KIS 보조 |

### 3.4 자동화 스크립트 설계

#### `scripts/daily_recovery.py`
```python
1. 장 마감 후 트리거 (cron: 0 16 * * 1-5)
2. KIS/Kiwoom REST API로 당일 분봉 수집
3. DB에서 당일 틱 데이터 조회
4. 분봉 ↔ 틱 교차 검증
5. 불일치 구간 리포트 생성
6. 누락 구간 있으면 분봉으로 보정 (Upsert)
```

#### `scripts/quality_report.py`
```python
1. Coverage, Consistency, Latency 계산
2. KIS vs Kiwoom 비교 테이블 생성
3. Markdown 리포트 생성 (data/reports/질quality_YYYYMMDD.md)
4. Slack/Email 알림 (임계값 미달 시)
```

## 4. 6인 페르소나 의견 (Council Perspective)

### 👨‍💼 PM (Product Manager)
> "데이터 품질이 백테스팅 신뢰도의 핵심입니다. 자동화된 품질 보증은 필수입니다."  
> **결정**: ✅ 승인 (P1 우선순위)

### 🏗️ Architect
> "분봉 수집은 비동기 Job으로, 틱 수집과 독립적으로 동작해야 합니다. Celery/APScheduler 도입 고려."  
> **제안**: Cron + systemd timer로 시작, 추후 Celery 마이그레이션

### 🔧 DevOps Lead
> "16:00 분봉 수집 시 KIS/Kiwoom API 동시 호출 → Rate Limit 위험. 순차 처리 또는 delay 추가 필요."  
> **주의**: TPS 제한 고려 (KIS < Kiwoom)

### 🧪 QA Lead
> "품질 메트릭 임계값이 명확해야 합니다. Coverage < 95% = FAIL?"  
> **요청**: 임계값 정의 필요

### 🛡️ Security Lead
> "분봉 데이터도 민감 정보입니다. S3 저장 시 암호화 필수."  
> **체크**: 현재 DB 암호화 상태 확인 필요

### 💻 Engineer
> "분봉-틱 매칭 알고리즘이 복잡할 수 있습니다. Time window 허용 범위?"  
> **구현 고려**: ±1초 허용, Fuzzy Matching

## 5. 로드맵 연동 시나리오

이 아이디어는 **Pillar 2: 고정밀 데이터 인입 파이프라인**의 **Phase 4.5 (Data Integrity & Continuity)**에 직접 연결됩니다.

### 현재 Roadmap 상태:
- Phase 4.5: "Daily Gap-Filler 도입" (✅ DONE - 분봉 수집 검증 완료)

### 추가될 항목:
- **Phase 4.6**: Quality Assurance Automation
  - 분봉-틱 교차 검증 자동화
  - 일일 품질 리포트 생성
  - Slack 알림 통합

## 6. 다음 단계 (Next Actions)

### Immediate (오늘):
1. ✅ KIS/Kiwoom 분봉 API 테스트 완료
2. 🔄 금일(1/19) 데이터로 품질 평가 스크립트 실행
3. 🔄 KIS vs Kiwoom 비교 분석 리포트 생성

### Short-term (이번 주):
1. `daily_recovery.py` 스크립트 작성
2. `quality_report.py` 스크립트 작성
3. Cron job 설정
4. Council Review → RFC로 승격 여부 결정

### Long-term (다음 분기):
1. Celery 기반 비동기 작업 큐 도입
2. Grafana 대시보드 통합 (실시간 품질 모니터링)
3. 머신러닝 기반 이상 패턴 탐지

## 7. 승격 기준 (Promotion to RFC)

- [x] 기술 검증 완료 (KIS/Kiwoom API 테스트)
- [ ] PoC 완료 (1일치 데이터 품질 평가)
- [ ] Council 만장일치 승인
- [ ] 비용 분석 완료 (추가 인프라 불필요 → ✅)

**예상 승격 시점**: 2026-01-20 (내일)

## 8. 참고 자료

- [KIS 분봉 테스트 결과](file:///home/ubuntu/workspace/stock_monitoring/data/proof/)
- [Kiwoom 분봉 테스트 결과](file:///home/ubuntu/workspace/stock_monitoring/data/proof/)
- [Gap Analysis Report](file:///home/ubuntu/workspace/stock_monitoring/docs/governance/gap_analysis_report_2026-01-19.md)

---

**작성일**: 2026-01-19  
**작성자**: Antigravity AI  
**버전**: v0.1 (Sprouting)
