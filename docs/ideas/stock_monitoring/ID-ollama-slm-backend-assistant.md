# IDEA: Ollama SLM Backend Assistant

**Status**: 🌿 Sprouting (Drafting)
**Priority**: P2
**Category**: Infrastructure, DevOps
**Created**: 2026-01-22
**Owner**: Developer + Architect

---

## 1. 개요 (Abstract)

### 문제 정의
현재 시스템은 다음과 같은 반복적인 수동 작업들로 인해 개발 효율성이 저하되고 있습니다:
- 컨테이너 내부 상태를 수동으로 확인하고 리포트 작성
- API 문서와 코드 간 불일치 발생 (수동 동기화 필요)
- 거버넌스 규칙(.ai-rules.md) 준수 여부를 수동 점검
- 시스템 메트릭 분석 및 이상 징후 탐지의 지연

### 해결 방안
**Ollama 기반 경량 SLM(Small Language Model)**을 프로덕션 백엔드에 통합하여:
- ClaudeCode: 복잡한 설계/구현/리팩토링 담당
- Ollama SLM: 반복적인 문서화 및 모니터링 작업 자동화

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

### 3.1 시스템 구성도

```
┌─────────────────────────────────────────────────────────┐
│                  Production Server (Linux)               │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────┐     ┌──────────────┐                  │
│  │  Ollama      │────▶│  SLM Agent   │                  │
│  │  (qwen2.5:7b)│     │  Container   │                  │
│  └──────────────┘     └───────┬──────┘                  │
│                               │                          │
│                               ├─▶ Monitor Containers     │
│                               ├─▶ Generate Docs          │
│                               └─▶ Report to Redis        │
│                                                           │
│  ┌──────────────────────────────────────────────┐       │
│  │  Existing Containers                         │       │
│  ├──────────────────────────────────────────────┤       │
│  │  kis-service, kiwoom-service, api-server...  │       │
│  └──────────────────────────────────────────────┘       │
│                                                           │
│  ┌──────────────┐     ┌──────────────┐                  │
│  │    Redis     │────▶│  Dashboard   │                  │
│  │ (Pub/Sub Hub)│     │     UI       │                  │
│  └──────────────┘     └──────────────┘                  │
│                                                           │
└─────────────────────────────────────────────────────────┘

         ▲
         │ SSH / ClaudeCode 연동
         │
   ┌─────┴─────┐
   │  Mac Dev  │
   └───────────┘
```

### 3.2 컴포넌트 상세

#### A. Ollama Service
- **모델**: `qwen2.5:7b` 또는 `llama3.1:8b` (CPU 최적화)
- **역할**: SLM 추론 엔진 제공
- **리소스**: 2GB RAM, 1 CPU core

#### B. SLM Agent (New Container)
- **이미지**: `python:3.11-slim` + `ollama` client
- **주요 작업**:
  1. **주기적 상태 수집** (5분 간격)
     - `docker stats` 파싱 (CPU, Memory, Network)
     - `docker logs --tail 100` 에러 패턴 추출

  2. **문서 자동 생성** (Git Hook 트리거)
     - 새 커밋 감지 → 변경된 `.py` 파일 분석
     - Docstring 누락 검출 → PR 코멘트 제안
     - `docs/api/` 하위 OpenAPI 스펙 업데이트

  3. **거버넌스 검증** (Pre-commit Hook)
     - `.ai-rules.md` 규칙 파싱
     - 커밋 메시지, 브랜치명 규칙 검증

  4. **컨텍스트 리포트 생성** (On-Demand)
     - ClaudeCode 요청 시 최근 24h 시스템 상태 요약
     - `context_reports/YYYY-MM-DD.md` 자동 생성

#### C. Redis Integration
- **채널**: `slm.reports`, `slm.alerts`
- **메시지 포맷**:
  ```json
  {
    "type": "container_health",
    "timestamp": "2026-01-22T10:30:00Z",
    "containers": [
      {"name": "kis-service", "cpu": "12%", "memory": "512MB", "status": "healthy"},
      {"name": "api-server", "cpu": "8%", "memory": "256MB", "errors": 0}
    ],
    "summary": "All services running normally. kis-service showing 3 connection retries in last 5min."
  }
  ```

---

## 4. 구현 전략 (Implementation Strategy)

