# IDEA: OpenCode + Ollama Backend Assistant

**Status**: 🌿 Sprouting (Drafting)
**Priority**: P2
**Category**: Infrastructure, DevOps
**Created**: 2026-01-22
**Updated**: 2026-01-22
**Owner**: Developer + Architect
**Tech Stack**: OpenCode (CLI), Ollama, qwen2.5-coder

---

## 1. 개요 (Abstract)

### 문제 정의
현재 시스템은 다음과 같은 반복적인 수동 작업들로 인해 개발 효율성이 저하되고 있습니다:
- 컨테이너 내부 상태를 수동으로 확인하고 리포트 작성
- API 문서와 코드 간 불일치 발생 (수동 동기화 필요)
- 거버넌스 규칙(.ai-rules.md) 준수 여부를 수동 점검
- 시스템 메트릭 분석 및 이상 징후 탐지의 지연
- Docstring, Type hints 등 코드 품질 개선 작업의 지연

### 해결 방안
**OpenCode + Ollama 조합**을 ClaudeCode의 **실행 도구(Executor)**로 활용:
- **ClaudeCode (Orchestrator)**: 전략 수립, OpenCode에 작업 위임, 결과 검증
- **OpenCode (Executor)**: ClaudeCode 명령을 받아 반복/대량 작업 실행

**핵심 패턴**: ClaudeCode가 Bash tool로 OpenCode를 호출하여 하위 작업을 자동화

---

## 2. 가설 및 기대 효과 (Hypothesis & Impact)

### 핵심 가설
> "경량 SLM을 백엔드에 상주시켜 컨테이너 내부 상태를 지속적으로 모니터링하고 자동 문서화하면, 개발자의 인지 부하를 줄이고 시스템 투명성을 높일 수 있다."

### 기대 효과
1. **문서 동기화 자동화** (30% 시간 절감)
   - API 엔드포인트 변경 시 자동으로 OpenAPI 스펙 업데이트
   - Docstring 생성 및 README 동기화

2. **실시간 시스템 상태 리포트** (가시성 80% 향상)
   - 컨테이너별 리소스 사용량, 에러 로그 요약
   - 이상 패턴 탐지 및 Slack/Discord 알림

3. **거버넌스 자동 검증** (규칙 위반 조기 발견)
   - .ai-rules.md 준수 여부 커밋 시점 체크
   - 워크플로우 이탈 감지 및 가이드 제공

4. **ClaudeCode 컨텍스트 지원** (협업 효율 20% 향상)
   - SLM이 주기적으로 시스템 상태 요약 생성
   - ClaudeCode가 작업 시작 시 최신 컨텍스트 즉시 활용

---

## 3. 아키텍처 설계 (Architecture)

### 3.1 Agent Orchestration 구조

