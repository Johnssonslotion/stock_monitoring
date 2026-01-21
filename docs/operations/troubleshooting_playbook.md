# 장애 조치 플레이북 (Troubleshooting Playbook)

**Last Updated**: 2026-01-04
**Target Audience**: Infra Engineer, Developer, On-call Ops

## 1. 개요
본 문서는 `stock_monitoring` 시스템 운영 중 발생할 수 있는 주요 장애 상황(Incident)과 그에 대한 표준 대응 절차(SOP)를 정의한다.

## 2. 에러 코드 체계 (Error Codes)
-   **1xxx**: Data Ingestion (Collector)
-   **2xxx**: Messaging (Redis)
-   **3xxx**: Storage (DuckDB)
-   **5xxx**: System/Network

## 3. 상황별 대응 가이드

### [ERR-1001] WebSocket Connection Lost
-   **증상**: 로그에 `ConnectionClosedError` 반복, Redis 채널에 데이터 없음.
-   **원인**: 거래소 서버 점검 또는 로컬 네트워크 불안정.
-   **자동 대응**: Collector 내부의 지수 백오프(Exponential Backoff) 로직이 30초 간격으로 재접속 시도.
-   **수동 조치**:
    1.  인터넷 연결 확인: `ping 8.8.8.8`
    2.  재시작: `make restart-collector`

### [ERR-2001] Redis OOM (Out of Memory)
-   **증상**: `OOM command not allowed` 에러 발생, 데이터 저장 실패.
-   **원인**: 틱 데이터가 Consumer에 의해 소비되지 않고 Redis 큐에 계속 쌓임.
-   **긴급 조치**:
    1.  메모리 확보: `redis-cli FLUSHALL` (주의: 모든 데이터 유실됨, 최후의 수단)
    2.  Archiver 상태 확인: `docker ps | grep archiver`

### [ERR-5001] Oracle Free Tier Resource Limit
-   **증상**: 컨테이너가 이유 없이 죽음 (Killed), `dmesg`에 `Out of memory` 기록.
-   **원인**: 24GB RAM 한도 초과.
-   **조치**:
    1.  `docker stats`로 메모리 누수 범인 색출.
    2.  `docker-compose.yml`에서 해당 서비스의 `mem_limit`를 낮춤.

## 4. 모니터링 체크리스트
-   [ ] Collector 컨테이너가 `Up` 상태인가?
-   [ ] Redis 메모리 사용량이 1GB 이하인가?
-   [ ] `data/` 디렉토리에 DuckDB 파일이 갱신되고 있는가?
