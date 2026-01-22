# 비동기 실행 패턴 (Async Execution Pattern)

## 문제 정의

### 현재 설계의 토큰 비효율성
```
ClaudeCode API 요청
    ↓
opencode "대량 작업 실행" (동기 실행)
    ↓
[⏳ 5분 대기... 토큰 계속 소모]
    ↓
결과 반환
    ↓
ClaudeCode 응답
```

**비용 예시**:
- OpenCode 5분 실행 = ClaudeCode API 세션 5분 유지
- Sonnet 4.5: $3/1M input tokens, $15/1M output tokens
- 5분 대기 = 불필요한 토큰 소모

---

## 해결 방안: 비동기 작업 큐

### Pattern 1: Background Execution + File Results

#### 아키텍처
```
Session 1 (작업 시작) - 10초 소요
    ClaudeCode: "opencode 작업을 백그라운드로 시작했습니다"
    토큰 사용: ~500 tokens

    ↓ (ClaudeCode 세션 종료)

[OpenCode 백그라운드 작업: 5분]
    결과 저장: ~/.opencode/results/2026-01-22-task-001.json

    ↓ (사용자가 원할 때)

Session 2 (결과 확인) - 30초 소요
    ClaudeCode: 파일 읽고 분석
    토큰 사용: ~2000 tokens

총 토큰: ~2500 tokens (5분 대기 0 tokens!)
```

#### ClaudeCode 실행 코드

**Session 1: 작업 시작**
```bash
#!/bin/bash
# claudecode_start_async_task.sh

TASK_ID="task-$(date +%Y%m%d-%H%M%S)"
RESULT_DIR="$HOME/.opencode/results"
RESULT_FILE="$RESULT_DIR/${TASK_ID}.json"

mkdir -p "$RESULT_DIR"

# 백그라운드 실행 (nohup으로 세션 독립)
nohup bash -c "
  echo '{\"status\": \"running\", \"task_id\": \"$TASK_ID\", \"started_at\": \"$(date -Iseconds)\"}' > $RESULT_FILE

  # OpenCode 실행 (결과를 파일로 캡처)
  result=\$(opencode 'Add docstrings to all files in src/api/' 2>&1)
  exit_code=\$?

  # 결과 JSON 저장
  echo '{
    \"task_id\": \"$TASK_ID\",
    \"status\": \"completed\",
    \"exit_code\": '\$exit_code',
    \"completed_at\": \"'$(date -Iseconds)'\",
    \"result\": \"'\$result'\"
  }' > $RESULT_FILE
" > /tmp/opencode-${TASK_ID}.log 2>&1 &

# PID 저장
echo $! > "$RESULT_DIR/${TASK_ID}.pid"

# ClaudeCode 즉시 응답
echo "✅ OpenCode 작업 시작됨"
echo "📋 Task ID: $TASK_ID"
echo "📁 결과 파일: $RESULT_FILE"
echo ""
echo "💡 작업 완료 후 다음 명령으로 결과 확인:"
echo "   cat $RESULT_FILE"
```

**Session 2: 결과 확인**
```bash
#!/bin/bash
# claudecode_check_results.sh

RESULT_DIR="$HOME/.opencode/results"

# 모든 작업 상태 확인
echo "📊 OpenCode 작업 현황:"
echo ""

for file in "$RESULT_DIR"/*.json; do
    [ -e "$file" ] || continue

    task_id=$(jq -r '.task_id' "$file")
    status=$(jq -r '.status' "$file")

    case $status in
        "running")
            echo "⏳ $task_id: 실행 중..."
            ;;
        "completed")
            exit_code=$(jq -r '.exit_code' "$file")
            if [ "$exit_code" -eq 0 ]; then
                echo "✅ $task_id: 성공"
                echo "   결과: $(jq -r '.result' "$file" | head -3)..."
            else
                echo "❌ $task_id: 실패 (exit code: $exit_code)"
            fi
            ;;
    esac
done

echo ""
echo "💡 특정 작업 상세 확인: cat $RESULT_DIR/task-XXXXXX.json"
```

---

### Pattern 2: Hook-Based Callback

#### 아키텍처
```
ClaudeCode → opencode 시작 (백그라운드)
                ↓
          [작업 실행 중...]
                ↓
     작업 완료 시 hook 실행
                ↓
   hook: "echo 'DONE' >> ~/.opencode/notifications"
                ↓
ClaudeCode: 주기적으로 notifications 파일 확인
          (또는 사용자가 수동으로 확인)
```

#### 구현

**OpenCode 완료 Hook**
```bash
#!/bin/bash
# opencode_with_hook.sh

TASK_ID=$1
COMMAND=$2
NOTIFICATION_FILE="$HOME/.opencode/notifications"

{
    # OpenCode 실행
    opencode "$COMMAND"
    EXIT_CODE=$?

    # 완료 알림 (Hook)
    echo "$(date -Iseconds)|$TASK_ID|$EXIT_CODE|COMPLETED" >> "$NOTIFICATION_FILE"
} &

echo "Task $TASK_ID started in background"
```

