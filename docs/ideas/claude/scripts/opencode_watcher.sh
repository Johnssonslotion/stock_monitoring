#!/bin/bash
# OpenCode 작업 완료 감시 스크립트
# ClaudeCode와 독립적으로 실행되며, 작업 완료 시 사용자에게 알림

RESULT_DIR="$HOME/.opencode/results"
CHECK_INTERVAL=30  # 30초마다 체크

echo "🔍 OpenCode 작업 감시 시작..."
echo "📁 감시 디렉토리: $RESULT_DIR"
echo "⏱️  체크 간격: ${CHECK_INTERVAL}초"
echo ""

# 초기 파일 목록
mkdir -p "$RESULT_DIR"
initial_files=$(ls -1 "$RESULT_DIR"/*.json 2>/dev/null | wc -l)

while true; do
    current_files=$(ls -1 "$RESULT_DIR"/*.json 2>/dev/null)

    for file in $current_files; do
        # 파일이 존재하고 읽을 수 있는지 확인
        if [ ! -f "$file" ]; then
            continue
        fi

        # 상태 확인
        status=$(jq -r '.status' "$file" 2>/dev/null || echo "unknown")

        if [ "$status" = "completed" ]; then
            task_id=$(jq -r '.task_id' "$file" 2>/dev/null)
            exit_code=$(jq -r '.exit_code' "$file" 2>/dev/null)

            # 이미 알림 보낸 작업인지 확인 (마커 파일)
            marker_file="${file}.notified"
            if [ -f "$marker_file" ]; then
                continue
            fi

            echo "✅ 작업 완료 감지: $task_id"

            # macOS 알림
            if [ "$exit_code" -eq 0 ]; then
                osascript -e "display notification \"Task ID: $task_id\" with title \"✅ OpenCode 작업 완료\" sound name \"Glass\""
            else
                osascript -e "display notification \"Task ID: $task_id (실패)\" with title \"❌ OpenCode 작업 실패\" sound name \"Basso\""
            fi

            # 터미널 출력
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo "🔔 OpenCode 작업 완료 알림"
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo "Task ID: $task_id"
            echo "종료 코드: $exit_code"
            echo "결과 파일: $file"
            echo ""
            echo "💡 ClaudeCode에서 다음 명령으로 확인:"
            echo "   cat $file"
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

            # 알림 완료 마커 생성
            touch "$marker_file"
        fi
    done

    sleep $CHECK_INTERVAL
done
