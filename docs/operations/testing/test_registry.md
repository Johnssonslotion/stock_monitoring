# 🧪 Test Registry (TDD 증명서)

> [!IMPORTANT]
> **위계 (Hierarchy)**: 이 문서는 프로젝트의 모든 테스트 케이스와 품질 상태를 기록하는 **Data SSoT(Single Source of Truth)**입니다. "무엇이 테스트되는가"와 "성공 여부"를 관리하며, **[Testing Master Guide](TESTING_MASTER_GUIDE.md)**보다 데이터 정합성 측면에서 우선합니다.
> **관리 워크플로우**: 새로운 테스트 케이스 추가 및 상태 변경은 **[`/manage-tests`](../../.agent/workflows/manage-tests.md)**를 따릅니다.

## 🚦 품질 게이트 요약 (Quality Gate Summary)
| 단계 | 핵심 지표 | 기준 | 상태 |
| :--- | :--- | :--- | :--- |
| **Unit** | 커버리지 | 100% (핵심로직) | 🟡 진행중 (90%) |
| **Integration** | 데이터 일관성 | 유실율 0% | 🟢 통과 (Core) |
| **E2E** | 시스템 복원력 | Chaos 시나리오 통과 | ⏳ 예정 |

---

## 🏗️ 1. 데이터 수집 레이어 (Ingestion)

### 1.1 한국 시장 (KR Market)
| ID | 테스트명 | 파일명 | 검증 상황 | 상태 |
| :--- | :--- | :--- | :--- | :--- |
| KR-ASP-01 | `test_kr_orderbook_parsing` | `tests/test_asp_parsing.py` | H0STASP0 패킷에서 5단계 호가/잔량 파싱 | ✅ Pass |
| KR-SCH-01 | `test_kr_schema_validation` | `tests/test_schema_integrity.py` | 수집된 데이터가 `MarketData` Pydantic 모델을 100% 통과하는지 | ✅ Pass |
| KR-SCH-02 | `test_tier2_integration` | `tests/test_tier2_integration.py` | Producer-Consumer 데이터 검증 컨트랙트 (Tier 2 Strict) | ✅ Pass |

### 1.2 미국 시장 (US Market)
| ID | 테스트명 | 파일명 | 검증 상황 | 상태 |
| :--- | :--- | :--- | :--- | :--- |
| US-TICK-01 | `test_parse_us_tick_data` | `tests/test_us_collector.py` | HDFSCNT0 실시간 체결가 파싱 정확성 (Strategy: [Doc](../../strategy/realtime_ingestion_strategy.md)) | ✅ Pass |
| US-TICK-02 | `test_parse_us_websocket_message` | `tests/test_us_collector.py` | US 웹소켓 프레임 핸들링 및 Redis 발행 | ✅ Pass |
| US-ASP-01 | `test_us_orderbook_parsing` | `tests/test_asp_parsing.py` | HDFSASP0 US 호가 패킷 파싱 정확성 | ✅ Pass |
| US-SCH-01 | `test_us_schema_validation` | `tests/test_schema_integrity.py` | US 데이터의 Pydantic 모델 정합성 검증 | ✅ Pass |
| DUAL-SOC-01 | `test_concurrent_socket` | `src/data_ingestion/price/common/websocket_dual.py` | Tick/Orderbook 소켓 분리 및 동시 연결 (Logs Verified) | ✅ Pass |
| DUAL-ISO-01 | `test_socket_isolation` | Manual Verification | 한쪽 소켓 장애 시 다른 소켓 영향 없음 (Logs Verified) | ✅ Pass |
| SUB-CONF-01 | `test_subscription_confirmation` | Manual (Logs Verified) | 구독 요청 후 서버 응답(SUCCESS/FAILED) 확인 및 재시도 로직 검증 | ✅ Pass |
| SUB-RETRY-01 | `test_subscription_retry` | Manual (Logs Verified) | 구독 실패 시 최대 3회 즉시 재시도 동작 확인 | ✅ Pass |
| CONN-READY-01 | `test_connection_ready_signal` | Manual (Logs Verified) | switch_url 후 연결 완료 대기 후 구독 시작 확인 | ✅ Pass |

### 1.3 가상자산 (Crypto)
| ID | 테스트명 | 파일명 | 검증 내용 | 상태 |
| :--- | :--- | :--- | :--- | :--- |
| CRY-TICK-01 | `test_normalize_upbit` | `tests/test_collector.py` | 업비트 원본 데이터를 표준 포맷으로 변환 | ✅ Pass |

---

## 🗄️ 2. 데이터 저장 레이어 (Archiving)

