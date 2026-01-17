# 🌌 Antigravity Master Roadmap (전체 로드맵)

이 문서는 Antigravity 프로젝트를 단순한 수집기를 넘어 **상용 수준의 프로페셔널 트레이딩 터미널**로 진화시키기 위한 통합 마스터 로드맵입니다. 모든 마일스톤은 `.ai-rules.md`의 **품질 게이트(Quality Gate)**를 통과해야 승인됩니다.

---

## 🚦 품질 통과 기준 (Quality Assurance Gate)
| 단계 | 검증 대상 | 통과 기준 (Pass Criteria) | 보고 의무 |
| :--- | :--- | :--- | :--- |
| **Pillar 1/2** | Ingestion & Sync | 유닛 커버리지 100%, 스키마 무결성 (Tier 2) | ✅ **PASSED** |
| **Pillar 3/4** | Viewer & Ops | E2E 지연시간 < 50ms, Chaos 복구율 100% | ⏳ 예정 |

---

## 🏛️ 4대 핵심 필러 (Strategic Pillars)

### Pillar 0: 거버넌스 및 스펙 표준화 (Governance & Spec) [DONE]
- **Goal**: "No Spec, No Code". 모든 개발 활동의 선행 지표로서 문서화 강제.
- **Phase 1 (Validation)**: `ai-rules.md` 헌법 개정 및 LLM Self-Check 도입. (✅ DONE)
- **Phase 2 (Standardization)**:
  - Backend/Database/UI **3대 명세서(Specification Sheet)** 제정. (✅ DONE)
  - **RFC & ADR Process** 도입으로 변경 관리 체계화. (✅ DONE)
- **Phase 3 (Audit)**: 주기적인 문서-코드 정합성 감사 (Gap Analysis). (✅ DONE)

### Pillar 1: 인프라 안정성 (Dev/Prod 격리) [DONE]
- **Phase 1**: `.env.dev` / `.env.prod` 설정을 통한 키 및 DB 경로 분리.
- **Phase 2**: `Makefile` & `docker-compose.override.yml` 도입.

### Pillar 2: 고정밀 데이터 인입 파이프라인 (Data Ingestion) [IN-PROGRESS]
- **Phase 1 (Ticks)**: KR(Unverified)/US(✅ Verified) 실시간 체결가 수집기 구축. (✅ DONE)
  - *US Config*: `HDFSCNT0` + `/HDFSCNT0` (Dual-Socket Ready)
- **Phase 2 (Dual-Socket)**: Tick/Orderbook 소켓 분리를 통한 동시 수집 안정성 확보. (✅ DONE)
- **Phase 2.5 (Doomsday Protocol)**: 장애 발생 시 자동 복구 전략 (Sentinel Trigger -> Auto Fallback). (✅ DONE)
- **Phase 3 (Hybrid Ingestion Strategy)**: 🆕 **2026-01-14**
  - **Strategy**: **Ticks (Real-time WS)** + **Orderbook (1s Polling REST)** 혼합 운용.
  - **Standard**: **FI-2010 Format** 준수 (10-level Ask/Bid Depth) 학습용 정밀 데이터 확보.
  - **Constraints**: Single-Key 환경에서의 최적화된 동시 수집 모델.
- **Phase 4 (Quality Guardrail)**:
  - **Tier 2 기체 품질 게이트 강제 적용** (Schema Validation 승인 완료). (✅ DONE)
  - **Protocol Auto-Validation**: `invalid tr_key` 등 프로토콜 에러 자동 검출 및 차단 로직 구현. (✅ DONE)
- **Phase 5 (Subscription Confirmation)**: 🆕 **2026-01-14**
  - **구독 응답 확인**: 서버 응답(SUCCESS/FAILED) 파싱 및 성공/실패 판정. (✅ DONE)
  - **재시도 로직**: 구독 실패 시 심볼당 최대 3회 즉시 재시도. (✅ DONE)
  - **연결 대기**: switch_url 후 connection_ready 신호 대기 후 구독 시작. (✅ DONE)
  - **타임아웃 증가**: ping_timeout 10초 → 30초. (✅ DONE)

