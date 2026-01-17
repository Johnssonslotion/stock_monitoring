# Gap Analysis Report: Documentation vs Implementation (v1.2)

## 1. 개요 (Overview)
본 문서는 `ai-rules.md`의 **"No Spec, No Code"** 및 **"Single Source of Truth"** 원칙에 따라, 현재 시스템의 문서와 구현체 간의 간극(Gap)을 정밀 진단한 결과입니다.

> [!CRITICAL]
> **Governance Violation Detected**: 백엔드 명세서(`backend_specification.md`)가 프로젝트 헌법(`ai-rules.md`)의 **Single Socket** 원칙을 정면으로 위반하고 있습니다. 즉시 수정이 필요합니다.

## 2. 진단 결과 요약 (Summary)

| Component | Status | Spec File | Major Gaps & Violations |
| :--- | :--- | :--- | :--- |
| **Governance** |  **Critical** | `backend_specification.md` | Spec은 **Dual Socket**을 명시하나, `ai-rules.md`는 이를 **금지**함. (Spec Outdated) |
| **Strategy** |  **Vacuum** | **MISSING** | `src/backtest/strategies/` 코드는 존재하나, `docs/specs/strategies/` 명세가 **전무함**. |
| **Backend** |  Unsafe | `src/data_ingestion/price/unified_collector.py` | 코드가 `enable_dual_socket` 없을 시 **True(Dual)**로 기본값 설정함. (Safe Mode Violation) |
| **Frontend** | 🔴 Refactor | `src/web/src/StreamManager.ts` | **Heuristic Parsing** 사용 (Spec 위반), Port `8000` 하드코딩. |
| **Database** |  Warning | `migrations/000_baseline.sql` | `market_orderbook` DDL(CREATE TABLE) 누락됨. (Procedure에서만 참조) |

## 3. 상세 분석 (Detailed Findings)

### 3.1 Governance Conflict (Spec vs Constitution)
- **Issue**: `backend_specification.md` Section 3.1은 "Data Ingestion (Dual Socket)"을 표준으로 정의하고 있습니다.
- **Violation**: `ai-rules.md` Immutable Law #2는 "**Single Socket**: KIS API는 하나의 소켓 연결만 유지한다"라고 명시합니다.
- **Impact**: AI나 개발자가 Spec을 따르면 헌법을 위반하게 되는 모순 발생.
- **Action**: `RFC-001`을 발의하여 Single Socket으로 Spec을 강제 변경해야 합니다.

### 3.2 Strategy Specification Vacuum
- **Issue**: `src/backtest/strategies/` 하위에 `BaseStrategy` 등 구현체가 존재하지만, 이에 대한 입출력, 파라미터, 엣지 케이스 명세가 어디에도 없습니다.
- **Violation**: `ai-rules.md` Rule #2.6 (**No Spec, No Code**). 문서 없는 코드는 불법입니다.
- **Action**: `RFC-002`를 발의하여 전략 명세 표준을 수립하고, 기존 전략에 대한 명세를 소급 작성(Retroactive Spec)해야 합니다.

### 3.3 Backend Implementation Gaps
- **Unified Collector**: Redis 설정 부재 시 Dual Socket으로 Fallback되는 로직은 위험합니다. Single Socket Default로 변경해야 합니다.
- **Kiwoom**: `KiwoomWSCollector`에 대한 토큰 관리 및 재접속 상세 정책이 Spec에 누락되었습니다.

### 3.4 Frontend & Database
- **Frontend**: `StreamManager.ts`의 하드코딩과 휴리스틱 파싱은 유지보수성을 해칩니다.
- **Database**: `market_orderbook` 테이블 DDL이 누락되어 있어 초기 배포 시 실패할 수 있습니다.

## 4. 조치 계획 (Action Plan)

### Phase 1: Governance Repair (Immediate)
1.  **RFC 승인 및 Spec 수정**:
    - `RFC-001`: Single Socket Enforcement
    - `RFC-002`: Strategy Specification Standard
2.  **Spec Patch**: `backend_specification.md` 수정, `docs/specs/strategies/` 신설.

### Phase 2: Code Alignment
1.  **Backend Fix**: `unified_collector.py` Default 값 변경.
2.  **Strategy Doc**: 기존 코드 기반으로 Spec 역공학(Reverse Engineering)하여 문서화.
3.  **DB Migration**: 누락된 DDL 추가.

### Phase 3: Verification
1.  **Unit Test**: Spec 기반 테스트 케이스 보강.
