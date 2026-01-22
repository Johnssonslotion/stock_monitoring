# ClaudeCode → OpenCode Orchestration Examples

이 문서는 ClaudeCode가 OpenCode를 **실행 도구**로 활용하는 구체적인 예시를 보여줍니다.

---

## Pattern: ClaudeCode가 OpenCode에 명령하는 구조

```
User Request
     ↓
ClaudeCode (전략 수립)
     ↓
OpenCode (작업 실행)
     ↓
ClaudeCode (결과 검증)
     ↓
최종 완성
```

---

## Example 1: API 문서화 자동화

### 사용자 요청
"API 코드를 전부 문서화해줘"

### ClaudeCode의 전략
```
1. [분석] src/api/ 구조 파악
2. [위임] OpenCode로 기본 docstring 생성
3. [검증] 복잡한 함수는 직접 보완
4. [통합] 최종 커밋
```

### ClaudeCode 실행 코드
```bash
# Step 1: 파일 구조 파악
ls -R src/api/

# Step 2: OpenCode에 작업 위임
opencode "Add comprehensive Google-style docstrings to all functions in src/api/"

# Step 3: 결과 검토
git diff src/api/

# Step 4: 복잡한 비즈니스 로직 함수는 ClaudeCode가 직접 개선
# (OpenCode가 생성한 일반적인 docstring을 더 상세하게)
```

### OpenCode가 생성한 것 (80%)
```python
def calculate_profit(trades: List[Trade]) -> float:
    """Calculate total profit from trades.

    Args:
        trades: List of trade objects

    Returns:
        Total profit amount
    """
    return sum(t.profit for t in trades)
```

### ClaudeCode가 보완한 것 (20%)
```python
def calculate_profit(trades: List[Trade]) -> float:
    """Calculate total profit from trades with tax consideration.

    This function aggregates profits from all trades and applies
    the current tax rate defined in the portfolio settings.
    Negative values indicate losses.

    Args:
        trades: List of Trade objects with .profit attribute.
                Each trade must be settled (status='closed').

    Returns:
        float: Net profit after tax deduction.
               Formula: sum(profits) * (1 - tax_rate)

    Raises:
        ValueError: If any trade has status != 'closed'

    Example:
        >>> trades = [Trade(profit=100), Trade(profit=-50)]
        >>> calculate_profit(trades)
        45.0  # (100-50) * (1-0.1) with 10% tax
    """
    if any(t.status != 'closed' for t in trades):
        raise ValueError("All trades must be closed")

    gross_profit = sum(t.profit for t in trades)
    tax_rate = get_tax_rate()
    return gross_profit * (1 - tax_rate)
```

**역할 분담**:
- OpenCode: 기본 구조 생성 (빠르고 무료)
- ClaudeCode: 도메인 지식 추가 (정확하고 맥락 이해)

---

## Example 2: 레거시 코드 리팩토링

### 사용자 요청
"프로젝트 전체 코드 품질을 개선해줘"

### ClaudeCode의 전략
```
Phase 1: OpenCode로 기계적 작업 (10분)
  - Type hints 추가
  - Import 정리
  - 미사용 변수 제거

Phase 2: ClaudeCode로 구조적 개선 (30분)
  - 순환 의존성 해결
  - 중복 코드 통합
  - 아키텍처 개선
```

### ClaudeCode 실행 순서

#### Phase 1: OpenCode 대량 작업
```bash
# 1. Type hints 추가 (100개 파일, OpenCode가 처리)
opencode "Add type hints to all function signatures in src/"

# 2. Import 정리 (OpenCode가 처리)
opencode "Sort and optimize imports across all Python files"

# 3. 미사용 코드 제거 (OpenCode가 처리)
opencode "Remove unused imports and variables marked by linters"

# 결과 검토
git diff --stat
```

#### Phase 2: ClaudeCode 정밀 작업
```
# ClaudeCode가 직접:
1. 순환 import 수동 해결
2. 중복 로직을 유틸리티로 추출
3. 복잡한 함수 분해
4. 테스트 보강
```

---

## Example 3: 거버넌스 검증 자동화

### 사용자 요청
"커밋 전에 .ai-rules.md 규칙 준수 여부 확인해줘"