**ClaudeCode 체크**
```bash
#!/bin/bash
# check_notifications.sh

NOTIFICATION_FILE="$HOME/.opencode/notifications"

if [ ! -f "$NOTIFICATION_FILE" ]; then
    echo "📭 알림 없음"
    exit 0
fi

echo "📬 새 알림:"
cat "$NOTIFICATION_FILE"

# 읽은 후 파일 비우기
> "$NOTIFICATION_FILE"
```

---

### Pattern 3: Watch + inotify (리눅스)

**OpenCode 결과 디렉토리 감시**

```bash
#!/bin/bash
# watch_opencode_results.sh

RESULT_DIR="$HOME/.opencode/results"

# inotify로 파일 생성 감지
inotifywait -m -e create "$RESULT_DIR" | while read path action file; do
    if [[ "$file" == *.json ]]; then
        echo "🔔 새 결과 파일 생성됨: $file"

        # ClaudeCode를 자동으로 트리거 (선택적)
        # 또는 단순히 알림만
        osascript -e 'display notification "OpenCode 작업 완료" with title "ClaudeCode"'
    fi
done
```

---

## 토큰 효율성 비교

### Scenario: 100개 파일에 docstring 추가 (OpenCode 5분 소요)

| 방식 | ClaudeCode 대기 시간 | 토큰 사용량 | 비용 (Sonnet 4.5) |
|------|---------------------|------------|------------------|
| **동기 실행** | 5분 | ~50,000 tokens | ~$0.75 |
| **비동기 (Pattern 1)** | 0분 (즉시 종료) | ~2,500 tokens | ~$0.04 |
| **절약** | 5분 | ~47,500 tokens | ~$0.71 (95% 절감) |

---

## 실전 워크플로우

### Use Case: 프로젝트 전체 문서화

**ClaudeCode Session 1 (10초)**
```
User: "프로젝트 전체에 docstring 추가해줘"

ClaudeCode:
  1. 작업 규모 파악 (100개 파일)
  2. "이 작업은 5-10분 소요될 것 같습니다"
  3. 백그라운드로 OpenCode 실행
  4. "작업 시작했습니다. Task ID: task-20260122-103000"
  5. 세션 종료
```

**[OpenCode 백그라운드: 7분]**

**User가 나중에 확인**
```
User: "OpenCode 작업 완료됐어?"

ClaudeCode Session 2 (20초):
  1. cat ~/.opencode/results/task-20260122-103000.json
  2. "✅ 완료되었습니다. 100개 파일에 docstring 추가됨"
  3. git diff --stat 요약
  4. "검토하시겠습니까?"
  5. 세션 종료
```

**총 토큰**: ~3,000 tokens (동기 방식 대비 95% 절감)

---

## 자동화 레벨

### Level 1: 수동 확인 (기본)
```
ClaudeCode: "작업 시작했습니다"
   ↓
[사용자 대기]
   ↓
User: "확인해줘"
   ↓
ClaudeCode: "완료됐습니다"
```

### Level 2: 폴링 스크립트
```bash
# check_opencode_loop.sh
while true; do
    if [ -f ~/.opencode/results/task-*.json ]; then
        status=$(jq -r '.status' ~/.opencode/results/task-*.json)
        if [ "$status" = "completed" ]; then
            echo "🔔 OpenCode 완료!"
            break
        fi
    fi
    sleep 30
done
```

### Level 3: Webhook (고급)
```
OpenCode 완료 → curl POST → Claude.ai API → 사용자에게 알림
```

---

## 구현 우선순위

### Phase 1: 파일 기반 비동기 (즉시 구현 가능)
```bash
# ClaudeCode가 실행
nohup opencode "..." > /tmp/result.txt 2>&1 &
echo "작업 시작. 나중에 cat /tmp/result.txt 하세요"
```

### Phase 2: 구조화된 작업 큐
- Task ID 관리
- JSON 결과 저장
- 상태 추적

### Phase 3: 알림 시스템
- macOS Notification
- Slack webhook
- 이메일 알림

---

## ClaudeCode 대화 패턴

### 동기 작업 (빠른 작업 < 10초)
```
User: "src/api/main.py에 docstring 추가해줘"

ClaudeCode:
  opencode "Add docstrings to src/api/main.py"
  [10초 대기]
  "✅ 완료. 5개 함수에 docstring 추가됨"
```

### 비동기 작업 (느린 작업 > 1분)
```
User: "프로젝트 전체에 docstring 추가해줘"

ClaudeCode:
  "이 작업은 약 5분 소요됩니다."
  "백그라운드로 실행하시겠습니까? (y/n)"

  [User: y]

  nohup opencode "..." &
  "✅ 작업 시작 (Task ID: task-001)"
  "완료되면 '작업 확인해줘'라고 말씀해주세요"
  [세션 즉시 종료]
```

---

## Conclusion

**핵심 원칙**:
1. **빠른 작업 (< 10초)**: 동기 실행 OK
2. **느린 작업 (> 1분)**: 무조건 비동기
3. **사용자 선택**: 작업 시작 전 예상 시간 알려주고 선택하게

**토큰 절감**:
- 동기 5분 대기 = $0.75
- 비동기 즉시 종료 = $0.04
- **95% 절감**

ClaudeCode는 "시작"과 "검증"만 하고,
**대기는 하지 않는다** = 토큰 효율 극대화
