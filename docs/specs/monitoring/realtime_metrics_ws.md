# Real-time Monitoring WebSocket API Specification (ISSUE-044)

**Version**: 1.0  
**Date**: 2026-01-17  
**Author**: Architect / Developer

---

## 1. Overview (개요)
본 명세서는 `SystemDashboard`의 실시간성 확보를 위해 REST 폴링 방식을 대체하는 **WebSocket 기반 시스템 메트릭 스트리밍 API**를 정의합니다.

**Purpose**: 
- 기존 5초 단위 HTTP 폴링 방식의 클라이언트 부하 및 지연 시간 단축.
- 리소스 임계치 초과 시 즉각적인 경고(Alert) 전파.
- Sentinel과 Dashboard 간의 실시간 피드백 루프 구축.

**Scope**: 
- `/ws/system` 엔드포인트를 통한 메트릭 데이터 스트리밍.
- Redis Pub/Sub을 활용한 이벤트 기반 브로드캐스트 시스템.
- 호스트(CPU, Mem, Disk) 및 컨테이너 상태(Running, Stopped) 정보 포함.

---

## 2. Interface (인터페이스)

### 2.1 WebSocket Endpoint
```
WS /api/system/ws
```
- **Auth**: Query parameter `api_key` 또는 초기 연결 시 Header 인증 사용.
- **Protocol**: `JSON`

### 2.2 Redis Pub/Sub
- **Channel**: `system:metrics`
- **Producer**: `sentinel.py` 또는 리소스 수집 유틸리티.
- **Consumer**: API Server (WebSocket Router).

---

## 3. Data Structures (데이터 구조)

### 3.1 Message Schema (JSON)
```json
{
  "type": "system_metric",
  "data": {
    "time": "2026-01-17T04:30:00Z",
    "metric_type": "cpu",
    "value": 45.2,
    "source": "host",
    "meta": {
        "unit": "percent"
    }
  }
}
```

### 3.2 Container Status Schema
```json
{
  "type": "container_status",
  "data": {
    "container": "tick-archiver",
    "status": "running",
    "time": "2026-01-17T04:30:00Z"
  }
}
```

---

## 4. Edge Cases (예외 상황 처리)

| Scenario | Expected Behavior |
|:---|:---|
| WebSocket 연결 끊김 | 클라이언트(`StreamManager.ts`)에서 2, 5, 10, 30초 간격으로 지수 백오프 기반 재연결 시도. |
| Redis 장애 | 백엔드 로그에 에러 기록 후 클라이언트에 `503 Service Unavailable` 관련 패킷 전송 시도. |
| 대량의 데이터 유입 | 백엔드에서 초당 메시지 수 제한(Throttling) 적용. |
| 비인증 접근 | 초기 핸드셰이크 단계에서 연결 강제 종료. |

---

## 5. Dependencies (의존성)

### Internal Modules
- `src/api/routes/system.py`: WebSocket 라우터 통합.
- `src/monitoring/sentinel.py`: 데이터 소스(Producer) 역할.
- `src/web/src/StreamManager.ts`: 프론트엔드 수신부 연동.

### External Services
- Redis: 메시지 브로커(Pub/Sub).

---

## 6. Constraints (제약사항)

- **Performance**: 메시지 전달 지연 시간(Back-to-Front) 100ms 이내.
- **Resource**: 최대 동시 접속 클라이언트 100명으로 제한 (현재 무부하 기준).

---

## 7. 관련 RFC/Specs
- [Observability Roadmap](../../strategies/observability_roadmap.md)
- [Backend Specification](../backend_specification.md)
