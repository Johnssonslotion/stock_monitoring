# 📡 Specifications Index (기술 명세서)

본 문서는 프로젝트의 모든 상세 기술 명세와 설계 문서를 관리하는 인덱스입니다.

## 1. Core Backend & Ingestion
- **[Backend Specification](backend_specification.md)**: 백엔드 핵심 설계 가이드.
- **[Data Schema](data_schema.md)**: 데이터 테이블 정의 및 타입 명세.
- **[Database Specification](database_specification.md)**: 데이터베이스 인프라 및 설정.
- **[Ingestion Open Guard](ingestion_open_guard_spec.md)**: 수집기 예외 처리 및 가드 로직.

## 2. API & Integration
- **[API Specification](api_specification.md)**: 전체 API 인터페이스 정의 (OpenAPI).
- **[API Hub v2 Overview](api_hub_v2_overview.md)**: 통합 REST API Gateway 전체 설계 (ISSUE-037).
- **[API Hub v2 Configuration](api_hub_config_spec.md)**: API Hub 설정 옵션 참조 문서 (SSoT).
- **[BaseAPIClient Spec](api_hub_base_client_spec.md)**: API Client 추상화 설계 (Phase 2).
- **[Token Manager Spec](token_manager_spec.md)**: OAuth 토큰 자동 갱신 설계 (Phase 2).
- **[Rate Limiter Integration](rate_limiter_integration_plan.md)**: Rate Limit 통합 계획 (Phase 2).
- **[Data Normalization](data_normalization_spec.md)**: 외부 API 통합 정규화 규격.
- **[Kiwoom Chart API](kiwoom-chart-api.md)**: 키움 전용 차트 API 연동 가이드.
- **[Virtual Investment API](virtual_investment_api.md)**: 가상 투자 모듈 및 API 명세.

## 3. Frontend & Visualization
- **[UI Design Master](ui_design_master.md)**: 디자인 시스템 및 UI 전체 설계.
- **[UI Specification](ui_specification.md)**: 상세 컴포넌트 동작 명세.
- **[Backend Chart V2](backend_chart_v2_spec.md)**: 차트 고도화를 위한 백엔드 최적화.
- **[Visualization Viewport](visualization_viewport_strategy.md)**: 차트 렌더링 및 뷰포트 관리 전략.
- **[Chart Features V2](chart_features_v2.md)**: 확장된 차트 기능 정의.

## 4. Monitoring & Infra
- **[Infrastructure](infrastructure.md)**: 시스템 하드웨어 및 서버 구조.
- **[Sentinel Specification](monitoring/sentinel_specification.md)**: 장애 감지 에이전트 상세 설계.
- **[Realtime Metrics WS](monitoring/realtime_metrics_ws.md)**: 실시간 모니터링 웹소켓 사양.

## 5. Reference & Others
- **[API Reference Hub](api_reference/README.md)**: 외부 API(한투/키움) 상세 레퍼런스.
- **[Experimentation](experimentation.md)**: 시스템 실험 및 검증 가이드.
- **[Short Term Goals](short_term.md)** / **[Long Term Goals](long_term.md)**
- **[Base Strategy](strategies/base_strategy.md)**

---
> [!NOTE]
> 모든 명세서는 `/create-spec` 워크플로우를 통해 생성 및 갱신됩니다.
