# IDEA: 강제적 환경 변수 기반 비밀 정보 관리 (Mandatory Secret Management)
**Status**: 💡 Seed (Idea)
**Priority**: P1

## 1. 개요 (Abstract)
로컬 개발 및 진단 스크립트 작성 시 API 키나 시크릿 정보가 코드에 하드코딩되는 것을 원천 차단하고, 반드시 `.env` 파일이나 환경 변수를 통해서만 주입되도록 강제하는 규칙과 시스템을 설계합니다.

## 2. 가설 및 기대 효과 (Hypothesis & Impact)
- **가설**: 비밀 정보에 접근하는 표준 인터페이스를 강제하고, 커밋 전 자동 검사(Lint/Hook)를 도입한다면 인적 실수로 인한 보안 유출 사고를 0%에 수렴하게 만들 수 있다.
- **기대 효과**:
    - 보안 사고 예방: 실수로 인한 API 키 노출 방지.
    - 환경 일관성: 개발/테스트/운영 환경 간 설정 관리의 일관성 확보.
    - 거버넌스 준수: `.ai-rules.md` 보안 원칙의 기술적 강제.

## 3. 구체화 세션 (Elaboration)
- **Security Architect**: 
    - **Secret Manager Wrapper**: `src/core/security.py`를 만들어 특정 환경 변수(`KIS_APP_KEY` 등)에만 접근 가능한 클래스를 정의. 직접적인 `os.getenv` 호출보다 이 래퍼 사용을 권장.
    - **Pre-commit Hook**: `TruffleHog`나 `git-secrets`를 도입하여 커밋 전에 높은 엔트로피를 가진 문자열이나 특정 키 패턴을 자동 스캔.
- **DevOps Engineer**: 
    - **Strict Config Validation**: 앱 시작 시 필수 환경 변수가 없으면 즉시 에러를 내고 종료(`pydantic`의 `required` 필드 활용).
    - **CI Secret Scanner**: GitHub Actions에 비밀 정보 스캔 단계를 추가하여 원격 저장소 유입 원천 봉쇄.
- **Developer (AI Persona)**:
    - **Antigravity Rule Update**: `.ai-rules.md`에 "진단 스크립트 작성 시에도 반드시 `load_dotenv()`와 `os.getenv()`를 사용해야 하며, 하드코딩 발견 시 즉시 반려" 규칙 명시.

## 4. 로드맵 연동 시나리오
- **Pillar**: Pillar 0 (Governance & Standards) / Pillar 1 (Infra Stability)
- **Target Component**: `.ai-rules.md`, `src/core/config.py`, `.pre-commit-config.yaml`

## 5. 제안하는 다음 단계
1. **Security Wrapper 구현 (ISSUE-017)**: 비밀 정보를 안전하게 가져오는 표준 클래스 구현.
2. **Pre-commit 도입 (ISSUE-018)**: 로컬 보안 스캔 훅 설정.
3. **AI 거버넌스 개정**: 하드코딩 금지 규칙을 `.ai-rules.md`에 추가.
