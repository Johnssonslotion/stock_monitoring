# Kiwoom WebSocket Production Verification Test Plan

## 개요
- **목표**: Kiwoom WebSocket Collector의 안정성을 검증하고 Production(Live) 환경에 배포하기 위함.
- **기간**: 2026-01-20 (월) ~ 2026-01-22 (수)
- **책임자**: QA Engineer, Infrastructure Engineer

---

## 🧪 Tier 1: Connectivity & Data Integrity (월요일)
**목표**: 실제 장 운영 시간 동안 데이터가 정상적으로 수신되고 파싱되는지 확인.

| ID | 테스트 항목 | 시나리오 | 통과 기준 | 비고 |
|----|-------------|----------|-----------|------|
| **T1-1** | **최초 연결 및 인증** | 08:30 KST 장 시작 전 접속 시도 | `LOGIN` 응답 `return_code: 0` 확인 | 필수 |
| **T1-2** | **다중 TR 등록 (REG)** | 08:31 틱(0B), 호가(0D), 지수(0J), VI(1h) 동시 등록 | `REG` 응답 `return_code: 0` 확인 | 필수 |
| **T1-3** | **실시간 데이터 수신** | 09:00~10:00 (1시간) 동안 연결 유지 | 데이터 수신 끊김 없이 지속됨 (로그 확인) | 필수 |
| **T1-4** | **FID 파싱 검증** | 수신된 0B, 0D, 0J, 1h 데이터 샘플링 | FID 값 파싱 에러(KeyError, ValueError) 0건 | 필수 |
| **T1-5** | **Dual Socket 검증** | KIS 소켓과 Kiwoom 소켓 동시 연결 | 두 소켓 모두 403/Connection Closed 없이 유지 | **Priority** |

---

## 🛡️ Tier 2: Resilience & Recovery (화요일)
**목표**: 네트워크 불안정, 서버 재시작 등 장애 상황에서의 복구 능력 검증.

| ID | 테스트 항목 | 시나리오 | 통과 기준 | 비고 |
|----|-------------|----------|-----------|------|
| **T2-1** | **강제 연결 종료 (Client)** | 수신 중 클라이언트(Python) 강제 종료 후 재시작 | 10초 내 재접속 및 데이터 수신 재개 | |
| **T2-2** | **네트워크 단절 시뮬레이션** | `iptables`로 패킷 차단 또는 WiFi Off/On | `ConnectionClosed` 감지 → 재연결 로직 작동 | |
| **T2-3** | **Token 만료 갱신** | (가능하다면) 토큰 만료 후 재접속 시도 | 401/Invalid Token 에러 시 자동갱신 후 재접속 | |
| **T2-4** | **비정상 데이터 처리** | (Mock) FID 누락, 타입 불일치 데이터 주입 | 크래시 없이 에러 로깅 후 무시 (Skip) | |

---

## ☠️ Tier 3: Doomsday Protocol (수요일)
**목표**: 시스템이 완전히 멈췄을 때의 감지 및 최후의 수단 검증.

| ID | 테스트 항목 | 시나리오 | 통과 기준 | 비고 |
|----|-------------|----------|-----------|------|
| **T3-1** | **Data Silence 감지** | 60초간 데이터 수신 0건 (장중) | `SystemWatcher`가 "No ticks" 경보 발생 | |
| **T3-2** | **자동 재기동 (Self-Healing)** | Silence 감지 시 Docker Container 재시작 | 컨테이너 재시작 후 정상 복구 | |
| **T3-3** | **Failover 알림** | Kiwoom 완전 불능 시 KIS 단독 모드 전환 | `system:status`에 `KIWOOM_DOWN` 상태 발행 | Critical |

---

## 📝 실행 계획 (Timeline)

### 📅 월요일 (1/20) - Data Day
- **08:30**: `scripts/kiwoom_live_monitor.py` 실행 (로깅 모드)
- **09:00**: 파싱 로그 확인, FID 매핑 누락분 실시간 업데이트
- **10:00**: Tier 1 통과 판정 → Redis Pub/DB Save 활성화 (`KIWOOM_BACKUP_MODE=True`)
- **15:30**: 장 마감 후 데이터 품질 리포트 작성

### 📅 화요일 (1/21) - Chaos Day
- **10:00**: T2-1 (재시작) 테스트
- **11:00**: T2-2 (네트워크 단절) 테스트
- **14:00**: 복구 로직 튜닝 및 재배포

### 📅 수요일 (1/22) - Production Day
- **09:00**: 전체 시스템 정상 가동 확인
- **10:00**: T3 Doomsday Protocol 모의 훈련 (테스트 환경)
- **15:00**: 최종 Production 배포 승인 (Council Meeting)
