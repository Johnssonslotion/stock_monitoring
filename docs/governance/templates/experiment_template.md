# 🧪 Experiment Record: [Title]

> **Experiment ID**: EXP-[XXX] (Sequential)
> **Date**: YYYY-MM-DD
> **Status**: [Draft / In-Progress / Concluded / Rejected]
> **Related Rules**: `.ai-rules.md` Rule [X.X]

## 1. Hypothesis (가설)
- **Problem**: [Describe the problem concisely]
- **Proposed Solution**: [Describe what you are testing]
- **Expected Outcome**: [Quantitative metric, e.g., Latency < 50ms]

## 2. Experimental Setup (실험 환경)
- **Target**: [Specific Service/Container/Module]
- **Tools**: [e.g., Locust, pytest, manual script]
- **Variables**:
    - Control Group: [Current state]
    - Experimental Group: [New configuration]

## 3. Results & Observations (결과)
> ⚠️ **Mandatory**: Include raw data or screenshots (Charts/Logs).

### 3.1 Quantitative Metrics (정량 지표)
| Metric | Control (Before) | Experiment (After) | Change (%) |
| :--- | :--- | :--- | :--- |
| **Latency (p95)** | 100ms | 45ms | ⬇️ 55% |
| **CPU Usage** | 40% | 42% | ⬆️ 2% |
| **Error Rate** | 0.1% | 0.0% | - |

### 3.2 Qualitative Findings (정성적 발견)
- [Finding 1]
- [Finding 2]

## 4. Conclusion & Decision (결론)
- **Verdict**: [Adopt / Reject / Pivot]
- **Next Steps**:
    1.  [Action Item 1]
    2.  [Action Item 2]

## 5. Artifacts
- **Code**: `src/path/to/implementation.py`
- **Tests**: `tests/test_experiment_case.py`
