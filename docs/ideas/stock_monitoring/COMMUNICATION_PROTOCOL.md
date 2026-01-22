# ClaudeCode ↔ OpenCode 통신 프로토콜 및 평가 전략

이 문서는 ClaudeCode가 OpenCode를 오케스트레이션할 때 사용하는 **통신 방법**과 **결과 평가 전략**을 정의합니다.

---

## 1. 통신 프로토콜 (Communication Protocol)

### Protocol 1: Bash 표준 입출력 (기본)

**용도**: 단순하고 빠른 작업 (docstring 추가, import 정리 등)

#### ClaudeCode 실행 패턴
```bash
# 기본 실행
opencode "Add docstrings to src/api/main.py"

# 결과 캡처
result=$(opencode "Analyze BACKLOG.md and summarize P0 tasks")
echo "$result"

# 성공 여부 확인
if [ $? -eq 0 ]; then
    git add src/api/main.py
else
    echo "OpenCode failed, manual intervention needed"
fi
```

#### OpenCode 출력 형식
```
✓ Analyzed src/api/main.py
✓ Added 15 docstrings to functions
✓ Added 3 class docstrings

Changes:
  - Added Google-style docstrings
  - Inferred types from function signatures
  - Added example usage where complex

Next steps:
  - Review changes with 'git diff src/api/main.py'
  - Run tests to verify no breakage
```

**장점**:
- 즉시 결과 확인
- 추가 인프라 불필요
- Bash tool 네이티브 지원

**단점**:
- stdout 버퍼 제한 (대용량 출력 시)
- 진행 상황 모니터링 어려움

---

### Protocol 2: 파일 기반 통신

**용도**: 대량 데이터, 구조화된 결과 (프로젝트 분석, 통계 리포트 등)

#### ClaudeCode 실행 패턴
```bash
# 결과를 파일로 저장하도록 명령
opencode "Analyze entire project and save report to /tmp/project-report.md"

# 파일 읽기
cat /tmp/project-report.md

# JSON 형식으로 구조화된 결과
opencode "Count functions without docstrings and output JSON to /tmp/stats.json"
jq '.missing_docstrings[] | .file' /tmp/stats.json
```

#### OpenCode 출력 예시 (JSON)
```json
{
  "task": "docstring_analysis",
  "timestamp": "2026-01-22T10:30:00Z",
  "stats": {
    "total_functions": 245,
    "with_docstrings": 180,
    "without_docstrings": 65,
    "coverage": "73.5%"
  },
  "missing_docstrings": [
    {"file": "src/api/main.py", "function": "calculate_profit", "line": 42},
    {"file": "src/data_ingestion/archiver.py", "function": "archive_tick", "line": 128}
  ]
}
```

**장점**:
- 대용량 결과물 처리
- 구조화된 데이터 (jq로 파싱)
- 결과 재사용 가능

**단점**:
- 파일 정리 필요
- 동시 실행 시 파일명 충돌

---

### Protocol 3: Redis Pub/Sub (백엔드 자동화)

**용도**: 서버에서 OpenCode가 daemon으로 실행될 때 (장기 실행 작업)

#### 아키텍처
```
ClaudeCode (Publisher)
     │
     ├─▶ Redis: "opencode.tasks" (작업 요청)
     │
     ▼
OpenCode Agent (Subscriber)
     │
     ├─▶ 작업 실행
     │
     ├─▶ Redis: "opencode.results" (결과 발행)
     │
     ▼
ClaudeCode (Subscriber) → 결과 수신
```

#### ClaudeCode 실행 패턴
```python
import redis
import json
import uuid

redis_client = redis.Redis()

# 작업 요청 발행
task_id = str(uuid.uuid4())
task = {
    "id": task_id,
    "command": "Add docstrings to all files in src/api/",
    "priority": "high"
}
redis_client.publish("opencode.tasks", json.dumps(task))

# 결과 대기
pubsub = redis_client.pubsub()
pubsub.subscribe("opencode.results")

for message in pubsub.listen():
    if message['type'] == 'message':
        result = json.loads(message['data'])
        if result['task_id'] == task_id:
            print(f"OpenCode completed: {result['summary']}")
            break
```

**장점**:
- 비동기 실행 (ClaudeCode가 블록되지 않음)
- 여러 작업 병렬 처리
- 진행 상황 실시간 모니터링

**단점**:
- Redis 인프라 필요
- 복잡도 증가

---

## 2. 결과 평가 전략 (Evaluation Strategy)

### Level 1: 자동 검증 (Fast Fail)

**목적**: 명백한 오류를 빠르게 탐지

