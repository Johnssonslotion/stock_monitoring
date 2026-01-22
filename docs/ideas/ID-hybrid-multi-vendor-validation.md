# IDEA: Hybrid Multi-Vendor Validation Architecture
**Status**: 🌿 Sprouting (Drafting)
**Priority**: [P0]

## 1. 개요 (Abstract)
- **문제**: KIS/Kiwoom의 개별 수집만으로는 데이터의 완전성(Completeness)을 100% 확신할 수 없음. 또한, DuckDB의 파일 락(Lock) 문제로 인해 실시간 수집과 대량 복구가 동시에 수행될 때 병목이 발생함.
- **기회**: 현재 KIS와 Kiwoom 데이터를 동시에 수집 중이며, REST API 분봉 데이터를 활용하면 3자 교차 검증(Triangulation)을 통해 "진실된 데이터(Ground Truth)"를 확보할 수 있음.

## 2. 가설 및 기대 효과 (Hypothesis & Impact)
- **가설**: "실시간 수집은 TimescaleDB(Buffer)에 집중하고, 복구/검증을 마친 정제 데이터를 DuckDB(Archive)로 이관하는 'Tiered Storage' 방식을 도입하면 성능과 무결성을 동시에 잡을 수 있다."
- **기대 효과**:
    - **무결성**: KIS vs Kiwoom vs REST 3-Way 교차 검증으로 누락 데이터 0% 지향.
    - **가용성**: DuckDB Lock 문제 회피 및 TimescaleDB의 최적화된 시계열 쿼리 활용.
    - **유연성**: 분석은 DuckDB(OLAP), 실시간 처리는 TimescaleDB(OLTP)로 역할 분담.

## 3. 구체화 세션 (Elaboration)

### 3.1 3자 교차 검증 (Triangulation) 로직
1. **Source A (KIS)**: WebSocket 실시간 틱
2. **Source B (Kiwoom)**: WebSocket 실시간 틱 + Raw Log (JSONL)
3. **Source C (REST API)**: 분봉 (Volume, OHLCV)
- **로직**: `Source A + Source B` 합집합의 `Volume` == `Source C`의 `Volume`인지 확인.
- 불일치 시 `Source C`를 기준으로 누락 구간 재복구 (KIS REST API 활용).

### 3.2 저장소 계층화 (Tiered Storage)
| 레이어 | 저장소 | 역할 | 보관 주기 |
| :--- | :--- | :--- | :--- |
| **L1 (Hot)** | Redis | 실시간 시세 방송 (Pub/Sub) | 0일 (Volatile) |
| **L2 (Warm)** | TimescaleDB | 실시간 적재, 7일치 데이터, **검증 버퍼** | 7일 (TTL) |
| **L3 (Cold)** | DuckDB/Parquet | 검증 완료된 Ground Truth, 백테스팅용 아카이브 | 영구 |

## 4. 로드맵 연동 시나리오
- **Pillar**: Data Quality Management
- **Section**: [RFC-008] Tick Completeness QA
- **Next Step**: `market_ticks_recovery`를 활용한 Daily Triangulation 스크립트 구현.

## 5. 저장 구조 고도화안 (Schema)
- `market_ticks_recovery` (TimescaleDB): 검증 전 원본 데이터 (중복 허용)
- `market_verification_results` (TimescaleDB): 검증 통계 및 상태값
- `market_ticks_final` (DuckDB): 최종 정제 데이터 (UDS: Unique Data Source)
