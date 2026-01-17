# Decision Record 001: Governance Update (Dual Socket & Schema Strictness)

- **Date**: 2026-01-17
- **Status**: ~~Approved~~ **Deferred** (Superseded by Decision-002)
- **Author**: Antigravity (on behalf of Council)

## 1. Context (배경)
1.  **Dual Socket Issue**: 기존 `ai-rules.md`는 KIS API의 Single Socket을 강제했으나, 신규 API의 멀티 세션 지원 기능을 활용하여 데이터 수집 성능(Tick/Orderbook 분리)을 극대화해야 함.
2.  **Documentation Debt**: 코드와 스펙의 불일치(Gap)가 심각하며, 단순 텍스트 명세로는 이를 막을 수 없음. Swagger/OpenAPI 수준의 Strict Schema 도입이 시급함.

## 2. Council Deliberation (페르소나 협의)

### 👔 PM (Project Manager)
> "현재 우리는 코드가 문서를 앞서가는 'Technical Debt' 상황에 직면했습니다. 사용자는 단순한 Gap Analysis를 넘어, **Swagger 수준의 엄격한 검토**를 요구하고 있습니다. Dual Socket 도입보다 시급한 것은 'Spec이 없으면 코드도 없다'는 원칙을 **Machine-Readable Spec** 수준으로 격상시키는 것입니다."

### 🏛️ Architect (설계자)
> "전적으로 동의합니다. 현재 `docs/specs/*.md`는 자연어 위주라 해석의 여지가 있습니다. **Schema Enforcement**를 위해 모든 API와 데이터 구조는 Pydantic Model 또는 OpenAPI Specification(YAML) 형태로 선행 정의되어야 합니다."

### 🔧 Infrastructure Engineer (인프라)
> "Zero Cost 원칙 내에서 Dual Socket 리소스 사용은 문제없음이 확인되었습니다. 하지만 문서화되지 않은 포트 사용은 보안 위험입니다. **Spec-First**가 지켜져야 인프라 자동화도 가능합니다."

### 📝 Doc Specialist (문서)
> "히스토리 관리 전략을 'Hybrid'로 제안합니다. 이 문서는 상세 논리를 담고, `HISTORY.md`는 인덱스 역할만 합니다. 헌법(`ai-rules.md`)은 가볍게 유지합니다."

### ⚖️ Final Decision
> "**만장일치 승인**. Dual Socket 허용 및 Schema Strictness 조항을 신설하고, 변경 관리 프로토콜을 도입한다."

## 3. Changes (변경 사항)

### 3.1 Immutable Law #2 (Socket Strategy)
- **Before**: Single Socket 강제.
- **After**: **Dual Socket 허용**. 단, API Key 충돌 시 Single Socket으로 자동 복구(Fallback) 가능한 구조여야 함. (Safe Default 필수)

### 3.2 Immutable Law #7 (Schema Strictness) [NEW]
- **Content**: "모든 Public API와 DB Table은 **Swagger/OpenAPI** 또는 **SQL DDL** 수준의 정밀한 명세가 선행되어야 한다. 모호한 자연어 명세는 인정하지 않는다."

### 3.3 Rule Change Protocol [NEW]
- **Content**: 모든 헌법 개정은 `HISTORY.md`와 `decisions/`에 기록을 남긴 후에만 수행할 수 있다.
