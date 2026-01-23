# ISSUE-039: [Bug] TickArchiver (DuckDB) Redis 연결 불안정 - 동기 블로킹 I/O 문제

**Status**: Open
**Priority**: P1
**Type**: bug
**Created**: 2026-01-23
**Assignee**: Developer
**Related**: ISSUE-017 (DuckDBArchiver 구현)

## 문제 현상

`tick-archiver` 컨테이너가 Redis Pub/Sub 연결이 반복적으로 끊기고 재연결됨.

```
ERROR:__main__:Redis Connection Lost: Connection closed by server.. Reconnecting...
INFO:__main__:Redis connection closed.
INFO:__main__:✅ Subscribed to market:ticks / tick:* / ticker.*
(무한 반복)
```

## 근본 원인 분석

### 1. Redis 출력 버퍼 초과
- **설정값**: `pubsub 33554432 8388608 60` (hard: 32MB, soft: 8MB/60초)
- **클라이언트 상태**: `oll=153` (출력 대기 메시지), `omem=2.4MB` (버퍼 사용량)
- 메시지 소비 속도 < 생산 속도 → 버퍼 누적 → soft limit 초과 → 연결 강제 종료

### 2. 동기 블로킹 I/O가 async 루프를 차단

**문제 코드** (`src/data_ingestion/ticks/archiver.py`):

```python
# Line 68-122: flush_buffer() - 동기 DuckDB executemany
self.conn.executemany(...)  # 블로킹!

# Line 124-168: merge_recovery_files() - 동기 파일/DB I/O
self.conn.execute("ATTACH ...")  # 블로킹!

# Line 202: async 루프에서 동기 함수 직접 호출
self.merge_recovery_files()  # 최악의 패턴
```

**영향**:
- 틱 데이터: 초당 117개 유입
- DuckDB 작업 중 이벤트 루프 차단 → 메시지 수신 불가
- Redis 출력 버퍼 누적 → 60초 후 연결 끊김

## 임시 조치 (2026-01-23)

Redis Pub/Sub 출력 버퍼 확장 (런타임 적용):
```bash
docker exec stock_prod-redis redis-cli CONFIG SET client-output-buffer-limit \
  "normal 0 0 0 slave 268435456 67108864 60 pubsub 134217728 67108864 60"
```
- 결과: **효과 없음** - 소비 속도 문제는 해결되지 않음

## 해결 방안

### Option A: asyncio.to_thread() 적용 (권장)
DuckDB 동기 작업을 별도 스레드에서 실행:

```python
async def flush_buffer(self):
    if not self.buffer:
        return
    data = self._prepare_data()
    await asyncio.to_thread(self._sync_flush, data)  # 블로킹 해제

async def run(self):
    # ...
    await asyncio.to_thread(self.merge_recovery_files)  # 블로킹 해제
```

### Option B: 별도 프로세스/스레드 분리
- 메시지 수신: async 전용 루프
- DuckDB 쓰기: 별도 스레드/프로세스 (큐 기반)

### Option C: TimescaleArchiver 통합
- DuckDB archiver 제거
- TimescaleDB만 사용 (현재 정상 동작 중)
- **주의**: 무결성 검증 평가 중이므로 당장 적용 불가

## Acceptance Criteria

- [ ] `flush_buffer()`가 이벤트 루프를 차단하지 않음
- [ ] `merge_recovery_files()`가 이벤트 루프를 차단하지 않음
- [ ] Redis 연결이 1시간 이상 안정적으로 유지됨
- [ ] 틱 데이터 소비 속도 >= 생산 속도 (초당 117+ ticks)

## 작업 일정

- **예정 수정 시점**: 2026-01-23 장 마감 후 (15:30 KST 이후)
- **영향 범위**: tick-archiver 컨테이너 재시작 필요
- **TimescaleDB 영향**: 없음 (별도 경로)

## 참고 자료

### 현재 아키텍처

```
KIS/KIWOOM 수집기
       │
       ▼
   Redis Pub/Sub ──────────────────────────┐
       │                                   │
       ▼                                   ▼
┌─────────────────┐               ┌─────────────────┐
│ timescale-archiver │             │  tick-archiver   │
│   (별도 컨테이너)    │             │  (별도 컨테이너)   │
│  ✅ 정상 동작      │             │  ❌ 블로킹 문제   │
└────────┬────────┘               └────────┬────────┘
         ▼                                 ▼
    TimescaleDB                         DuckDB
   (421,785 ticks/1h)                 (137MB)
```

### Redis CLIENT LIST 분석
```
id=26339 addr=172.20.0.14:45196 flags=P psub=3
oll=153 omem=2439976 (2.4MB) events=rw
```
- `oll`: Output List Length (전송 대기 메시지)
- `omem`: Output Memory (출력 버퍼 메모리)
- `events=rw`: 읽기/쓰기 모두 대기 중

### Related Issues
- ISSUE-017: DuckDBArchiver 구현 (원본 구현)
- ISSUE-022: DuckDB 타입 변환 오류 (별도 버그)
