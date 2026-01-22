# ClaudeCode Hook 제약사항 및 대안

## ❌ 불가능한 것: ClaudeCode가 Hook을 받기

### 근본적인 아키텍처 제약

```
ClaudeCode = Stateless Request-Response 모델

┌─────────────────────────────────────┐
│  User 입력                           │
│       ↓                              │
│  ClaudeCode API 호출                 │
│       ↓                              │
│  응답 생성 및 반환                    │
│       ↓                              │
│  세션 종료 (메모리 해제)              │
└─────────────────────────────────────┘

❌ 백그라운드 상주 불가능
❌ 이벤트 리스너 불가능
❌ Hook/Callback 수신 불가능
```

**왜 불가능한가?**
1. **Stateless**: 각 요청은 독립적, 이전 세션 정보 없음
2. **API 기반**: 요청이 올 때만 활성화
3. **비용 모델**: 대기 시간 = 토큰 소모 = 비용

---

## ✅ 가능한 대안들

### Option 1: 외부 Watcher + 사용자 알림 (추천)

**구조**:
```
OpenCode 백그라운드 실행
        ↓
[작업 진행 중...]
        ↓
결과 파일 생성 (~/.opencode/results/task-001.json)
        ↓
Watcher Script 감지 (fswatch/inotify)
        ↓
macOS Notification 발송
        ↓
사용자가 알림 보고 수동으로 ClaudeCode 실행
        ↓
ClaudeCode가 결과 파일 읽고 분석
```

**장점**:
- ✅ 토큰 0 소모 (ClaudeCode 대기 안 함)
- ✅ 사용자가 원할 때 확인
- ✅ 구현 단순

**단점**:
- ⚠️ 자동화 아님 (사용자 개입 필요)

**실행 방법**:
```bash
# Terminal 1: OpenCode 작업 시작
nohup opencode "Add docstrings to src/" > ~/.opencode/results/task-001.json 2>&1 &

# Terminal 2: Watcher 실행
./scripts/opencode_watcher.sh

# [작업 완료 시 macOS 알림 받음]

# Terminal 1: ClaudeCode로 결과 확인
claude "OpenCode 작업 결과 확인해줘"
```

---

### Option 2: fswatch + 자동 ClaudeCode 트리거

**구조**:
```
fswatch ~/.opencode/results/
        ↓
파일 생성 감지
        ↓
자동으로 새로운 ClaudeCode 세션 실행
  claude "Task task-001 결과 분석해줘"
```

**구현**:
```bash
#!/bin/bash
# auto_trigger_claudecode.sh

RESULT_DIR="$HOME/.opencode/results"

fswatch -0 "$RESULT_DIR" | while read -d "" event; do
    if [[ "$event" == *.json ]]; then
        task_id=$(basename "$event" .json)

        echo "🔔 새 결과 파일 감지: $task_id"

        # 자동으로 ClaudeCode 실행 (새 세션)
        claude "OpenCode task $task_id 의 결과를 분석하고 요약해줘. 파일 경로: $event"
    fi
done
```

**장점**:
- ✅ 완전 자동화
- ✅ 사용자 개입 불필요

**단점**:
- ⚠️ ClaudeCode CLI 명령어가 매번 새 세션 = 컨텍스트 없음
- ⚠️ 사용자가 원하지 않을 때도 실행됨

---

### Option 3: MCP (Model Context Protocol) 활용 (미래)

**개념**:
Claude Desktop App이 지원하는 MCP를 통해 파일 시스템 이벤트를 감지

```
┌──────────────────────────────────┐
│  Claude Desktop (MCP Server)     │
├──────────────────────────────────┤
│  File System Watcher (MCP Tool)  │
│       ↓                           │
│  파일 생성 감지                    │
│       ↓                           │
│  ClaudeCode에 "이벤트" 전달       │
│       ↓                           │
│  ClaudeCode: "새 결과 파일 있음"  │
└──────────────────────────────────┘
```

**현재 상태**: MCP는 도구 제공 프로토콜이지 푸시 이벤트 시스템은 아님

**가능성**: 향후 MCP가 WebSocket 같은 실시간 채널 지원 시 가능?

---

## 💡 현실적인 워크플로우

### 시나리오: 대량 docstring 추가 (5분 소요)