```
┌─────────────────────────────────────────────────────────┐
│               개발자 Mac (로컬)                           │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────────────────────────────────────┐       │
│  │  ClaudeCode (Orchestrator)                   │       │
│  │  ┌────────────────────────────────────────┐  │       │
│  │  │ 1. 전략 수립                            │  │       │
│  │  │ 2. 작업 분해                            │  │       │
│  │  │ 3. OpenCode 명령 생성                   │  │       │
│  │  └────────────────────────────────────────┘  │       │
│  └──────────────────┬───────────────────────────┘       │
│                     │ Bash tool 실행                     │
│                     ▼                                     │
│  ┌──────────────────────────────────────────────┐       │
│  │  OpenCode (Executor) + Ollama                │       │
│  │  ┌────────────────────────────────────────┐  │       │
│  │  │ - Docstring 일괄 생성                   │  │       │
│  │  │ - Type hints 추가                       │  │       │
│  │  │ - 코드 분석/리포트                       │  │       │
│  │  │ - 대량 파일 처리                         │  │       │
│  │  └────────────────────────────────────────┘  │       │
│  └──────────────────┬───────────────────────────┘       │
│                     │ 결과 반환                          │
│                     ▼                                     │
│  ┌──────────────────────────────────────────────┐       │
│  │  ClaudeCode (Reviewer)                       │       │
│  │  ┌────────────────────────────────────────┐  │       │
│  │  │ 4. 결과 검증                            │  │       │
│  │  │ 5. 복잡한 부분 직접 수정                 │  │       │
│  │  │ 6. 최종 통합                             │  │       │
│  │  └────────────────────────────────────────┘  │       │
│  └──────────────────────────────────────────────┘       │
│                                                           │
└─────────────────────────────────────────────────────────┘
                    │
                    │ git push
                    ▼
┌─────────────────────────────────────────────────────────┐
│                  Production Server (Linux)               │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────┐     ┌──────────────────────┐          │
│  │   Ollama     │────▶│  OpenCode Agent      │          │
│  │ qwen2.5-coder│     │  (Daemon Mode)       │          │
│  │     :7b      │     └───────┬──────────────┘          │
│  └──────────────┘             │                          │
│                               ├─▶ 문서 자동 동기화        │
│                               ├─▶ 컨테이너 상태 리포트    │
│                               ├─▶ 거버넌스 검증           │
│                               └─▶ Redis Pub/Sub 발행     │
│                                                           │
│  ┌──────────────────────────────────────────────┐       │
│  │  기존 컨테이너                                │       │
│  │  kis-service, kiwoom-service, api-server...  │       │
│  └──────────────────────────────────────────────┘       │
│                                                           │
│  ┌──────────────┐     ┌──────────────┐                  │
│  │    Redis     │────▶│  Dashboard   │                  │
│  │ (Pub/Sub Hub)│     │     UI       │                  │
│  └──────────────┘     └──────────────┘                  │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

### 3.2 컴포넌트 상세

#### A. Ollama Service
- **모델**: `qwen2.5-coder:7b` (코딩 특화) 또는 `qwen2.5-coder:32b` (고성능)
- **역할**: OpenCode의 백엔드 LLM 엔진
- **리소스**:
  - 7B 모델: 8GB RAM, 2 CPU cores
  - 32B 모델: 32GB RAM, 4 CPU cores (고성능 작업용)

#### B. OpenCode Agent (New Container)
- **이미지**: `node:20-slim` + OpenCode CLI
- **실행 모드**: Daemon (백그라운드 상주)
- **주요 작업**:

  **1. 코드 품질 자동 개선** (Git Hook 트리거)
  ```bash
  # Pre-commit hook에서 실행
  opencode "Add docstrings to modified Python files"
  opencode "Add type hints to functions without annotations"
  opencode "Fix import ordering in changed files"
  ```

  **2. 문서 자동 동기화** (Cron: 매시간)
  ```bash
  # API 변경 감지 시 자동 실행
  opencode "Update OpenAPI spec in docs/api/ based on src/api/main.py changes"
  opencode "Sync README.md with actual project structure"
  ```

  **3. 컨테이너 상태 리포트** (5분 간격)
  ```bash
  opencode "Analyze docker stats and logs, summarize health status"
  # 출력을 Redis로 발행
  ```

  **4. 거버넌스 검증** (Pre-commit Hook)
  ```bash
  opencode "Validate commit message against .ai-rules.md conventions"
  opencode "Check if branch name follows governance rules"
  ```

#### C. Redis Integration
- **채널**: `opencode.reports`, `opencode.alerts`
- **메시지 포맷**:
  ```json
  {
    "type": "container_health",
    "timestamp": "2026-01-22T10:30:00Z",
    "agent": "opencode",
    "containers": [
      {"name": "kis-service", "cpu": "12%", "memory": "512MB", "status": "healthy"},
      {"name": "api-server", "cpu": "8%", "memory": "256MB", "errors": 0}
    ],
    "summary": "All services running normally. kis-service showing 3 connection retries in last 5min.",
    "recommendations": [
      "Consider increasing kis-service connection timeout to reduce retries"
    ]
  }
  ```

---

## 4. 구현 전략 (Implementation Strategy)

### Phase 1: 로컬 PoC (1 Day)
```bash
# Mac에서 테스트
npm install -g @opencodehq/opencode
ollama pull qwen2.5-coder:7b

# 기본 기능 테스트
cd /Users/bbagsang-u/workspace/stock_monitoring
opencode --provider ollama --model qwen2.5-coder:7b

