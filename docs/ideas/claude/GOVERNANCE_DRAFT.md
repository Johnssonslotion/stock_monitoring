# [DRAFT] ClaudeCode + OpenCode Integration Policy

**Version**: 0.1 (Draft)
**Status**: ⚠️ DRAFT - PoC 미완료, 승인 전
**Created**: 2026-01-22
**Category**: Development Workflow

---

## ⚠️ 경고

이 정책은 **검증되지 않은 초안**입니다.
실제 PoC 테스트 및 검증 후 정식 승인 필요합니다.

**승인 조건**:
- [ ] OpenCode 설치 및 실행 성공
- [ ] 간단한 작업 (1-2개 파일) 품질 검증
- [ ] 토큰 절감 효과 실측
- [ ] 보안 검토 (민감 정보 처리)
- [ ] Council Review 통과

**승인 후 이동 경로**: `docs/governance/claude_opencode_integration.md`

---

---

## 1. 개요 (Overview)

ClaudeCode와 OpenCode를 **오케스트레이터-실행자(Orchestrator-Executor)** 관계로 통합하여 개발 효율성을 극대화하고 토큰 비용을 절감하는 정책.

### 핵심 원칙
```
ClaudeCode (Orchestrator)
    ↓ 전략 수립 및 명령
OpenCode (Executor)
    ↓ 작업 실행 및 결과 반환
ClaudeCode (Reviewer)
    ↓ 검증 및 승인
```

---

## 2. 역할 분담 (Role Separation)

### 2.1 ClaudeCode의 역할
- ✅ **전략적 의사결정**: 아키텍처 설계, 복잡한 비즈니스 로직
- ✅ **작업 분해**: 큰 작업을 OpenCode가 처리 가능한 단위로 분할
- ✅ **명령 생성**: 구체적이고 명확한 OpenCode 프롬프트 작성
- ✅ **결과 검증**: OpenCode 출력물의 품질 평가 (자동 + 수동)
- ✅ **정밀 보완**: OpenCode가 놓친 복잡한 부분 직접 수정

### 2.2 OpenCode의 역할
- ✅ **대량 작업**: 100개 파일에 docstring 추가 등 반복 작업
- ✅ **코드 품질**: Type hints 추가, Import 정리, 스타일 통일
- ✅ **데이터 수집**: 프로젝트 분석, 통계 생성, 패턴 탐지
- ✅ **문서 동기화**: OpenAPI 스펙 생성, README 업데이트
- ✅ **로컬 실행**: 프라이버시가 중요한 코드는 로컬에서만 처리

---

## 3. 통신 프로토콜 (Communication Protocol)

### 3.1 기본: Bash 표준 입출력
**용도**: 빠른 작업 (< 1분)

```bash
# ClaudeCode가 실행
result=$(opencode "Add docstrings to src/api/main.py")

# 결과 확인
if [ $? -eq 0 ]; then
    echo "Success: $result"
else
    echo "Failed, manual intervention needed"
fi
```

### 3.2 파일 기반: JSON 결과
**용도**: 대량 데이터, 구조화된 결과

```bash
opencode "Analyze project and save to /tmp/report.json"
jq '.summary' /tmp/report.json
```

### 3.3 비동기 실행: Background + Notification
**용도**: 느린 작업 (> 1분) → 토큰 절감

```bash
# 백그라운드 실행
nohup opencode "..." > ~/.opencode/results/task-001.json 2>&1 &

# Watcher가 완료 시 알림
# (사용자가 나중에 ClaudeCode로 확인)
```

---

## 4. 결과 평가 전략 (Evaluation Strategy)

### Level 1: 자동 검증 (Fast Fail)
```bash
# 문법 체크
python -m py_compile changed_file.py

# 린터
ruff check changed_file.py

# 테스트
pytest tests/test_changed_file.py

# 모두 통과 → OK, 하나라도 실패 → ClaudeCode 개입
```

### Level 2: 통계 이상 탐지
```bash
# 변경량 체크
total_changes=$(git diff --numstat | awk '{sum+=$1+$2} END {print sum}')

if [ $total_changes -gt 500 ]; then
    echo "⚠️ Excessive changes, manual review required"
fi
```

### Level 3: ClaudeCode 수동 검증
- **비즈니스 로직 일치**: Docstring이 실제 코드와 일치하는가?
- **보안**: API 키, 비밀번호 노출 여부
- **품질**: 코드 스타일, 아키텍처 일관성

### Level 4: 샘플링 (대량 작업)
- 100개 파일 변경 시 10개만 샘플링하여 검토
- 샘플 통과 시 전체 승인

---

## 5. 토큰 효율성 (Token Efficiency)

### 문제: 동기 실행의 비효율
```
ClaudeCode → opencode 실행 (5분)
    ↓
[대기 중... 토큰 계속 소모]
    ↓
결과 반환
```