### 2.1 TimescaleDB (Time-series)
| ID | 테스트명 | 파일명 | 검증 상황 | 상태 |
| :--- | :--- | :--- | :--- | :--- |
| TS-SAVE-01 | `test_save_tick_to_timescale` | `tests/test_timescale_archiver.py` | `market_ticks` 테이블 적재 및 롤백 확인 | ✅ Pass |
| TS-SAVE-02 | `test_save_orderbook_to_timescale` | `tests/test_timescale_archiver.py` | `market_orderbook` 22개 컬럼 매핑 저장 확인 | ✅ Pass |
| TS-TYPE-01 | `test_system_metrics_type_validation` | `tests/test_system_metrics_schema.py` | Sentinel 발행 메트릭 데이터 타입이 Archiver 스키마와 일치하는지 검증 (FMEA 3.4) | ✅ Pass |
| TS-CON-01 | `test_concurrent_save` | (신규 예정) | KR/US 동시 인입 시 DB 커넥션 풀 경합 및 저장 성공 여부 | ⏳ 예정 |

---

## 🔗 3. 통합 및 엔드투엔드 (E2E & Flow)

| ID | 테스트명 | 시나리오 | 검증 목표 | 상태 |
| :--- | :--- | :--- | :--- | :--- |
| E2E-FLW-01 | `test_full_pipeline_e2e` | `tests/test_pillar3_e2e.py` | 수집기 -> Redis -> DB -> API 전체 흐름 무결성 | ✅ Pass |
| E2E-WS-01 | `test_websocket_broadcast_e2e` | `tests/test_pillar3_e2e.py` | Redis 발행 시 웹소켓 즉각 브로드캐스트 검증 | ✅ Pass |
| E2E-OBS-01 | `test_observability_metrics` | (신규 예정) | 로깅에 발행 건수와 저장 건수가 1:1로 매칭되는지 확인 | ⏳ 예정 |

### 3.2 API v1 엔드포인트 및 보안 (Gate 1~2) [NEW]
| ID | 테스트명 | 파일명 | 검증 상황 | 상태 |
| :--- | :--- | :--- | :--- | :--- |
| API-V1-01 | `test_health_check` | `tests/test_api_v1.py` | API 서버 헬스체크 및 기본 가용성 | ✅ Pass |
| API-V1-02 | `test_unauthorized_missing_header` | `tests/test_api_v1.py` | 인증 헤더 누락 시 422/403 제어 확인 | ✅ Pass |
| API-V1-03 | `test_api_db_integration` | `tests/test_api_integration.py` | 틱 데이터 DB 조회 정합성 (Gate 2) | ✅ Pass |
| API-V1-04 | `test_orderbook_integration` | `tests/test_api_integration.py` | 호가 스냅샷 DB 조회 정합성 (Gate 2) | ✅ Pass |
| UI-DASH-01 | `test_dashboard_ws_render` | (Manual/Build) | WebSocket 수신 시 Ticker/Orderbook UI 즉시 업데이트 확인 | ✅ Pass |
| UI-DASH-02 | `test_dashboard_auth` | (Manual/Build) | X-API-Key 누락 시 데이터 로딩 차단 및 보안 경고 확인 | ✅ Pass |
| UI-EXT-01 | `test_external_browser_access` | (Manual) | 외부망 브라우저에서 5173 포트 접속 및 UI 렌더링 확인 | ⏳ 검증중 |
| UI-EXT-02 | `test_external_api_connection` | (Manual) | 외부망에서 동적 호스트 기반 API/WS 연결 성공 확인 | ⏳ 검증중 |
| UI-EXT-03 | `test_external_realtime_data` | (Manual) | 외부망 브라우저에서 실시간 틱/호가 데이터 수신 확인 | ⏳ 검증중 |
| UI-TS-01 | `test_tailscale_access` | (Manual) | Tailscale IP(100.100.103.19:5173)로 대시보드 접속 | ⏳ 검증중 |
| UI-CHART-01 | `test_candle_chart_render` | (Manual/Browser) | 분봉 캔들차트 렌더링 및 API 데이터 연동 검증 (QQQ) | ✅ Pass |
| UI-CHART-02 | `test_professional_chart_features` | (Manual/Browser) | 볼륨 서브플롯, MA5/MA20, 가격 패널, 시간 범위 선택 검증 | ✅ Pass |
| UI-MAP-01 | `Map-first drill-down` | `tests/e2e/map-first-layout.spec.ts` | Map 확장 상태 유지 및 클릭 시 차트 슬라이드업 검증 | ✅ Pass |
| UI-MAP-02 | `URL Symbol Sync` | `tests/e2e/map-first-layout.spec.ts` | URL 파라미터(`selected`)를 통한 종목 자동 로딩 및 분석 모드 진입 | ✅ Pass |

## 📈 4. 전략 및 백테스팅 (Strategy & Backtesting) [NEW]