### Phase 1: PoC (1-2 Days)
- [ ] Ollama 설치 및 `qwen2.5:7b` 모델 다운로드
- [ ] 간단한 Python 스크립트로 `docker stats` 데이터 수집
- [ ] SLM에게 "이 로그에서 에러 패턴 찾아줘" 프롬프트 테스트
- [ ] 결과물: 단일 스크립트 실행 데모

### Phase 2: Agent Container (3-4 Days)
- [ ] `slm-agent` 컨테이너 Dockerfile 작성
- [ ] Redis Pub/Sub 연동 (상태 리포트 발행)
- [ ] Cron 스케줄러 구현 (5분 간격 실행)
- [ ] 결과물: `docker-compose.yml`에 통합

### Phase 3: Documentation Automation (5-7 Days)
- [ ] Git Hook 설정 (post-commit, pre-push)
- [ ] Python AST 파서로 API 엔드포인트 추출
- [ ] OpenAPI 스펙 자동 업데이트 로직
- [ ] 결과물: `docs/api/` 자동 동기화

### Phase 4: Governance Validation (2-3 Days)
- [ ] `.ai-rules.md` 파서 구현
- [ ] 커밋 메시지 규칙 검증 (pre-commit hook)
- [ ] 위반 시 경고 메시지 + Slack 알림
- [ ] 결과물: 거버넌스 자동 감시 시스템

---

## 5. 기술 스택 (Tech Stack)

| 컴포넌트 | 기술 | 사유 |
|---------|------|------|
| SLM 엔진 | Ollama + qwen2.5:7b | CPU 최적화, 한국어 지원 우수 |
| Agent 언어 | Python 3.11 | 기존 코드베이스와 일관성 |
| 스케줄링 | APScheduler | 경량 크론 라이브러리 |
| 컨테이너 모니터링 | docker-py | Docker API 직접 호출 |
| Git 연동 | GitPython | 커밋 이벤트 감지 |
| Redis 클라이언트 | redis-py (asyncio) | 기존 인프라 재사용 |

---

## 6. 리스크 및 완화 전략 (Risks & Mitigation)

### Risk 1: SLM 추론 지연 (Latency)
- **완화**: 비동기 작업 큐 사용, 실시간 응답 불필요
- **Fallback**: 추론 타임아웃 5초 설정, 실패 시 기본 템플릿 사용

### Risk 2: 리소스 과다 사용
- **완화**: 메모리 제한 2GB, CPU 1 core로 제한
- **모니터링**: Sentinel Agent가 SLM Agent도 감시

### Risk 3: 잘못된 문서 생성 (Hallucination)
- **완화**: 생성된 문서는 PR로 제출, 사람 리뷰 필수
- **검증**: Unit Test로 OpenAPI 스펙 유효성 검증

### Risk 4: ClaudeCode와 충돌
- **완화**: 명확한 역할 분담 (SLM은 읽기 전용 작업 위주)
- **규칙**: SLM은 코드 수정 금지, 제안만 생성

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

- [Ollama Documentation](https://ollama.ai/docs)
- [Qwen2.5 Model Card](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct)
- [docker-py API](https://docker-py.readthedocs.io/)
- 내부 문서:
  - `docs/governance/.ai-rules.md` (거버넌스 규칙)
  - `docs/architecture/container_layout.md` (컨테이너 구조)
  - `docs/ideas/ID-sentinel-tagging.md` (Sentinel 모니터링)

---

## 10. 의견 수렴 (Persona Feedback)

### Developer
- ✅ **찬성**: 문서 자동화는 정말 필요한 기능. PoC 빠르게 진행해보자.
- ⚠️ **우려**: Ollama 모델 다운로드 용량 큰데 (7B = ~4GB) 서버 디스크 여유 확인 필요.

### Architect
- ✅ **찬성**: SLM이 읽기 전용 작업만 한다면 위험도 낮음.
- 💡 **제안**: ClaudeCode와의 통신 프로토콜 명확히 정의 필요. Redis 채널 분리 추천.

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
- [x] PoC 성공 (SLM이 로그 요약 및 문서 초안 생성 가능)
- [ ] 리소스 사용량 측정 (2GB 메모리 이내)
- [ ] Security 페르소나 승인 (민감 정보 마스킹 확인)
- [ ] ClaudeCode 연동 프로토콜 합의

**Mature 달성 시** → `/create-rfc ID-ollama-slm-backend-assistant`로 RFC 작성
