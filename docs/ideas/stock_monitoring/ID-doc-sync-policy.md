# IDEA: 문서 작업 전 동기화 강제 (Force Sync Before Doc Work)

**Status**: 🌿 Sprouting (Drafting)
**Priority**: P1
**Category**: Governance / Infrastructure

## 1. 개요 (Abstract)
사용자 제안: "모든 문서 작업(특히 이슈 발행, 백로그 수정 등)을 수행하기 전에는 반드시 `git pull`을 수행하여 문서 상태를 최신으로 동기화해야 한다."
목적: ID 충돌(예: `ISSUE-001` vs `ISSUE-007`) 방지 및 최신 거버넌스 규칙 준수.

## 2. 가설 및 기대 효과 (Hypothesis & Impact)
- **가설**: 문서를 작성하기 직전에 원격 상태를 확인하면, 이미 점유된 ID나 변경된 템플릿을 인지할 수 있어 충돌을 100% 예방할 수 있다.
- **기대 효과**:
    - 불필요한 재작업(Re-issue) 감소.
    - 팀원(사용자/AI) 간의 컨텍스트 불일치 해소.

## 3. 구체화 세션 (Elaboration - 6인 페르소나)
- **Developer**: "기술적으로 `git pull`은 코드와 문서를 분리해서 가져오지 않습니다. 문서를 동기화하려면 코드도 같이 동기화됩니다. 이는 개발 환경에 영향을 줄 수 있으므로(예: 실행 중인 서버), `git fetch` 후 문서(`docs/`)의 변경사항만 확인하거나, 그냥 맘편히 `git pull --rebase`를 생활화하는 것이 좋습니다."
- **Governance Officer**: "매우 찬성합니다. 특히 `BACKLOG.md`나 `ISSUE` 번호 채번은 동시성 제어가 중요합니다. 작업 시작 전 `Pull`은 헌법(Rules)에 추가되어야 합니다."
- **DevOps**: "단, `git pull` 과정에서 충돌이 나면 AI가 멈출 수 있습니다. 문서 충돌은 비교적 해결하기 쉬우니 자동화 전략을 잘 짜야 합니다."

## 4. 로드맵 연동 시나리오
- **Governance**: 이 규칙은 즉시 시행되어야 하므로 `.ai-rules.md`의 **"5. Spec Verification Gate"** 또는 **"Workflows"**에 전처리(Pre-condition) 단계로 추가되어야 합니다.