| ID | 테스트명 | 시나리오 | 검증 목표 | 상태 |
| :--- | :--- | :--- | :--- | :--- |
| BT-INF-01 | `test_backtest_isolation` | 원본과 백테스트 환경 동시 실행 | 포트 충돌(6380, 5433, 8001) 없음 확인 | ✅ Pass |
| BT-ENG-01 | `test_engine_runtime` | 샘플 전략(Momentum) 실행 | 엔진 초기화 및 틱 프로세싱 루프 무결성 | ✅ Pass |
| BT-DB-01 | `test_backtest_db_init` | `backtest-engine` 실행 시 DB 초기화 | `backtest_db.market_ticks` 하이퍼테이블 생성 확인 | ✅ Pass |
| BT-MET-01 | `test_metrics_calculation` | 가상 자산 변화 데이터 입력 | Return, MDD, SharpeRatio 계산 정확성 | ✅ Pass |

---

## 🛡️ 5. 품질 가디언 (Quality Guardian)
| ID | 테스트명 | 검증 상황 | 목표 지표 | 상태 |
| :--- | :--- | :--- | :--- | :--- |
| QG-UT-01 | `Unit Coverage` | 핵심 파싱 함수 라인 커버리지 | 100% | 🟡 90% |
| QG-IT-01 | `Redis Resilience` | Redis 중단 시 Collector 재시도 및 버퍼링 유지 | Persistence 보장 | ⏳ 예정 |
| QG-E2E-01 | `Zero-Data Alarm` | 5분간 데이터 무인입 시 Sentinel 알람 발생 여부 | Alerting 정확도 | ✅ Pass |
97: | SENTINEL-01 | `Critical Alert Pub` | KIS/Kiwoom 에러 시 `system:alerts` 발행 확인 | Logs Verified | ✅ Pass |
98: | SENTINEL-02 | `Heartbeat Threshold` | 장 중 60초 데이터 부재 시 알람 발생 확인 | Config Verified | ✅ Pass |

---

## 🏗️ 6. 인프라 및 환경 (Infrastructure & Environment) [NEW]

| ID | 테스트명 | 파일명 | 검증 상황 | 상태 |
| :--- | :--- | :--- | :--- | :--- |
| INF-DNS-01 | `test_container_dns_resolution` | `tests/test_infrastructure.py` | 모든 컨테이너가 timescaledb, redis 호스트를 정상 resolve하는지 검증 (FMEA 3.5) | ✅ Pass |
| INF-NET-01 | `test_network_alias_validation` | `tests/test_infrastructure.py` | docker-compose.yml의 network alias가 실제 네트워크에 적용되었는지 검증 (FMEA 3.5) | ✅ Pass |
| INF-HEALTH-01 | `test_service_startup_health` | `tests/test_infrastructure.py` | 모든 서비스가 시작 후 30초 내 정상 상태(healthy/running)에 도달하는지 검증 (FMEA 3.5) | ✅ Pass |
| INF-ENV-01 | `test_environment_variables` | `tests/test_infrastructure.py` | 필수 환경변수(DB_HOST, REDIS_URL 등)가 모든 컨테이너에 올바르게 설정되었는지 검증 | ✅ Pass (Fixed) |

---

## 🌪️ 7. 카오스 및 복원력 테스트 (Chaos & Resilience)
| ID | 테스트명 | 시나리오 | 검증 목표 | 상태 |
| :--- | :--- | :--- | :--- | :--- |
| CH-RES-01 | `test_db_disconnect` | 적재 중 DB 강제 종료 | DB 재연결 시 누락 데이터 자동 백필 | ⏳ 예정 |
| CH-NET-01 | `test_network_jitter` | 500ms 이상의 네트워크 지연 강제 발생 | 세션 자동 재시작 및 API 키 재갱신 확인 | ⏳ 예정 |
| CH-BRO-01 | `test_invalid_tr_key` | 잘못된 TR 키 전송 시 복구 흐름 | 세션 재초기화 및 Dual-Socket 정합성 확인 | ✅ Pass |
| CH-BRO-02 | `test_already_subscribed` | 중복 구독 발생 시 자동 해지 및 재질의 | `cleanup_subscriptions()` 동작 검증 | ✅ Pass |
| DOOM-PROT-01 | `test_doomsday_suicide` | Manual (Redis Trigger) | `restart` 신호 수신 시 컨테이너 자폭 및 재부팅 검증 | ✅ Pass |
| DOOM-PROT-02 | `test_failover_fallback` | Manual (Config Change) | 재발 장애 감지 시 Single Socket 모드 자동 전환 검증 | ✅ Pass |

---

## 🔌 8. API Gateway & Hub (ISSUE-037) [NEW]

> **Phase 1**: 키 없이 개발 가능 | **Phase 2**: API 키 필요
> **MVP 핵심**: ⭐ 표시된 테스트 우선 구현

