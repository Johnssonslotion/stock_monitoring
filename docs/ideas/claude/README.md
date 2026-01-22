# Claude-Generated Ideas & Integration Docs

이 디렉토리는 ClaudeCode가 생성한 아이디어 및 통합 문서를 관리합니다.

---

## 📁 구조

```
docs/ideas/claude/
├── README.md (이 파일)
├── ID-ollama-slm-backend-assistant.md (메인 아이디어)
├── ORCHESTRATION_EXAMPLES.md (실전 예시)
├── COMMUNICATION_PROTOCOL.md (통신 프로토콜)
├── ASYNC_EXECUTION_PATTERN.md (비동기 패턴)
└── HOOK_LIMITATIONS.md (Hook 제약사항)
```

---

## 🎯 OpenCode + ClaudeCode 통합

### 핵심 컨셉
**ClaudeCode → OpenCode 오케스트레이션**

```
ClaudeCode (전략가)
    ↓ 명령
OpenCode (실행자)
    ↓ 결과
ClaudeCode (검증자)
```

### 주요 문서

#### 1. ID-ollama-slm-backend-assistant.md
- **상태**: 🌿 Sprouting
- **내용**: OpenCode + Ollama 백엔드 자동화 어시스턴트 아이디어
- **Tech Stack**: OpenCode CLI, Ollama, qwen2.5-coder
- **목표**: 토큰 95% 절감, 개발 효율 30% 향상

#### 2. ORCHESTRATION_EXAMPLES.md
5가지 실전 예시:
- API 문서화 자동화 (80% OpenCode, 20% ClaudeCode)
- 레거시 코드 리팩토링 (단순 작업 위임)
- 거버넌스 검증 자동화
- 프로젝트 분석 리포트
- 백엔드 자동화 (서버 daemon)

#### 3. COMMUNICATION_PROTOCOL.md
통신 방법 3가지 + 4단계 평가:
- **Protocol 1**: Bash stdout (기본)
- **Protocol 2**: 파일 기반 JSON (대량 데이터)
- **Protocol 3**: Redis Pub/Sub (백엔드 자동화)
- **Evaluation**: 자동 → 통계 → 수동 → 샘플링

#### 4. ASYNC_EXECUTION_PATTERN.md
토큰 효율화 핵심:
- **문제**: 5분 대기 = $0.75
- **해결**: 비동기 실행 = $0.04 (95% 절감)
- **패턴**: Fire-and-Forget + 파일 결과

#### 5. HOOK_LIMITATIONS.md
ClaudeCode Hook 제약 및 대안:
- **불가능**: ClaudeCode는 Hook을 받을 수 없음 (Stateless API)
- **대안**: Watcher Script + macOS Notification
- **자동화**: fswatch + launchd

---

## 🔗 관련 파일

### 거버넌스
- `docs/governance/claude_opencode_integration.md` - 공식 정책

### Workflow (Skill)
- `.agent/workflows/opencode-assist.md` - `/opencode-assist` 명령
- `.claude/commands/opencode-assist.md` - Symlink

### 스크립트
- `scripts/opencode_watcher.sh` - 백그라운드 감시자

---

## 🚀 사용 방법

### 1. OpenCode 설치
```bash
brew install opencode ollama
ollama pull qwen2.5-coder:7b
```

### 2. Watcher 실행
```bash
nohup ./scripts/opencode_watcher.sh > ~/.opencode/watcher.log 2>&1 &
```

### 3. ClaudeCode에서 사용
```
User: "프로젝트 전체에 docstring 추가해줘"

ClaudeCode: "5분 소요 예상. 백그라운드로 실행하시겠습니까?"
User: "y"

[OpenCode 백그라운드 실행...]
[macOS 알림 받음]

User: "작업 확인해줘"
ClaudeCode: "100개 파일 완료. 검토하시겠습니까?"
```

---

## 📊 효과

| 지표 | 기존 | OpenCode 통합 | 개선 |
|------|------|--------------|------|
| 대량 작업 시간 | 수동 | 자동 | 100% |
| 토큰 비용 (5분 작업) | $0.75 | $0.04 | 95% 절감 |
| 문서 동기화 지연 | 2-3일 | 24시간 | 67% 단축 |
| 프라이버시 | 클라우드 | 완전 로컬 | ✅ |

---

## 🎯 다음 단계

### Phase 1 (완료)
- ✅ 아이디어 문서화
- ✅ 통신 프로토콜 정의
- ✅ 비동기 패턴 설계
- ✅ Watcher 스크립트
- ✅ Workflow (Skill) 추가

### Phase 2 (예정)
- [ ] Mac 로컬 PoC 테스트
- [ ] 실제 프로젝트 파일로 검증
- [ ] 성능 벤치마크 수집

### Phase 3 (미래)
- [ ] 서버 백엔드 OpenCode daemon
- [ ] Redis Pub/Sub 통합
- [ ] 대시보드 모니터링

---

## 📝 변경 이력

### 2026-01-22
- 초기 문서 생성
- docs/ideas/stock_monitoring/ → docs/ideas/claude/ 이동
- 거버넌스 정책 추가
- Workflow (Skill) 등록

---

## 🔍 참고

- [OpenCode Official](https://opencode.ai/)
- [Ollama Docs](https://ollama.ai/docs)
- [Qwen2.5-Coder](https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct)