# 테스트 시나리오
opencode "Add docstrings to src/api/main.py"
opencode "Analyze docker-compose.yml and suggest improvements"
opencode "Check if BACKLOG.md is consistent with docs/issues/"
```
- [ ] Ollama 설치 및 `qwen2.5-coder:7b` 모델 다운로드
- [ ] OpenCode 설치 및 기본 명령 테스트
- [ ] 실제 프로젝트 파일로 docstring 생성 품질 검증
- [ ] 결과물: PoC 보고서 (품질, 속도, 리소스 사용량)

### Phase 2: Docker 통합 (2 Days)
```yaml
# deploy/docker-compose.yml 추가
opencode-agent:
  image: node:20-slim
  container_name: opencode-agent
  working_dir: /workspace
  command: >
    sh -c "npm install -g @opencodehq/opencode &&
           while true; do
             opencode --provider ollama --model qwen2.5-coder:7b \
               'Check container health and report to Redis' &&
             sleep 300;
           done"
  environment:
    - OLLAMA_HOST=http://ollama:11434
  volumes:
    - ../:/workspace
    - /var/run/docker.sock:/var/run/docker.sock:ro
  depends_on:
    - ollama
    - redis

ollama:
  image: ollama/ollama:latest
  container_name: ollama-service
  volumes:
    - ollama-models:/root/.ollama
  deploy:
    resources:
      limits:
        memory: 8G
```
- [ ] `opencode-agent` 컨테이너 정의
- [ ] Ollama 서비스 추가 및 모델 자동 다운로드 스크립트
- [ ] Redis Pub/Sub 연동 테스트
- [ ] 결과물: `make up` 시 자동 시작

### Phase 3: Git Hooks 자동화 (2 Days)
```bash
# .git/hooks/pre-commit
#!/bin/bash
# OpenCode로 변경된 파일 자동 개선
CHANGED_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep '\.py$')

if [ -n "$CHANGED_FILES" ]; then
  echo "🤖 OpenCode: Checking Python files..."
  opencode --provider ollama --model qwen2.5-coder:7b \
    "Add missing docstrings and type hints to: $CHANGED_FILES"

  # 변경사항을 스테이징에 자동 추가
  git add $CHANGED_FILES