### 8.1 Queue & Dispatcher
| ID | 테스트명 | 파일명 | 검증 상황 | Phase | 상태 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| HUB-Q-01 ⭐ | `test_queue_push_pop` | `tests/unit/test_api_hub_queue.py` | Redis 큐 push/pop, 우선순위 처리 | 1 | ⏳ 예정 |
| HUB-Q-02 | `test_priority_dispatch` | `tests/unit/test_api_hub_queue.py` | HIGH 우선순위 태스크 선처리 | 1 | ⏳ 예정 |
| HUB-CB-01 ⭐ | `test_circuit_breaker` | `tests/unit/test_api_hub_dispatcher.py` | 연속 실패 시 backpressure 동작 | 1 | ⏳ 예정 |

### 8.2 Data Models & Schema
| ID | 테스트명 | 파일명 | 검증 상황 | Phase | 상태 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| HUB-MDL-01 ⭐ | `test_candle_model` | `tests/unit/test_api_hub_models.py` | CandleModel Pydantic 검증 | 1 | ⏳ 예정 |
| HUB-MDL-02 | `test_tick_model` | `tests/unit/test_api_hub_models.py` | TickModel 직렬화/역직렬화 | 1 | ⏳ 예정 |
| HUB-GT-01 | `test_source_type_ground_truth` | `tests/unit/test_api_hub_models.py` | source_type 필드 Ground Truth 검증 | 1 | ⏳ 예정 |
| HUB-SCH-01 | `test_kis_response_schema` | `tests/unit/test_api_hub_schema.py` | KIS API 응답 ↔ CandleModel 호환 | 1 | ⏳ 예정 |
| HUB-SCH-02 | `test_kiwoom_response_schema` | `tests/unit/test_api_hub_schema.py` | Kiwoom API 응답 ↔ CandleModel 호환 | 1 | ⏳ 예정 |

### 8.3 Rate Limiter & Token
| ID | 테스트명 | 파일명 | 검증 상황 | Phase | 상태 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| HUB-RL-01 | `test_gatekeeper_integration` | `tests/integration/test_api_hub_rate.py` | redis-gatekeeper 토큰 획득 | 1 | ⏳ 예정 |
| HUB-TKN-01 | `test_token_manager_ssot` | `tests/integration/test_api_hub_token.py` | Redis SSoT 토큰 관리 (`api:token:*`) | 2 | ⏳ 예정 |

### 8.4 Client & Integration
| ID | 테스트명 | 파일명 | 검증 상황 | Phase | 상태 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| HUB-KIS-01 | `test_kis_client_mock` | `tests/integration/test_api_hub_clients.py` | KIS REST API Mock 호출 | 2 | ⏳ 예정 |
| HUB-KIW-01 | `test_kiwoom_client_mock` | `tests/integration/test_api_hub_clients.py` | Kiwoom REST API Mock 호출 | 2 | ⏳ 예정 |
| HUB-REG-01 | `test_backfill_compatibility` | `tests/integration/test_api_hub_compat.py` | BackfillManager 호환성 검증 | 2 | ⏳ 예정 |
| HUB-SCH-03 | `test_schema_drift_detection` | `tests/integration/test_api_hub_schema.py` | 실제 API 호출 후 스키마 변경 감지 | 2 | ⏳ 예정 |

### 8.5 E2E & Performance
| ID | 테스트명 | 파일명 | 검증 상황 | Phase | 상태 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| HUB-E2E-01 | `test_api_hub_e2e` | `tests/e2e/test_api_hub_e2e.py` | 전체 파이프라인 + Chaos 시나리오 | 2 | ⏳ 예정 |
| HUB-RES-01 | `test_memory_usage` | `tests/integration/test_api_hub_perf.py` | 메모리 512M 이하 검증 (Zero Cost) | 2 | ⏳ 예정 |

### 8.6 Test Fixtures
```
tests/fixtures/api_responses/
├── kis_candle_response.json      # KIS 분봉 API 샘플
├── kis_tick_response.json        # KIS 틱 API 샘플
├── kiwoom_candle_response.json   # Kiwoom 분봉 API 샘플
└── README.md                     # 샘플 갱신 방법
```

---

## 📄 9. 문서 및 규정 준수 (Documentation & Compliance) [STRICT]

| ID | 테스트명 | 검증 항목 | 목표 지표 | 상태 |
| :--- | :--- | :--- | :--- | :--- |
| DOC-SYNC-01 | `SSoT Alignment` | README/Roadmap/Registry 간의 모든 링크 및 상태 동기화 | 불일치 0건 | ✅ Pass |
| DOC-RULE-01 | `.ai-rules.md Compliance` | 모든 소스 코드에 한국어 Docstring 적용 확인 | 준수율 100% | ✅ Pass |
