---
status: DRAFT (PoC 미완료)
description: Delegate repetitive tasks to OpenCode (local LLM executor)
---

# [DRAFT] Workflow: OpenCode Assist

⚠️ **경고**: 이 워크플로우는 아직 구현되지 않았습니다. PoC 테스트 및 검증 후 `.agent/workflows/`로 이동 예정입니다.

이 워크플로우는 ClaudeCode가 **OpenCode**(Ollama 기반 로컬 LLM)에 반복적인 작업을 위임하여 토큰 효율을 극대화하는 프로세스입니다.

---

## Trigger Conditions

다음 상황에서 이 워크플로우를 사용하세요:

- 100개 파일에 docstring 추가 같은 **대량 반복 작업**
- Type hints, Import 정리 등 **코드 품질 개선**
- 프로젝트 분석, 통계 생성 등 **데이터 수집**
- 작업 예상 시간이 **1분 이상**일 때 (토큰 절감)
- 프라이버시가 중요한 코드 (로컬 처리)

---

## Steps

### 1. 작업 평가 및 분해

**Action**: 작업의 복잡도와 예상 시간 평가

```python
# 평가 기준
if task_complexity == "simple" and task_time > 60:
    use_opencode = True
    execution_mode = "async"  # 1분 이상은 비동기
elif task_requires_domain_knowledge:
    use_opencode = False  # ClaudeCode가 직접
elif security_sensitive:
    use_opencode = False  # 보안 코드는 ClaudeCode가 직접
else:
    use_opencode = True
    execution_mode = "sync"
```

**ClaudeCode 판단**:
- "이 작업은 100개 파일에 docstring을 추가하는 작업으로 약 5분 소요됩니다."
- "OpenCode에 위임하시겠습니까? (y/n)"

---

### 2. 작업 위임 (Delegation)

**Action**: OpenCode에 명확한 명령 전달

#### 동기 실행 (< 1분)
```bash
# ClaudeCode가 실행
opencode "Add docstrings to src/api/main.py"

# 결과 즉시 확인
git diff src/api/main.py
```

#### 비동기 실행 (> 1분)
```bash
# 백그라운드 실행
TASK_ID="task-$(date +%Y%m%d-%H%M%S)"
RESULT_FILE="$HOME/.opencode/results/${TASK_ID}.json"

nohup bash -c "
  opencode 'Add docstrings to all files in src/api/'
  echo '{\"task_id\": \"$TASK_ID\", \"status\": \"completed\"}' > $RESULT_FILE
" > /tmp/opencode-${TASK_ID}.log 2>&1 &

# ClaudeCode 즉시 응답
echo "✅ OpenCode 작업 시작됨 (Task ID: $TASK_ID)"
echo "완료되면 '작업 확인해줘'라고 말씀해주세요"
```

**사용자에게 전달**:
- "OpenCode 작업을 백그라운드로 시작했습니다."
- "완료 시 알림을 받으시려면 watcher 스크립트를 실행하세요:"
- `` `nohup ./scripts/opencode_watcher.sh &` ``

---

### 3. 결과 검증 (Validation)

**Action**: 4단계 검증 프로세스

#### Level 1: 자동 검증
```bash
# 변경된 파일 자동 검증
for file in $(git diff --name-only | grep '\.py$'); do
    # 문법 체크
    python -m py_compile "$file" || exit 1

    # 린터
    ruff check "$file" || exit 1

    # 테스트
    pytest "tests/test_$(basename $file)" || echo "⚠️ No tests found"
done
```

#### Level 2: 통계 이상 탐지
```bash
total_changes=$(git diff --numstat | awk '{sum+=$1+$2} END {print sum}')

if [ $total_changes -gt 500 ]; then
    echo "⚠️ Excessive changes detected, manual review required"
fi
```

#### Level 3: ClaudeCode 수동 검토
```
체크리스트:
- [ ] Docstring이 실제 함수 로직과 일치하는가?
- [ ] 보안 취약점 (API 키 노출 등) 없는가?
- [ ] 비즈니스 로직이 변경되지 않았는가?
- [ ] 테스트가 모두 통과하는가?
```

#### Level 4: 샘플링 (대량 작업)
```bash
# 100개 파일 중 10개만 샘플링
changed_files=$(git diff --name-only)
sample=$(echo "$changed_files" | shuf | head -10)

# 샘플 검토 후 전체 승인 여부 결정
```

---

### 4. 승인 또는 거부

**Action**: 검증 결과에 따라 조치

