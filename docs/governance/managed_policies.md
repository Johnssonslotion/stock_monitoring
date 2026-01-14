# Managed Policies & Configuration Registry
**Last Updated**: 2026-01-14
**Status**: 🛡️ Ratified by Council of Six

이 문서는 코드 내에 산재된 **가변적 관리 항목(Variables & Thresholds)**들을 정의하고, 각 항목의 소유권(Persona)과 변경 정책을 명시한다.

---

## 1. 🕒 Market Operation Policies (시장 운영 정책)
**Owner**: 🔬 **Data Scientist** | **Impl**: `unified_collector.py`

| Item | Value (Current) | Description | Change Policy |
| :--- | :--- | :--- | :--- |
| **KR Market Hours** | `08:30` ~ `16:00` (KST) | 한국 주식 정규장 및 시간외 (30분 버퍼 포함) | 🏛️ Council Verification |
| **US Market Hours** | `17:00` ~ `08:00` (Next Day) | 프리마켓 + 정규장 + 애프터마켓 전체 커버 | 🏛️ Council Verification |
| **Timezone** | `Asia/Seoul` (KST) | 시스템의 기준 시간대 (로그, DB 파티셔닝) | ⚠️ **Immutable** (변경 불가) |

> **Architect's Note**: 현재 `market_scheduler` 함수 내에 하드코딩 되어 있음. 향후 `configs/market_schedule.yaml`로 분리 권장.

---

## 2. 🛡️ Resilience & Failover (장애 대응)
**Owner**: 🔧 **Infra Engineer** | **Impl**: `websocket_base.py`, `sentinel.py`

| Item | Value | Config Loc | Impact |
| :--- | :--- | :--- | :--- |
| **Watchdog Warn** | `60s` No Data | `websocket_base.py` | 단순 로그 기록 (Level 1) |
| **Watchdog Resub** | `120s` No Data | `websocket_base.py` | WebSocket 재구독 시도 (Level 2) |
| **Watchdog Kill** | `180s` No Data | `websocket_base.py` | **소켓 강제 종료** 및 재연결 (Level 3) |
| **Doomsday Trigger** | `5 min` (300s) | `configs/sentinel_config.yaml` | **컨테이너 강제 재시작 (Docker Restart)** |
| **Max Restarts** | `5` times / hour | `configs/sentinel_config.yaml` | 무한 재부팅 방지 (Circuit Breaker) |

> **Infra's Note**: Watchdog 임계값은 코드 수정 (`git push`) 필요. Doomsday 및 Sentinel 설정은 `yaml` 수정 (`git trigger`)만으로 배포 없이 적용 가능.

---

## 3. 💾 Data & Resource Management (데이터 리소스)
**Owner**: 🔧 **Infra Engineer** & 🔬 **Data Scientist**

| Item | Value | Description | Enforcement |
| :--- | :--- | :--- | :--- |
| **Log Retention** | `120 Hours` (5 days) | Raw WebSocket Log (`.jsonl`) 보존 기간 | 코드 내 `_cleanup_old_logs` 루프 |
| **Min Protection** | `48 Hours` | 디스크가 꽉 차도 절대 지우지 않는 최소 보존량 | 하드코딩 (Safety Lock) |
| **Disk Warning** | `90%` Usage | Sentinel 알림 발송 임계값 | `sentinel_config.yaml` |
| **Memory Warning** | `85%` Usage | Sentinel 알림 발송 임계값 | `sentinel_config.yaml` |

> **PM's Note**: 디스크 경고(90%) 발생 시, Infra 엔지니어는 즉시 `make prune-logs`를 수행하거나 Retention 정책을 72시간으로 하향 조정해야 한다.

---

## 4. 🚨 Alerting & Notification (알림 정책)
**Owner**: 👔 **Project Manager** | **Impl**: `sentinel.py`

| Item | Value | Description |
| :--- | :--- | :--- |
| **Price Anomaly** | `10%` Change | 직전 틱 대비 10% 이상 가격 급변 시 알림 (오류 데이터 감지용) |
| **Heartbeat** | `30s` | Sentinel이 Redis Pub/Sub을 확인하는 주기 |
| **CPU Load** | `80%` | 지속적인 고부하 감지 시 Warning |

---

## 5. 📊 Monitoring Priorities (모니터링 우선순위)
**Defined by**: 🔧 **Infra Engineer** & 👔 **PM**

시스템 리소스 제약(Zero Cost)과 비즈니스 연속성을 고려한 메트릭 중요도 등급입니다.

| Priority | Metric | Condition | Action Required |
| :--- | :--- | :--- | :--- |
| **P0 (Critical)** | **Container Status** | `status != running` | **즉시 복구**. Doomsday Protocol 발동 및 관리자 호출. |
| **P1 (High)** | **Disk Usage** | `> 90%` | 데이터 유실 임박. `make prune-logs` 실행 및 Retention 정책 긴급 수정. |
| **P2 (Medium)** | **Memory Usage** | `> 85%` | OOM Kill 위험. 메모리 누수 점검 및 불필요 서비스 중단. |
| **P3 (Low)** | **CPU Usage** | `> 80%` | 처리 지연 가능성. 코드 최적화 또는 수집 주기 조정 검토. |

---

## ✅ Council Review Summary
1.  **Architect**: "현재 로직(`.py`)과 설정(`.yaml`)이 혼재되어 있음. 장기적으로 모든 Policy를 `configs/`로 이동시키는 리팩토링이 필요함."
2.  **Dev**: "Watchdog 임계값(60/120/180s)은 경험적 수치임. 운영 데이터 쌓이면 조정 필요."
3.  **QA**: "시장 시간(08:30) 변경 시 반드시 오전 8시 전 배포해야 함. (장 중 배포 금지)"
4.  **Data Scientist**: 
    - "US Market은 자정을 넘어가므로(`Next Day`), DB 조회 시 단순 일자별(`Day`) 집계가 아닌 **'Trading Day' 기준 집계 로직**이 필수적임." 
    - "로그 삭제(Retention) 전, 파싱 에러나 이상 데이터가 포함된 로그는 별도 아카이빙하는 **'Data Rescue' 파이프라인**이 필요함."
5.  **PM**: "모든 정책 변경은 비즈니스 가치(데이터 무결성)와 비용(Zero Cost) 사이의 균형을 유지해야 함. 과도한 안전장치로 인한 리소스 초과는 불허."
6.  **Doc Specialist**: "정책 문서(`managed_policies.md`)는 코드가 변경될 때마다 즉시 동기화되어야 하며, 변경 이력(History)이 투명하게 남아야 함."
