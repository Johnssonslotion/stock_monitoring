# Antigravity Documentation Hub

본 문서는 프로젝트의 모든 규정, 명세, 기술 문서의 **단일 진실 공급원(SSoT)** 인덱스입니다.

---

## 🏛️ 거버넌스 (Governance)
- **[Governance Hub (INDEX)](governance/INDEX.md)**: 전체 운영 원칙 및 의사결정 인덱스
- **[Constitution (ai-rules.md)](../.ai-rules.md)**: 최상위 절대 원칙 및 워크플로우 바인딩
- **[HISTORY](governance/HISTORY.md)** / **[RFC Center](governance/rfc/)** / **[Templates](governance/templates/)**
- **[RFC-005: Unified Verification](governance/decisions/RFC-005_unified_verification_architecture.md)**: 검증 아키텍처 통합 (Queue + Realtime)
- **[RFC-006: Auto-Deploy Verify](governance/decisions/RFC-006_automated_deployment_verification.md)**: 배포 로그 자동 검증 (Silent Failure 방지)

## 🔭 전략 및 설계 (Strategy)
- **[Strategy Hub (INDEX)](strategy/master_roadmap.md)**: 로드맵 및 핵심 아키텍처 (Master Roadmap)
- **[Grand Strategy](strategy/grand_strategy.md)** / **[Data Management](strategy/data_management_strategy.md)**
- **[Portfolio Strategy](strategy/target_portfolio.md)** / **[Architecture](strategy/architecture_design.md)**
- **[API Hub Migration Guide](guides/api_hub_migration_guide.md)**: 워커 컨테이너 통합 마이그레이션 가이드

## 📡 기술 명세서 (Specifications)
- **[Specifications Hub (INDEX)](specs/INDEX.md)**: 전체 기술 명세 및 설계 문서 인덱스
- **[API Hub v2 Overview](specs/api_hub_v2_overview.md)**: 통합 REST API Gateway 전체 설계 (ISSUE-037)
- **[API Hub v2 Configuration (SSoT)](specs/api_hub_config_spec.md)**: API Hub 설정 옵션 참조 문서
- **[Unified Verification Worker](specs/verification/unified_verification_worker.md)**: 검증 워커 통합 설계 (RFC-005)
- **[Database Spec](specs/database_specification.md)** / **[API Spec](specs/api_specification.md)**
- **[UI Master](specs/ui_design_master.md)** / **[Data Normalization](specs/data_normalization_spec.md)**

## 🛠️ 운영 및 가이드 (Operations)
- **[Testing Master](operations/testing/TESTING_MASTER_GUIDE.md)**: 테스트 실행 통합 매뉴얼
- **[Registry](operations/testing/test_registry.md)** / **[FMEA](operations/testing/FAILURE_MODE_ANALYSIS.md)**
- **[API Schema Discovery Guide](operations/testing/api_schema_discovery_guide.md)**: API 응답 스키마 자동 수집 및 문서화 가이드
- **[Runbooks](operations/runbooks/)** / **[Infrastructure](operations/infrastructure/monitoring_requirements.md)**
- **[Security](operations/security_guidelines.md)** / **[Deployment](operations/deployment/CHECKLIST.md)**

## 📝 실행 및 기록 (Issues & Ideas)
- **[Issues & Planning Hub (INDEX)](issues/INDEX.md)**: 이슈 트래킹 및 단계별 기획서
- **[Idea Bank (INDEX)](ideas/IDEA_BANK.md)**: 아이디어 인큐베이팅 허브
- **[Unified Backlog](../BACKLOG.md)** / **[Known Issues](issues/KNOWN_ISSUES.md)**

## 📦 아카이브 (Archive)
- **[Archive Center](ARCHIVE/README.md)**: 과거 리포트, 이슈, 실험 결과 등 보존 데이터

---

## 🔄 워크플로우 맵 (Workflow Map)
- 문서 관리: `@/manage-docs` | 정합성 체크: `@/run-gap-analysis`
- 스펙 생성: `@/create-spec` | 의사결정: `@/council-review`
