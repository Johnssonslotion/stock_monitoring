# IDEA: State Awareness & Context Loading Workflow
**Status**: 🌿 Sprouting
**Priority**: P2

## 1. 개요 (Abstract)
AI 에이전트나 자동화 스크립트가 작업을 시작하기 전에, **현재 프로젝트의 구조(File Structure), 설정(Config), 데이터 상태(Data State)**를 사전에 파악하여 "맹목적인 실행(Blind Execution)"으로 인한 오류를 방지하는 워크플로우를 도입한다.

## 2. 문제 정의 (Problem)
- **Blind Execution**: 파일 경로를 추측하거나, 이미 존재하는 데이터를 덮어쓰거나, 잘못된 환경변수 설정을 인지하지 못한 채 스크립트를 실행하여 실패하는 경우가 빈번함.
- **Context Gap**: 사용자의 의도와 시스템의 실제 상태(디렉토리 구조, 로그 포맷 등) 간의 괴리 발생.

## 3. 제안 워크플로우: `/detect-context` (State Analysis)
### Phase 1: 구조 파싱 (Structure Parsing)
- **Directory Mapping**: `list_dir` 재귀 호출로 `src/`, `scripts/`, `docs/`의 최신 레이아웃 확인.
- **Config Loading**: `configs/` 내의 YAML 파일과 `.env` (변수명만) 확인하여 활성화된 기능 파악.

### Phase 2: 상태 로딩 (State Loading)
- **Process Check**: 현재 실행 중인 서비스(`docker ps`, `ps aux`) 확인.
- **Data Check**: `data/raw/` 및 DB의 최신 타임스탬프 조회하여 "마지막으로 수집된 데이터" 시점 파악.

### Phase 3: Pre-Execution Report
- 실행 전 AI에게 "나는 지금 [이런 환경]에서, [이런 설정]으로, [이런 상태]의 시스템을 건드릴 것이다"라고 스스로 요약(Self-Correction)하게 함.

## 4. 기대 효과
- **에러 감소**: `FileNotFound`, `ImportError` 등의 기초적인 실수 예방.
- **안전성**: 이미 기동 중인 프로세스와의 충돌 방지.
- **문맥 유지**: 긴 세션에서도 프로젝트 구조 변경 사항을 놓치지 않음.

## 5. 로드맵 연동
- [ ] `.agent/workflows/detect-context.md` 작성.
- [ ] 주요 작업(복구, 배포) 워크플로우의 첫 단계로 `/detect-context` 의무화.
