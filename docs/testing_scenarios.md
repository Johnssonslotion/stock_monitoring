# 테스트 시나리오 명세 (Testing Scenarios)

**QA Owner**: QA Engineer
**Target**: Collector, Processor, Trader

## 1. 정밀성 검증 (Unit/Functional)
| ID | Category | Scenario | Expected Result |
| :--- | :--- | :--- | :--- |
| TC-001 | Config | 유효하지 않은 YAML 로드 | `ValidationError` 발생 및 앱 실행 중단 |
| TC-002 | Collector | Upbit WS 연결 성공 | `Open` 로그 발생 및 Ping-Pong 유지 |
| TC-003 | Data | 음수 가격(`-100원`) 수신 | `normalize()` 함수에서 유효성 에러 발생 및 필터링 |
| TC-004 | Parser | 필수 필드(`timestamp`) 누락 | 해당 틱 무시하고 에러 카운트 증가 (Crashing 금지) |

## 2. 통합 검증 (Integration/E2E)
| ID | Category | Scenario | Expected Result |
| :--- | :--- | :--- | :--- |
| TC-101 | Data Flow | Mock Exchange -> Collector -> Redis | Redis Subscriber에서 보낸 데이터와 동일한 JSON 수신 확인 |
| TC-102 | Archiving | Redis -> DuckDB 저장 | 1분 후 `select count(*) from ticks` 조회 시 데이터 존재 |

## 3. 카오스 테스트 (Chaos Engineering) - *High Priority*
| ID | Category | Scenario | Expected Result |
| :--- | :--- | :--- | :--- |
| **TC-901** | **Network** | **수집 도중 인터넷 연결 차단 (5초간)** | `ConnectionClosed` 감지 -> **자동 재접속(Reconnect)** -> 데이터 수집 재개 |
| TC-902 | Load | 초당 10,000개 틱 폭탄 투하 | 메모리 사용량 급증하되 Collector 프로세스 죽지 않음 (Backpressure) |
| TC-903 | Dependency | Redis 프로세스 Kill | Collector는 에러 로그 남기며 대기하다가 Redis 복구 시 자동 연동 |

## 4. 테스트 전략
-   **CI/CD**: `pytest`는 매 커밋마다 실행.
-   **Chaos**: 주 1회 별도 환경에서 수행.