**비용**: 5분 대기 = ~50,000 tokens = ~$0.75

### 해결: 비동기 실행
```
Session 1: 작업 시작 (10초)
    "백그라운드로 실행했습니다"
    토큰: ~500

[OpenCode 백그라운드: 5분]
    (ClaudeCode 세션 종료 = 토큰 0)

Session 2: 결과 확인 (30초)
    "완료되었습니다"
    토큰: ~2,000
```

**비용**: ~2,500 tokens = ~$0.04 (95% 절감)

---

## 6. 워크플로우 가이드라인

### 6.1 작업 시작 판단
```
IF 작업 예상 시간 < 10초:
    → 동기 실행 OK
ELIF 작업 예상 시간 > 1분:
    → 비동기 실행 필수
    → 사용자에게 예상 시간 알림
    → "백그라운드로 실행하시겠습니까?"
```

### 6.2 결과 검증 순서
```
1. OpenCode 실행
2. 자동 검증 (pytest, ruff)
3. 통계 분석 (git diff)
4. ClaudeCode 수동 검토 (필요 시)
5. 승인/거부 결정
```

### 6.3 실패 처리
```
IF 자동 검증 실패:
    → OpenCode 재실행 또는 ClaudeCode가 직접 수정
ELIF 보안 이슈 발견:
    → 즉시 거부, git checkout
ELIF 과도한 변경:
    → 샘플링 검토
```

---

## 7. 문서 위치 (Documentation)

모든 OpenCode 관련 아이디어 및 구현 문서는 `docs/ideas/claude/`에 저장:

- **ID-ollama-slm-backend-assistant.md**: 메인 아이디어 문서
- **ORCHESTRATION_EXAMPLES.md**: 실전 예시 5가지
- **COMMUNICATION_PROTOCOL.md**: 통신 프로토콜 상세
- **ASYNC_EXECUTION_PATTERN.md**: 비동기 실행 패턴
- **HOOK_LIMITATIONS.md**: Hook 제약사항 및 대안

---

## 8. 도구 및 스크립트

### 8.1 Watcher Script
```bash
# 백그라운드로 OpenCode 작업 감시
nohup ./scripts/opencode_watcher.sh > ~/.opencode/watcher.log 2>&1 &

# 완료 시 macOS 알림 발송
```

### 8.2 자동 검증 스크립트
```bash
./scripts/validate_opencode_output.sh <file>
# → pytest, ruff, mypy 실행
# → 통과 시 exit 0, 실패 시 exit 1
```

---

## 9. Best Practices

### ✅ Good Patterns
```bash
# 명확한 범위 지정
opencode "Add docstrings to functions in src/api/routes/*.py"

# 구체적인 스타일 요구
opencode "Add Google-style docstrings with Args, Returns, Examples"

# 결과 검증 가능
opencode "..." && git diff src/api/ | head -50
```

### ❌ Anti-Patterns
```bash
# 너무 모호한 명령
opencode "코드 개선해줘"

# OpenCode 능력 초과
opencode "복잡한 순환 참조 해결해줘"  # ClaudeCode가 직접

# 결과 검증 없이 맹신
opencode "..." && git add . && git commit  # 위험!
```

---

## 10. 예외 사항 (Exceptions)

다음 작업은 OpenCode에 위임하지 않고 **ClaudeCode가 직접** 수행:

1. **보안 관련 코드**: 인증, 권한, 암호화
2. **비즈니스 로직**: 거래 알고리즘, 결제 로직
3. **아키텍처 변경**: 모듈 구조 재설계
4. **데이터베이스 마이그레이션**: 스키마 변경
5. **복잡한 버그 수정**: 순환 참조, 메모리 누수

---

## 11. 향후 개선 (Roadmap)

### Phase 1 (현재)
- ✅ 파일 기반 비동기 실행
- ✅ Watcher 스크립트
- ✅ 기본 자동 검증

### Phase 2 (1개월)
- [ ] Redis Pub/Sub 통합
- [ ] 대시보드에서 OpenCode 작업 모니터링
- [ ] 자동 검증 스크립트 강화

### Phase 3 (3개월)
- [ ] MCP (Model Context Protocol) 연동 실험
- [ ] 서버 백엔드 OpenCode daemon 배포
- [ ] 통계 기반 이상 탐지 자동화

---

## 12. 참고 자료 (References)

- [OpenCode Official Docs](https://opencode.ai/docs/)
- [Ollama Documentation](https://ollama.ai/docs)
- [Qwen2.5-Coder Model](https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct)
- 내부 문서: `docs/ideas/claude/`

---

## 변경 이력 (Changelog)

### v1.0 (2026-01-22)
- 초기 정책 수립
- 오케스트레이터-실행자 패턴 정의
- 통신 프로토콜 3가지 정립
- 4단계 평가 전략 수립
