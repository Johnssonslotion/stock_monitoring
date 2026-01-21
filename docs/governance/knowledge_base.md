# 🧠 Technical Knowledge Base

본 문서는 프로젝트 세션이 종료되어도 핵심 기술 설계와 결정 사항이 유지될 수 있도록 관리되는 지식 허브입니다.

## 설계 및 의사결정 이력
- **[Back-end Architecture](./architecture.md)**: 가변적 워커(Configurable Worker) 구조 및 인터페이스 설계.
- **[Broker Infrastructure](infrastructure.md)**: 한투/키움/미래 소켓 제약사항 및 Failure Modes 통합 가이드. (v2.2)
- **[Strategy Anchoring](../strategies/anchoring_strategy.md)**: 상법개정(2024-02-26) 기반 데이터 분석 앵커링 원칙.

---

## 🔒 유지관리 수칙
- 모든 분석 결과는 브레인 아티팩트에서 확정된 후 본 경로로 이관(Sync)한다.
- 새로운 브로커나 API 도입 시 `Broker Infrastructure` 문서를 우선 업데이트한다.
