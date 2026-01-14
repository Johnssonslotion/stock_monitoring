# Operational Policies & Procedures
**Version**: 1.0 (2026-01-14)
**Status**: Active

---

## 1. 로그 관리 정책 (Log Retention)
**목표**: 디스크 부족 방지 및 데이터 무결성 보존의 균형 유지.

### 1.1 저장 및 로테이션
- **위치**: `/app/data/raw/` (Docker Volume)
- **포맷**: `ws_raw_YYYYMMDD_HH.jsonl` (1시간 단위 로테이션)
- **관리 주체**: `real-collector` 컨테이너 내부 `RawWebSocketLogger`

### 1.2 보존 기간 (Retention)
- **기본 정책**: **120시간 (5일)**
- **보호 로직(Hard Limit)**: 최근 **48시간(2일)** 데이터는 어떠한 경우에도 자동 삭제되지 않음.
- **삭제 방식**: 매 시간(Hourly) 비동기 루프(`_cleanup_old_logs`)가 만료된 파일을 삭제.
- **수동 개입**: 디스크 사용량 80% 초과 시 `retention_hours`를 72시간(3일)으로 축소 권장.

---

## 2. 장애 감지 및 복구 (Failover & Healing)

### 2.1 Traffic Watchdog (유령 구독 방지)
**목표**: WebSocket 연결은 되어 있으나 데이터가 수신되지 않는 Zombie 상태 방지.

| 단계 | 조건 (데이터 미수신 시간) | 조치 내용 | 로그 레벨 |
| :--- | :--- | :--- | :--- |
| **Level 1** | **60초** | 경고 로그 출력 | `WARNING` |
| **Level 2** | **120초** (2분) | **재구독 (Resubscribe)** 시도 <br> (서버에 구독 패킷 재전송) | `WARNING` |
| **Level 3** | **180초** (3분) | **강제 재연결 (Hard Reconnect)** <br> (소켓 연결 종료 후 프로세스 재시작 유도) | `ERROR` |

### 2.2 Doomsday Protocol (데이터 전멸 대응)
- **트리거**: 운영 시간(09:00~15:30) 중 5분 이상 전체 데이터 유입 0건.
- **조치**: Sentinel이 알림 발송 -> 관리자가 `make restart-collectors` 실행. (향후 자동화 예정)

---

## 3. 데이터 보정 (Backfill Policy)
**목표**: 수집 실패로 인한 데이터 누락 복구 (결측치 최소화).

### 3.1 누락 판단 기준
- **일별 검증**: 매일 장 마감 후 `verify_integrity.py` 실행.
- **Gap 탐지**: 1분 이상 Ticker 데이터 공백 발생 시 누락으로 간주.

### 3.2 백필 절차
1. **소스**: `yfinance` (Yahoo Finance) 등 외부 API.
2. **도구**: `history-loader` 컨테이너.
3. **명령어**:
   ```bash
   # 특정 날짜 백필 실행
   docker-compose run --rm history-loader python -m src.data_ingestion.history.loader --date 2026-01-13
   ```
4. **우선순위**: 실시간 수집(KIS) 데이터가 우선하며, 백필 데이터는 누락된 구간(`INSERT ON CONFLICT DO NOTHING`)만 채운다.