```bash
#!/bin/bash
# validate_opencode_output.sh

FILE=$1

# 1. 문법 체크
echo "🔍 Syntax check..."
python -m py_compile "$FILE" || exit 1

# 2. Import 순환 참조 체크
echo "🔍 Import cycle check..."
pydeps "$FILE" --max-bacon 2 > /dev/null || echo "⚠️ Potential cycle detected"

# 3. 린터 체크
echo "🔍 Linting..."
ruff check "$FILE" || exit 1

# 4. 타입 체크 (선택적)
echo "🔍 Type checking..."
mypy "$FILE" --ignore-missing-imports || echo "⚠️ Type issues found"

# 5. 테스트 실행 (해당 파일에 대한 테스트)
echo "🧪 Running tests..."
pytest "tests/test_$(basename $FILE)" -v || exit 1

echo "✅ All automated checks passed"
```

#### ClaudeCode 사용 예시
```bash
# OpenCode 실행
opencode "Add type hints to src/api/main.py"

# 자동 검증
./scripts/validate_opencode_output.sh src/api/main.py

if [ $? -eq 0 ]; then
    echo "✅ Auto-validation passed, proceeding to manual review"
else
    echo "❌ Auto-validation failed, reverting changes"
    git checkout src/api/main.py
fi
```

---

### Level 2: 통계 기반 이상 탐지

**목적**: 과도하거나 의심스러운 변경 탐지

```bash
#!/bin/bash
# detect_anomalies.sh

# 변경 통계 수집
stats=$(git diff --numstat src/api/main.py)
added=$(echo "$stats" | awk '{print $1}')
deleted=$(echo "$stats" | awk '{print $2}')
total=$((added + deleted))

echo "📊 Change statistics:"
echo "  Added: $added lines"
echo "  Deleted: $deleted lines"
echo "  Total: $total lines"

# 이상 탐지 규칙
if [ $total -gt 500 ]; then
    echo "⚠️ ALERT: Excessive changes (>500 lines)"
    echo "   → Manual review REQUIRED"
    exit 1
fi

if [ $deleted -gt $((added * 2)) ]; then
    echo "⚠️ ALERT: More deletions than additions"
    echo "   → Possible data loss, review carefully"
    exit 1
fi

# Docstring만 추가되었는지 확인 (로직 변경은 없어야 함)
logic_changes=$(git diff src/api/main.py | grep -E '^\+.*def |^\+.*return |^\+.*if ' | wc -l)
if [ $logic_changes -gt 5 ]; then
    echo "⚠️ ALERT: Logic changes detected (expected only docstrings)"
    echo "   → OpenCode may have modified business logic"
    exit 1
fi

echo "✅ Statistics look normal"
```

---

### Level 3: ClaudeCode 수동 검증

**목적**: 비즈니스 로직 정확성 및 보안 검토

#### ClaudeCode의 체크리스트
```python
REVIEW_CHECKLIST = {
    "문법 정확성": {
        "method": "자동 검증 (pytest, ruff)",
        "threshold": "100% pass",
        "action": "자동 승인"
    },
    "비즈니스 로직 일치": {
        "method": "ClaudeCode 수동 검토",
        "threshold": "Docstring이 실제 코드와 일치",
        "action": "git diff 읽고 판단"
    },
    "보안 취약점": {
        "method": "정규식 스캔 + ClaudeCode 판단",
        "patterns": ["API_KEY", "password", "secret", "eval(", "exec("],
        "action": "발견 시 즉시 거부"
    },
    "코드 스타일": {
        "method": "자동 검증 (black, ruff)",
        "threshold": "100% compliant",
        "action": "자동 승인"
    },
    "테스트 커버리지": {
        "method": "pytest-cov",
        "threshold": "새 코드 80% 이상",
        "action": "미달 시 ClaudeCode가 테스트 추가"
    }
}
```

#### ClaudeCode 실행 플로우
```
1. OpenCode 실행
   ↓
2. 자동 검증 (Level 1)
   ↓
3. 통계 이상 탐지 (Level 2)
   ↓
4. IF 이상 없음:
     - 변경 < 50 lines → 자동 승인
     - 변경 > 50 lines → ClaudeCode가 git diff 읽기
   ↓
5. ClaudeCode 판단:
     - ✅ 승인 → git add & commit
     - ⚠️ 조건부 승인 → 일부 수정 후 commit
     - ❌ 거부 → git checkout (원복)
```

---

### Level 4: 샘플링 전략 (대량 작업)

**목적**: 100개 파일 변경 시 모두 검토 불가능, 대표 샘플만 검증