### Pillar 3: 데이터 비주얼라이제이션 & 분석 터미널 (Viewer Evolution) [IN-PROGRESS]
- **목표**: 초저지연 시각화 및 알고리즘 인터랙션.
- **Phase 1**: FastAPI 기반 시계열 쿼리 엔진 및 **Tier 3 품질 보고서** 체계 수립. (✅ DONE)
- **Phase 2**: React + Vite 기반 대시보드 및 하드웨어 가속 시각화. (✅ DONE)
- **Phase 3A (Map-First Layout)**: 🆕 **APPROVED 2026-01-12**
  - Dashboard 탭 재설계: Map 70% → Chart 30% (클릭 시 반전)
  - Multi-Timeframe Support: 일봉 → 1분봉 전환 UI
  - 사용자 온보딩: 첫 방문 툴팁 + Classic Layout 토글
  - **Timeline**: Week 1-2 (Phase 2A)
- **Phase 3B (Tick Streaming)**: 🆕 **CONDITIONAL** (Load Testing 필수)
  - WebSocket `/ws/ticks/{symbol}` 실시간 스트리밍
  - Lightweight Charts 기반 Canvas 렌더링
  - Data Quality Badge + Statistical Summary (VWAP, Spread, Velocity)
  - **Prerequisite**: Locust 성능 검증 (CPU < 80%, Latency < 100ms p95)
  - **Timeline**: Week 5-8 (Phase 3)

### Pillar 4: 운영 및 관측성 (Operations & Observability) [IN-PROGRESS]
- **목표**: 무중지 시스템 및 카오스 엔진(Chaos Engine)을 통한 복원력 강화.
- **Phase 1 (Monitoring)**: Sentinel(0-Data Alarm) 및 인프라 메트릭 수집. (✅ DONE)
- **Phase 2 (System Dashboard)**: 🆕 **2026-01-14**
  - **System Metrics**: CPU, Memory, Disk, Container Health 시각화. (✅ DONE)
  - **Log Viewer**: 주요 경고 및 장애 로그 타임라인 뷰. (✅ DONE)
- **Phase 3 (Chaos Engineering)**: DB/Network 강제 장애 시나리오 검증.

### Pillar 5: 전략 및 실험 (Strategy & Experimentation) [DONE] 🆕
- **목표**: 과거 데이터를 활용한 전략 가속 검증 및 최적화.
- **Phase 1 (Backtest Infrastructure)**: 원본과 격리된 백테스팅 전용 워크트리 및 Docker 인프라 구축. (✅ DONE)
- **Phase 2 (Engine Core)**: Event-driven 방식의 백테스팅 엔진 및 성과 측정(Sharpe, MDD 등) 모듈 구현. (✅ DONE)
- **Phase 3 (Worktree Strategy)**: `exp/*` 브랜치를 활용한 실험 관리 및 결과 리포트 자동화 프로세스 정립. (✅ DONE)

---

## 📅 타임라인 (Timeline Estimate)

| 분기 | 핵심 과제 | 기대 결과 |
| :--- | :--- | :--- |
| **Q1-A** | 환경 분리 및 데이터 파이프라인 안정화 | 장애 없는 상시 수집 및 실시간 분봉 자동 생성 |
| **Q1-B** | **품질 게이트(Tier 2) 통과** 및 호가 수집 | 기술 부채 없는 고순도 데이터셋 확보 |
| **Q2-A** | **Map-First UI 출시** (Phase 3A) 🆕 | 탐색적 데이터 분석 워크플로우 구현 |
| **Q2-B** | **Tick 스트리밍** (Phase 3B) + [Electron 앱](../docs/ui_design_master.md#11-electron-client-design-specs-phase-3-spec) | 실시간 시장 미시구조 모니터링 |

---

## 🏛️ Council of Personas 최종 승인 의견

### 👔 PM
> "품질 게이트(Tier 1~3) 도입은 프로젝트의 완성도를 객관화하는 신의 한 수입니다. 이제 모든 기능은 보고서가 수반되어야 승인됩니다."

### 🧪 QA Engineer
> "Chaos 시나리오와 스키마 무결성이 로드맵의 중심에 배치되었습니다. '테스트되지 않은 기능은 존재하지 않는 것'이라는 원칙을 끝까지 고수하겠습니다."
