# Gap Analysis Report: Documentation vs Implementation

## 1. 개요 (Overview)
본 문서는 `ai-rules.md`의 **"No Spec, No Code"** 원칙에 따라 시스템 전반의 문서화 현황을 진단하고, 코드에 숨겨진 "암묵적 로직(Hidden Logic)"을 식별합니다.

## 2. 진단 결과 요약 (Summary)

| Component | Status | Spec File | Major Gaps |
| :--- | :--- | :--- | :--- |
| **Backend (Core)** | 🟡 Partial | `specs/backend_specification.md` | `history/loader.py`의 Backfill 로직 Spec 누락. Hardcoded URL Defaults. |
| **Frontend (UI)** | 🔴 **Missing** | *None* | `config.js`의 API 엔드포인트 구성 로직, WebSocket 연결 정책 문서 부재. |
| **Database** | 🔴 **Missing** | *None* | TimescaleDB Hypertable 설정, `market_ticks` 스키마 정의가 코드/SQL에만 존재. |
| **Infrastructure** | 🟢 Safe | `infrastructure.md` | Docker/Port 설정은 기존 문서에 비교적 잘 정의됨. |

## 3. 상세 분석 (Detailed Findings)

### 3.1 Backend Gaps
- **Hardcoded Defaults**: `real_collector.py` 등에 `ws://ops.koreainvestment.com:21000` 문자열이 하드코딩됨. Spec 문서의 Table과 일치하지만, **Single Source of Truth**가 아님 (Duplicate).
- **History Loader**: 실시간 수집(WebSocket) 외에, 과거 데이터 적재(`history/loader.py`)의 에러 처리 핸들링(`rt_cd` check)이 Spec에 명시되지 않음.

### 3.2 Frontend Gaps
- **Implicit Protocol**: `scr/viewer/dashboard`에서 API 서버 포트를 `8000`으로 가정하고 연결하는 로직이 있으나, 이를 정의한 인터페이스 명세가 없음.
- **Vite Config**: Proxy 설정 및 환경 변수(`VITE_API_HOST`) 의존성이 문서화되지 않음.

### 3.3 Database Gaps
- **Schema Visibility**: `market_ticks` 테이블이 어떤 컬럼을 가지는지, 압축 정책(Compression Policy)은 무엇인지 확인하려면 `migrations/` 폴더 sql 파일을 직접 열어봐야 함.

## 4. 조치 계획 (Action Plan)

### Phase 2: Standardization
1.  **Frontend Spec 작성**: `docs/specs/ui_specification.md` 생성. (API 연동 규약 정의)
2.  **DB Schema Spec 작성**: `docs/specs/database_schema.md` 생성. (Table/Column 정의)
3.  **Backend Spec 보완**: Backfill/History API 프로토콜 추가.

### Phase 3: Verification
- 모든 Code의 Docstring에 관련 `See docs/specs/...` 링크 추가 Refactoring.