```bash
#!/bin/bash
# sampling_review.sh

SAMPLE_SIZE=10  # 10개만 샘플링

# 변경된 파일 목록
changed_files=$(git diff --name-only)
total_count=$(echo "$changed_files" | wc -l)

echo "📊 Total changed files: $total_count"

if [ $total_count -gt 50 ]; then
    echo "⚠️ Too many files to review manually"
    echo "🎲 Sampling $SAMPLE_SIZE files for review..."

    # 무작위 샘플링
    sample=$(echo "$changed_files" | shuf | head -$SAMPLE_SIZE)

    echo "Selected sample:"
    echo "$sample"

    # 샘플만 ClaudeCode가 정밀 검토
    for file in $sample; do
        echo "═══════════════════════════════"
        echo "Reviewing: $file"
        echo "═══════════════════════════════"
        git diff "$file"
        echo ""
        read -p "Approve this file? (y/n): " answer
        if [ "$answer" != "y" ]; then
            echo "❌ Sample review failed, rejecting entire batch"
            exit 1
        fi
    done

    echo "✅ Sample review passed, approving all $total_count files"
else
    echo "✅ File count manageable, full review recommended"
fi
```

---

## 3. 실전 예시: 완전한 플로우

### 사용자 요청
"프로젝트 전체에 docstring 추가해줘"

### ClaudeCode 실행 스크립트
```bash
#!/bin/bash
set -e

echo "🚀 Starting project-wide docstring addition..."

# Step 1: OpenCode 실행
echo "📝 Step 1: OpenCode execution"
opencode "Add comprehensive Google-style docstrings to all Python functions in src/"

# Step 2: 자동 검증
echo "🔍 Step 2: Automated validation"
for file in $(git diff --name-only | grep '\.py$'); do
    python -m py_compile "$file" || {
        echo "❌ Syntax error in $file, reverting..."
        git checkout .
        exit 1
    }
done

# Step 3: 통계 분석
echo "📊 Step 3: Statistical analysis"
total_changes=$(git diff --numstat | awk '{sum+=$1+$2} END {print sum}')
echo "Total changes: $total_changes lines"

if [ $total_changes -gt 2000 ]; then
    echo "⚠️ Large changeset detected, using sampling strategy"
    bash ./scripts/sampling_review.sh || exit 1
fi

# Step 4: 테스트 실행
echo "🧪 Step 4: Running tests"
pytest tests/ -v || {
    echo "❌ Tests failed, reverting..."
    git checkout .
    exit 1
}

# Step 5: ClaudeCode 최종 검토
echo "👀 Step 5: Manual review by ClaudeCode"
echo "Changed files:"
git diff --stat

read -p "Approve and commit? (y/n): " final_approval
if [ "$final_approval" = "y" ]; then
    git add .
    git commit -m "docs: add docstrings to all functions via OpenCode

Generated by OpenCode (qwen2.5-coder:7b)
Reviewed and approved by ClaudeCode

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
    echo "✅ Changes committed successfully"
else
    echo "❌ Changes rejected, reverting..."
    git checkout .
fi
```

---

## 4. 프로토콜 선택 가이드

| 상황 | 추천 프로토콜 | 이유 |
|------|--------------|------|
| 단일 파일 docstring 추가 | Bash 표준 입출력 | 빠르고 간단 |
| 프로젝트 전체 분석 | 파일 기반 (JSON) | 구조화된 대용량 결과 |
| 서버 백엔드 모니터링 | Redis Pub/Sub | 비동기, 실시간 |
| 100개 파일 동시 처리 | Bash + 샘플링 | 효율적 검증 |
| 보안 민감 작업 | Bash + Level 3 검증 | 수동 검토 필수 |

---

## 5. 향후 개선 방향

### Phase 1 (현재)
- Bash 표준 입출력으로 기본 구현
- 자동 검증 스크립트 작성

### Phase 2 (1개월 후)
- 파일 기반 JSON 프로토콜 추가
- 샘플링 전략 자동화

### Phase 3 (3개월 후)
- Redis Pub/Sub 백엔드 통합
- 대시보드에서 OpenCode 작업 모니터링

---

## 6. Conclusion

**핵심 원칙**:
1. **Trust but Verify**: OpenCode 결과를 신뢰하되, 항상 검증
2. **Defense in Depth**: 다층 검증 (자동 → 통계 → 수동)
3. **Fail Fast**: 명백한 오류는 즉시 탐지하고 중단
4. **Sample Wisely**: 대량 작업은 샘플링으로 효율화

ClaudeCode는 OpenCode를 **신뢰할 수 있는 도구**로 활용하되,
**최종 책임과 판단**은 항상 ClaudeCode가 가져야 합니다.
