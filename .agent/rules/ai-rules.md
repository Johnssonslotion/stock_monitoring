---
trigger: always_on
---

# AI Rules v2.0 - The Constitution (Index)
*상세 규칙은 `docs/governance/` 하위 문서를 참조한다.*

## 0. 헌장 (Preamble)
이 프로젝트는 **Google Deepmind Antigravity**가 주도하는 파일럿 프로젝트이며, 다음 3대 가치를 수호한다.
1.  **Data First**: 데이터가 없으면 전략도 없다. 로직보다 파이프라인이 우선이다.
2.  **Zero Cost**: 오라클 프리티어(4 vCPU, 24GB RAM)를 넘어선 리소스 사용은 범죄다.
3.  **High Performance**: Python의 극한을 추구한다. 비동기(Asyncio)와 최적화된 자료구조를 사용한다.

## 1. Governance Navigation
| 영역 | 문서 | 핵심 내용 |
| :--- | :--- | :--- |
| **의사결정** | [Personas & Council](file:///home/ubuntu/workspace/stock_monitoring/docs/governance/personas.md) | 6인의 페르소나, 협의 프로토콜, Auto-Proceed 원칙 |
| **개발 & QA** | [Development & Quality](file:///home/ubuntu/workspace/stock_monitoring/docs/governance/development.md) | 코딩 컨벤션, Git Flow, **Deep Verification**, 품질 게이트 |
| **인프라 & DB** | [Infrastructure](file:///home/ubuntu/workspace/stock_monitoring/docs/governance/infrastructure.md) | 리소스 원칙, DB 스키마, 보안(Auth), **Doomdsay Protocol** |

## 2. 절대 헌법 (The Immutable Laws)
다음 5가지 원칙은 어떤 경우에도 타협할 수 없는 절대 규칙이다.

1.  **Deep Verification**: 데이터 작업 후 로그만 믿지 말고 **DB를 직접 조회**하여 교차 검증하라.
2.  **Single Socket**: KIS API는 하나의 소켓 연결만 유지한다. (Dual Socket 시도 금지)
3.  **Doomsday Check**: 60초간 데이터 0건이면 즉시 복구 절차를 밟는다.
4.  **Auto-Proceed**: 단위 테스트가 통과된 Safe 작업은 즉시 실행한다.
5.  **Reporting**: 모든 변경사항은 3대 문서(`README`, `Roadmap`, `Registry`)에 즉시 동기화한다.

## 3. 언어 원칙
-   **Artifacts**: 모든 산출물(Task, Plan, Walkthrough)은 **한국어**로 작성한다.
-   **Commit**: 커밋 메시지는 **영어**로 작성한다 (Conventional Commits).


## 4. Governance 문서를 검토할때, 검토한 문서명을 출력하여,
현재 프롬프트가 정확하게 포함되었는지 사용자에게 알린다.