### ClaudeCode의 전략
```
1. [분석] .ai-rules.md 규칙 파싱
2. [위임] OpenCode로 코드 스캔
3. [판단] 위반 사항 심각도 평가
4. [조치] 자동 수정 vs 경고 결정
```

### ClaudeCode 실행 코드
```bash
# Step 1: 거버넌스 규칙 확인
cat docs/governance/.ai-rules.md

# Step 2: OpenCode로 위반 사항 탐지
opencode "Scan all staged files for governance violations based on .ai-rules.md"

# Step 3: 결과 분석 및 조치
# (OpenCode가 반환한 위반 목록을 ClaudeCode가 평가)

# Step 4: 자동 수정 가능한 것은 OpenCode에 재위임
opencode "Fix import ordering violations in src/api/main.py"
```

---

## Example 4: 프로젝트 분석 리포트

### 사용자 요청
"현재 프로젝트 상태를 요약해줘"

### ClaudeCode의 전략
```
1. [위임] OpenCode로 통계 수집
2. [분석] 수치를 바탕으로 인사이트 도출
3. [보고] 사용자에게 전달
```

### ClaudeCode 실행 코드
```bash
# OpenCode로 데이터 수집
opencode "Analyze the project structure and provide statistics:
- Total lines of code by language
- Number of functions without docstrings
- Test coverage estimation
- Complexity metrics (cyclomatic complexity)
- Dependency graph overview"

# OpenCode 결과를 받아 ClaudeCode가 해석
# "통계를 보니 테스트 커버리지가 낮습니다. 특히 data_ingestion 모듈의
#  critical path에 테스트가 없어 위험합니다..."
```

---

## Example 5: 백엔드 자동화 (서버에서 실행)

### 배경
프로덕션 서버에서 OpenCode가 daemon으로 실행 중

### ClaudeCode가 원격으로 명령
```bash
# SSH를 통해 서버의 OpenCode에 명령
ssh stock-prod "docker exec opencode-agent opencode \
  'Analyze container logs from last 1 hour and detect anomalies'"

# 결과를 받아 ClaudeCode가 판단
# "kis-service 컨테이너에서 connection timeout이 3회 발생했습니다.
#  네트워크 설정을 확인하시겠습니까?"
```

---

## Pattern Summary

### ClaudeCode의 역할
- 🧠 **전략 수립**: 무엇을, 왜, 어떤 순서로
- 📋 **작업 분해**: 큰 작업을 OpenCode가 처리 가능한 단위로
- 🎯 **명령 생성**: 구체적이고 명확한 OpenCode 프롬프트
- ✅ **결과 검증**: OpenCode 출력물의 품질 평가
- 🔧 **정밀 보완**: OpenCode가 놓친 복잡한 부분 직접 수정

### OpenCode의 역할
- ⚡ **빠른 실행**: 대량 작업을 로컬에서 즉시 처리
- 💰 **무제한 시도**: 비용 부담 없이 여러 번 실행
- 📊 **데이터 수집**: 프로젝트 스캔, 통계, 패턴 탐지
- 🔁 **반복 작업**: 100개 파일에 동일 작업 적용
- 🛡️ **프라이버시**: 민감한 코드를 로컬에서만 처리

---

## Orchestration Best Practices

### ✅ Good Patterns
```bash
# 명확한 범위 지정
opencode "Add docstrings to functions in src/api/routes/*.py"

# 구체적인 스타일 요구
opencode "Add Google-style docstrings with Args, Returns, and Examples"

# 결과 검증 가능
opencode "..." && git diff src/api/ | head -50
```

### ❌ Anti-Patterns
```bash
# 너무 모호한 명령
opencode "코드 개선해줘"  # OpenCode가 무엇을 해야 할지 모름

# OpenCode 능력 초과
opencode "복잡한 순환 참조 해결해줘"  # ClaudeCode가 직접 해야 함

# 결과 검증 없이 맹신
opencode "..." && git add . && git commit  # 위험!
```

---

## Conclusion

**ClaudeCode → OpenCode 오케스트레이션**은:
- ClaudeCode의 전략적 사고
- OpenCode의 빠른 실행력

을 결합하여 **최고의 효율**을 만들어냅니다.

**핵심**: OpenCode는 ClaudeCode의 "하위 도구"가 아니라 **전문화된 실행 엔진**입니다.