fi
```
- [ ] Pre-commit hook 스크립트 작성
- [ ] Docstring/Type hints 자동 추가 검증
- [ ] 커밋 메시지 거버넌스 검증 (.ai-rules.md)
- [ ] 결과물: Git Hook 자동 설치 스크립트

### Phase 4: 문서 동기화 (2 Days)
```bash
# Cron job (매시간 실행)
0 * * * * opencode "Sync docs/api/openapi.yaml with src/api/routes/"
0 9 * * * opencode "Update BACKLOG.md if docs/issues/ changed"
```
- [ ] OpenAPI 스펙 자동 생성 로직
- [ ] BACKLOG.md ↔ docs/issues/ 양방향 동기화
- [ ] README.md 프로젝트 구조 자동 업데이트
- [ ] 결과물: 문서 불일치 제로 달성

---

## 5. 기술 스택 (Tech Stack)

| 컴포넌트 | 기술 | 사유 |
|---------|------|------|
| **코딩 어시스턴트** | OpenCode CLI | ClaudeCode와 유사한 UX, 75+ LLM 프로바이더 지원 |
| **SLM 엔진** | Ollama + qwen2.5-coder | 코딩 특화 모델, CPU 최적화 |
| **추천 모델** | qwen2.5-coder:7b / 32b | 7B: 빠른 작업, 32B: 복잡한 작업 |
| **Agent 런타임** | Node.js 20 | OpenCode 네이티브 환경 |
| **스케줄링** | Bash cron + while loop | 단순하고 안정적 |
| **컨테이너 모니터링** | docker CLI + OpenCode 분석 | 기존 도구 재활용 |
| **Git 연동** | Git Hooks (pre-commit) | 네이티브 Git 기능 |
| **Redis 클라이언트** | redis-cli + Bash | 경량 통합 |

### 모델 비교

| 모델 | 크기 | RAM | 코드 생성 | Docstring | 속도 | 추천 용도 |
|------|------|-----|-----------|-----------|------|-----------|
| `qwen2.5-coder:7b` | 4.7GB | 8GB | ⭐⭐⭐ | ⭐⭐⭐⭐ | 빠름 | 일반 작업 |
| `qwen2.5-coder:32b` | 19GB | 32GB | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 느림 | 복잡한 리팩토링 |
| `deepseek-coder-v2:16b` | 9GB | 16GB | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 보통 | 균형잡힌 선택 |

---

## 6. 리스크 및 완화 전략 (Risks & Mitigation)

### Risk 1: 코드 품질 저하 (Hallucination)
- **현상**: OpenCode가 잘못된 코드를 생성할 가능성
- **완화**:
  - Git Pre-commit hook에서 생성 → 사람 검토 후 커밋
  - 자동 커밋 금지, 항상 `git diff`로 확인
  - 테스트 통과를 필수 조건으로 설정
- **검증**: pytest 자동 실행, 실패 시 변경사항 롤백

### Risk 2: 리소스 과다 사용
- **현상**: Ollama 모델이 서버 메모리 고갈 유발
- **완화**:
  - Docker 메모리 제한: 7B 모델 = 8GB, 32B 모델 = 32GB
  - CPU 제한: 2-4 cores
  - Sentinel Agent가 Ollama/OpenCode 리소스 모니터링
- **Fallback**: OOM 발생 시 자동 재시작

### Risk 3: 문서 동기화 오류
- **현상**: OpenAPI 스펙이 실제 코드와 불일치
- **완화**:
  - 생성된 문서를 PR로 제출 (자동 머지 금지)
  - JSON Schema validator로 OpenAPI 유효성 검증
  - 주간 수동 리뷰 프로세스 유지
- **검증**: CI/CD에서 스펙 유효성 자동 체크

### Risk 4: ClaudeCode와 작업 충돌
- **현상**: 동시에 같은 파일 수정 시 충돌
- **완화**:
  - **명확한 역할 분담**:
    - ClaudeCode: 비즈니스 로직, 아키텍처 (사람이 직접 실행)
    - OpenCode: 문서화, 코드 품질 (자동 실행)
  - OpenCode는 주석/docstring만 수정, 로직 변경 금지
  - Git lock 메커니즘 활용
- **규칙**: OpenCode 자동 실행 시 파일 잠금 체크

### Risk 5: 보안 이슈 (로그 내 민감 정보)
- **현상**: OpenCode가 로그를 분석하면서 API 키 노출
- **완화**:
  - 로그 수집 전 정규식으로 민감 정보 마스킹
  - `.*_KEY|.*_SECRET|.*_TOKEN` 패턴 자동 필터링
  - OpenCode 프롬프트에 "민감 정보를 출력하지 마세요" 명시
- **검증**: Security 페르소나 필수 리뷰

---

## 7. 성공 지표 (Success Metrics)

### KPI 1: 문서 동기화 지연 감소
- **현재**: 평균 2-3일 지연
- **목표**: 24시간 이내 자동 업데이트

### KPI 2: 컨테이너 이상 탐지 시간
- **현재**: 수동 점검, 30분~2시간 지연
- **목표**: 5분 이내 자동 감지 및 알림

### KPI 3: 거버넌스 위반 조기 발견
- **현재**: 머지 후 발견 (롤백 비용 높음)
- **목표**: 커밋 시점에 80% 차단

### KPI 4: ClaudeCode 작업 효율
- **측정**: 작업 시작 전 컨텍스트 수집 시간
- **목표**: 5분 → 30초 단축

---

## 8. 다음 단계 (Next Steps)

### Immediate Actions
1. **기술 검증** (1-2 Days)
   - Ollama 로컬 설치 및 모델 테스트
   - `docker stats` 파싱 스크립트 작성
   - 샘플 로그에 대한 SLM 요약 성능 측정

2. **RFC 작성 여부 결정**
   - PoC 결과가 긍정적이면 `/create-rfc` 호출
   - 부정적이면 아이디어 보류 (ARCHIVE 이동)

3. **Council Review** (Optional)
   - 6인 페르소나 의견 수렴 (`/council-review`)
   - 특히 Architect, Security 페르소나 리뷰 필수

---

## 9. 참고 자료 (References)

### 외부 자료
- [OpenCode Official Docs](https://opencode.ai/docs/)
- [OpenCode + Ollama Integration Guide](https://blog.codeminer42.com/setting-up-a-free-claude-like-assistant-with-opencode-and-ollama/)
- [Ollama Documentation](https://ollama.ai/docs)
- [Qwen2.5-Coder Model Card](https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct)
- [OpenCode GitHub Examples](https://github.com/p-lemonish/ollama-x-opencode)

### 내부 문서
- `docs/governance/.ai-rules.md` (거버넌스 규칙)
- `deploy/docker-compose.yml` (컨테이너 구조)
- `docs/ideas/ID-sentinel-tagging.md` (Sentinel 모니터링)
- `BACKLOG.md` (프로젝트 백로그)

### 관련 블로그/튜토리얼
- [Free AI Coding: Ollama + OpenCode](https://kamilkwapisz.com/blog/free-ai-coding-ollama-opencode)
- [OpenCode with Ollama locally (Docker)](https://medium.com/@michael.harms_57592/opencode-with-ollama-locally-docker-container-included-b136f8179bc8)

---

## 10. 의견 수렴 (Persona Feedback)

### Developer
- ✅ **찬성**: OpenCode가 ClaudeCode 대안으로 완벽. 문서 자동화 정말 필요.
- ⚠️ **우려**: Ollama 모델 용량 (7B=4.7GB, 32B=19GB) 서버 디스크 여유 확인 필요.
- 💡 **제안**: 로컬(Mac)에서 먼저 7B 모델 테스트, 만족스러우면 서버에 배포.

### Architect
- ✅ **찬성**: OpenCode가 표준 CLI라서 통합 쉬움. 아키텍처 깔끔.
- 💡 **제안**:
  - ClaudeCode와 역할 명확히 분리 (문서 vs 로직)
  - Redis 채널: `opencode.*` 네임스페이스 사용
  - Git Hook은 옵션으로, 강제하지 말 것 (개발자 선택)

### Security
- ⚠️ **우려**: SLM이 로그를 읽으면서 민감 정보(API 키 등) 노출 가능성.
- 📌 **요구사항**: 로그 수집 전 민감 정보 마스킹 필터 필수.

### Data Scientist
- 💡 **제안**: SLM이 시계열 메트릭을 분석해서 이상 패턴 탐지하면 좋겠음.
- 🔍 **질문**: 컨테이너 메트릭을 TimescaleDB에 저장하고 있나? 그럼 쿼리해서 분석 가능.

### PM
- ✅ **승인**: P2 우선순위 적절. ISSUE-014(외부 모니터링)와 시너지 있음.
- 📅 **일정**: Phase 1 PoC 완료 후 다시 리뷰하자.

### QA
- 📌 **요구사항**: 생성된 문서의 정확성 검증 로직 필요.
- 🧪 **테스트 계획**: SLM 출력물에 대한 Unit Test 작성 (OpenAPI 스펙 유효성).

---

## 11. 관련 이슈 및 로드맵 (Related Issues)

- **ISSUE-014**: 외부 모니터링 대시보드 (시너지 높음)
- **ID-sentinel-tagging**: Sentinel 이벤트 태깅 (컨텍스트 공유 가능)
- **ID-state-awareness-workflow**: AI 상태 인지 워크플로우 (통합 후보)

---

## 12. 승격 조건 (Promotion Criteria)

이 아이디어가 **Mature** 상태로 승격되려면:
- [ ] **PoC 성공**: Mac에서 OpenCode + Ollama 설치 및 기본 기능 확인
  - Docstring 생성 품질 평가 (5개 함수 테스트)
  - 리소스 사용량 측정 (qwen2.5-coder:7b 기준)
  - 응답 속도 측정 (평균 < 10초)
- [ ] **Docker 통합**: 프로덕션 서버에서 컨테이너 실행 성공
  - Ollama 서비스 안정성 (24시간 무중단)
  - OpenCode Agent 자동 재시작 검증
- [ ] **보안 승인**: Security 페르소나 리뷰 통과
  - 로그 내 민감 정보 마스킹 확인
  - Docker 권한 최소화 적용
- [ ] **역할 분담 합의**: ClaudeCode와 충돌 없는 워크플로우 정립
  - Git Hook 옵션화 (개발자가 활성화 선택)
  - 자동 커밋 금지 정책 문서화

**Mature 달성 시** → `/create-rfc ID-opencode-ollama-backend`로 RFC 작성

---

## 13. 빠른 시작 가이드 (Quick Start)

### Mac (로컬 테스트)
```bash
# 1. Ollama 설치
brew install ollama
ollama serve  # 백그라운드 실행

# 2. 모델 다운로드
ollama pull qwen2.5-coder:7b

# 3. OpenCode 설치
npm install -g @opencodehq/opencode

# 4. 프로젝트에서 테스트
cd ~/workspace/stock_monitoring
opencode --provider ollama --model qwen2.5-coder:7b

# 5. 예제 명령
opencode "Add docstrings to src/api/main.py"
opencode "List all TODO comments in src/"
```

### Production (Linux 서버)
```bash
# 1. docker-compose.yml 업데이트 (Phase 2 참조)

# 2. 모델 사전 다운로드 (시간 소요)
docker run --rm -v ollama-models:/root/.ollama ollama/ollama \
  ollama pull qwen2.5-coder:7b

# 3. 서비스 시작
docker-compose up -d ollama opencode-agent

# 4. 로그 확인
docker logs -f opencode-agent
```
