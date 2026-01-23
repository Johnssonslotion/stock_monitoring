# Incident Report: Market Data Collection Failure (2026-01-08 ~ 01-13)

## 1. Incident Overview
-   **Period**: 2026-01-08 (Thu) ~ 2026-01-13 (Tue)
-   **Impact**:
    -   **Jan 08-09**: Total data loss (0 records).
    -   **Jan 10-11**: Weekend (No market).
    -   **Jan 12**: Normal collection (641k records, likely US market).
    -   **Jan 13 (09:00~10:13 KST)**: KR Market start data loss (~1 hour).
-   **Status**: Resolved (2026-01-13 10:20 KST).

## 2. Root Cause Analysis (RCA)

### Issue A: "The Test Endpoint Illusion" (Jan 08-09)
-   **Cause**: WebSocket URL was configured to `/tryitout/H0STCNT0` (Test Endpoint).
-   **Behavior**: The KIS Test endpoint accepts connections and subscription requests with `200 OK` (Success response), but **does not send any actual tick data**.
-   **Detection**: Discovered on Jan 09 (Commit `2300407`).
-   **Why it lingered**: Logs showed "Connected" and "Subscribed", misleading the team.

### Issue B: "The Race Condition Lie" (Jan 13)
-   **Cause**: When switching from US to KR mode (`switch_url`), the socket is forcibly closed. The scheduler immediately attempted `subscribe_market`.
-   **Defect**: `websocket_base.py`'s `_send_request` method swallowed ConnectionClosed errors.
-   **Critical Failure**: The code caught the error, logged a warning (buried in debug), but **processed the subscription count as successful**.
-   **Result**: The logs shouted `[KR] Subscribed 26 symbols`, causing the scheduler to believe its job was done. In reality, 0 packets were sent.

## 3. Persona Analysis (Responsibility Assessment)
The "Council of Six" failed to function properly.

-   **Developer (Dev)**: **Primary Fault**. Implemented "Fire and Forget" logic in `subscribe_market`. Failing to check a return value from a network operation is a junior-level mistake.
    -   *Verdict*: Competence Check Required.
-   **Quality Assurance (QA)**: **Process Failure**. Relied solely on application logs ("Success") for verification. Did not perform "Deep Verification" (DB Query) until explicitly requested.
    -   *Verdict*: Verification Protocol updated.
-   **Architect (Arch)**: **Design Flaw**. The "Single Socket" constraint was strictly followed, but the "Handover" (switching) logic lacked a handshake or state verification mechanism.
-   **Sentinel (Ops)**: **Silent**. The monitoring system checks for *process health*, not *data throughput*. It saw the process running and stayed silent while data was zero.

## 4. Prevention & Countermeasures (Actionable Items)

### A. Technical Fixes (Implemented)
1.  **Return Value Enforcement**: `_send_request` now returns `bool`. Subscription is only marked successful if this returns `True`.
2.  **Retry Scheduler**: `market_scheduler` now actively checks `active_markets` state and retries indefinitely if the subscription is not confirmed.
3.  **Strict Auth**: Daily API Key refresh at 08:30 KST mandated.

### B. Process Improvements (New Rules)
1.  **Deep Verification Rule** (Added to `ai-rules.md`):
    > "데이터 관련 작업 후에는 로그만 믿지 말고, **반드시 DB를 직접 조회(Query)**하여 교차 검증해야 한다."
2.  **Data-Driven Alerts**: Sentinel triggers alert if `market_ticks` table row count does not increase by >1000 in 5 minutes during market hours. (Planned)

## 5. Conclusion
This incident was a classic case of **"Log Reliance Bias"**. The system was designed to report success too eagerly. By enforcing deep verification (DB Query) and robust error handling (Retry Logic), we have moved from "Optimistic Reporting" to "Factual Reporting".
