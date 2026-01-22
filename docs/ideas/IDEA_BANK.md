# 💡 Idea Bank (아이디어 뱅크)

본 문서는 프로젝트의 모든 전략, 인프라, UX 개선 아이디어를 통합 관리하는 **단일 진실 공급원(SSoT)**입니다. `/brainstorm`을 통해 도출된 씨앗(Seed) 아이디어들이 이곳에 모여 RFC로 발전합니다.

## 1. 활성 아이디어 (Active Ideas)

### 📈 전략 및 백테스팅 (Strategy)
- **ID-recovery-stabilization**: 데이터 복구 프로세스의 안정성 및 속도 개선.
- **ID-change-verification**: 전략 변경에 따른 성과 변화 자동 검증 시스템.
- **ID-virtual-trading-v2**: 더 정교한 가상 투자 시뮬레이션 환경 구축.

### 🏗️ 인프라 및 거버넌스 (Infrastructure)
- **ID-living-governance**: [ai-rules.md](../.ai-rules.md) 원칙과 워크플로우의 유기적 바인딩. (진행 중)
- **ID-independent-collector**: [KIS/Kiwoom 수집 모듈의 가벼운 컨테이너 분리](collector/ID-independent-collector.md).
- **ID-hybrid-storage-tiering**: [DuckDB(Cold)와 TimescaleDB(Hot)의 하이브리드 저장 최적화](ID-hybrid-storage-tiering.md).
- **ID-hybrid-db-architecture**: [하이브리드 DB 아키텍처 상세 설계](ID-hybrid-db-architecture.md).
- **ID-timescale-validation**: [TimescaleDB 데이터 무결성 검증 전략](ID-timescale-validation.md).
- **ID-sentinel-tagging**: [Sentinel 운영 이벤트 태깅 및 컨텍스트 주입 시스템](stock_monitoring/ID-sentinel-tagging.md).
- **ID-ollama-slm-backend-assistant**: [OpenCode + Ollama 백엔드 자동화 어시스턴트](stock_monitoring/ID-ollama-slm-backend-assistant.md). 🌿 Sprouting
  - ClaudeCode 보완 도구 (복잡한 작업 vs 반복 작업 역할 분담)
  - 문서 자동 동기화, 컨테이너 모니터링, 코드 품질 개선
  - Tech: OpenCode CLI + Ollama qwen2.5-coder

### 📊 데이터 품질 및 정합성 (Data)
- **ID-dual-provider-validation**: [KIS와 Kiwoom 데이터 교차 검증을 통한 무결성 확보](ID-hybrid-multi-vendor-validation.md).
- **ID-realtime-gap-recovery**: [장중 실시간 데이터 누락 자동 탐지 및 즉시 복구](ID-realtime-gap-recovery.md).
- **ID-api-normalization**: [외부 API 제공자 간의 데이터 형식 표준화](ID-docs-api-standardization.md) (`@/create-spec`).
- **ID-volume-cross-check**: [거래량 기반 정합성 체크 로직](ID-volume-cross-check.md).
- **ID-tick-quality-evaluation**: [틱 데이터 품질 평가 지표 정의](ID-tick-quality-evaluation.md).

### 📝 문서 및 프로세스 (Process)
- **ID-docs-cleanup-strategy**: [문서 전수 조사 및 구조 최적화 전략](ID-docs-cleanup-strategy.md).
- **ID-state-awareness-workflow**: [AI 상태 인지 및 워크플로우 자동화](ID-state-awareness-workflow.md).
- **ID-error-screening-system**: [에러 재발 방지를 위한 스크리닝 시스템](ID-error-screening-system.md).
- **ID-backlog-roadmap-unified**: [백로그와 로드맵의 유기적 통합 관리](ID-backlog-roadmap-unified.md).
- **ID-doc-sync-policy**: [문서 동기화 강제 프로세스](ID-doc-sync-policy.md).

## 2. 아이디어 관리 원칙
1. 모든 아이디어는 `/brainstorm`으로 시작한다.
2. 구체화 세션을 거쳐 **Mature** 상태가 되면 [Implementation Plan](../../.gemini/antigravity/brain/99091a48-40c7-464a-967f-5d999d7cfc52/implementation_plan.md) 또는 RFC로 승격한다.
3. 실현 가능성이 낮거나 우선순위에서 밀린 아이디어는 `docs/ARCHIVE/ideas/`로 이동한다.

---
> [!TIP]
> 상세 내용은 각 아이디어 파일을 참조하십시오. (정리 중)