```
IF 모든 검증 통과:
    git add .
    git commit -m "docs: add docstrings via OpenCode"

ELIF 자동 검증 실패:
    → OpenCode 재실행 또는 ClaudeCode가 직접 수정

ELIF 보안 이슈:
    git checkout .
    → "보안 문제 발견, 변경사항 롤백"

ELIF 과도한 변경:
    → 샘플링 검토 또는 작업 분할
```

---

## Example Usage

### Example 1: 프로젝트 전체 문서화

**User**: "프로젝트 전체에 docstring 추가해줘"

**ClaudeCode**:
```
1. 파일 수 확인: 100개
2. 예상 시간: 5-7분
3. "이 작업은 시간이 걸립니다. 백그라운드로 실행하시겠습니까? (y/n)"

[User: y]

4. nohup opencode "Add docstrings to all Python files in src/" &
5. "✅ 작업 시작 (Task ID: task-20260122-10)"
6. "완료 시 알림 받으시려면: nohup ./scripts/opencode_watcher.sh &"
```

**[5분 후, 사용자가 알림 받음]**

**User**: "작업 확인해줘"

**ClaudeCode**:
```
1. cat ~/.opencode/results/task-20260122-10.json
2. "✅ 100개 파일에 docstring 추가 완료"
3. git diff --stat (요약)
4. pytest (자동 검증)
5. "수동 검토하시겠습니까? (샘플 10개)"

[User: y]

6. 샘플 10개 diff 표시
7. "승인하시겠습니까? (y/n)"

[User: y]

8. git add . && git commit
9. "✅ 커밋 완료"
```

---

### Example 2: Type Hints 추가

**User**: "모든 함수에 type hints 추가해줘"

**ClaudeCode**:
```
1. 파일 수 확인: 50개
2. 예상 시간: 2-3분
3. "백그라운드로 실행합니다"
4. nohup opencode "Add type hints to all function signatures" &
5. "완료되면 알려드리겠습니다"
```

---

## Integration Notes

### Watcher Script 설정

**자동 시작 (launchd)**:
```xml
<!-- ~/Library/LaunchAgents/com.user.opencode-watcher.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.opencode-watcher</string>
    <key>ProgramArguments</key>
    <array>
        <string>/path/to/scripts/opencode_watcher.sh</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
```

```bash
launchctl load ~/Library/LaunchAgents/com.user.opencode-watcher.plist
```

---

## Best Practices

### ✅ Good: 명확한 범위와 스타일
```bash
opencode "Add Google-style docstrings to functions in src/api/routes/*.py"
opencode "Add type hints using typing module to src/data_ingestion/"
opencode "Organize imports using isort style in all Python files"
```

### ❌ Bad: 모호하거나 복잡한 명령
```bash
opencode "코드 개선해줘"  # 너무 모호
opencode "아키텍처 재설계해줘"  # ClaudeCode가 직접 해야 함
opencode "버그 수정해줘"  # 복잡한 로직, ClaudeCode 필요
```

---

## Exceptions (OpenCode 사용 금지)

다음 작업은 **ClaudeCode가 직접** 수행해야 합니다:

1. **보안 관련**: 인증, 권한, 암호화 로직
2. **비즈니스 로직**: 거래 알고리즘, 결제 처리
3. **아키텍처 설계**: 모듈 구조 변경
4. **복잡한 버그**: 순환 참조, 메모리 누수
5. **데이터베이스**: 마이그레이션, 스키마 변경

---

## Token Efficiency

### 동기 실행 (5분 작업)
```
ClaudeCode API 세션 유지: 5분
토큰 사용: ~50,000 tokens
비용: ~$0.75
```

### 비동기 실행
```
Session 1 (작업 시작): 10초 = ~500 tokens
[OpenCode 백그라운드: 5분 = 0 tokens]
Session 2 (결과 확인): 30초 = ~2,000 tokens

총 토큰: ~2,500 tokens
비용: ~$0.04

절감: 95%
```

---

## Related Documents

- [거버넌스 정책](../../docs/governance/claude_opencode_integration.md)
- [아이디어 문서](../../docs/ideas/claude/ID-ollama-slm-backend-assistant.md)
- [오케스트레이션 예시](../../docs/ideas/claude/ORCHESTRATION_EXAMPLES.md)
- [통신 프로토콜](../../docs/ideas/claude/COMMUNICATION_PROTOCOL.md)
- [비동기 패턴](../../docs/ideas/claude/ASYNC_EXECUTION_PATTERN.md)

---

## Changelog

### v1.0 (2026-01-22)
- Initial workflow definition
- 4-level validation strategy
- Async execution pattern
- Token efficiency optimization