#### Step 1: 작업 시작 (ClaudeCode Session 1)
```
User: "프로젝트 전체에 docstring 추가해줘"

ClaudeCode:
  - 파일 수 확인: 100개
  - 예상 시간: 5-7분
  - "백그라운드로 실행하시겠습니까? (y/n)"

User: "y"

ClaudeCode:
  - nohup opencode "..." > ~/.opencode/results/task-20260122-10.json &
  - "✅ 작업 시작됨 (Task ID: task-20260122-10)"
  - "watcher 스크립트 실행 중이면 완료 시 알림 받으실 수 있습니다"
  - [세션 종료]
```

#### Step 2: 대기 (Watcher가 감시 중)
```
[5분 경과...]

Watcher Script:
  - 파일 생성 감지
  - macOS 알림: "✅ OpenCode 작업 완료"
```

#### Step 3: 결과 확인 (ClaudeCode Session 2)
```
User: (알림 받고) "작업 확인해줘"

ClaudeCode:
  - cat ~/.opencode/results/task-20260122-10.json
  - "✅ 100개 파일에 docstring 추가 완료"
  - git diff --stat 요약
  - "자동 검증 결과: pytest 통과 ✅"
  - "수동 검토하시겠습니까?"
  - [세션 종료]
```

**토큰 사용량**:
- Session 1: ~1,000 tokens
- Session 2: ~3,000 tokens
- **총**: ~4,000 tokens
- **절감**: 동기 방식(~50,000 tokens) 대비 92% 절감

---

## 🔧 실전 구현

### 1. Watcher 스크립트 백그라운드 실행

**터미널에서**:
```bash
# 백그라운드로 watcher 실행 (세션 독립)
nohup ./scripts/opencode_watcher.sh > ~/.opencode/watcher.log 2>&1 &

# PID 확인
echo $! > ~/.opencode/watcher.pid

# 로그 모니터링
tail -f ~/.opencode/watcher.log
```

**또는 launchd로 자동 시작 (macOS)**:
```xml
<!-- ~/Library/LaunchAgents/com.user.opencode-watcher.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.opencode-watcher</string>

    <key>ProgramArguments</key>
    <array>
        <string>/Users/bbagsang-u/workspace/stock_monitoring/scripts/opencode_watcher.sh</string>
    </array>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>StandardOutPath</key>
    <string>/Users/bbagsang-u/.opencode/watcher.log</string>

    <key>StandardErrorPath</key>
    <string>/Users/bbagsang-u/.opencode/watcher-error.log</string>
</dict>
</plist>
```

```bash
# launchd 등록
launchctl load ~/Library/LaunchAgents/com.user.opencode-watcher.plist

# 중지
launchctl unload ~/Library/LaunchAgents/com.user.opencode-watcher.plist
```

---

### 2. ClaudeCode와 통합

**ClaudeCode가 작업 시작 시**:
```bash
# 1. Watcher 실행 여부 확인
if pgrep -f "opencode_watcher.sh" > /dev/null; then
    echo "✅ Watcher 실행 중 - 완료 시 알림 받으실 수 있습니다"
else
    echo "⚠️ Watcher 미실행 - 수동으로 확인하셔야 합니다"
    echo "   실행: nohup ./scripts/opencode_watcher.sh &"
fi

# 2. OpenCode 백그라운드 실행
# ...
```

---

## 📊 방법 비교

| 방법 | 자동화 | 토큰 효율 | 구현 난이도 | 사용자 개입 |
|------|--------|-----------|------------|-----------|
| **동기 실행** | ❌ | ❌ (최악) | ✅ 쉬움 | 없음 |
| **비동기 + 수동 확인** | ⚠️ 반자동 | ✅ 최고 | ✅ 쉬움 | 수동 확인 필요 |
| **Watcher + 알림** | ✅ 자동 | ✅ 최고 | ⚠️ 보통 | 알림 후 실행 |
| **자동 트리거** | ✅ 완전 자동 | ✅ 높음 | ❌ 어려움 | 없음 (원치 않을 수도) |

---

## 결론

### ClaudeCode는 Hook을 받을 수 없지만...

**대안**:
1. **Watcher Script**가 파일 시스템 감시
2. OpenCode 완료 시 **사용자에게 알림**
3. 사용자가 **수동으로** ClaudeCode 재실행

**이것이 현재로서는 최선**:
- ✅ 토큰 효율 극대화
- ✅ 사용자가 제어 가능
- ✅ 구현 단순

**향후 개선 방향**:
- MCP 발전 시 실시간 이벤트 가능?
- Claude Desktop App 통합?
- 하지만 현재로서는 "Watcher + 알림" 방식 추천
