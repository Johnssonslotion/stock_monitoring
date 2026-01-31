# ISSUE-008: Realtime OrderBook Streaming (Phase 1)

## Context
RFC-010의 Phase 1 구현 과제입니다. 10단계로 수집된 호가 데이터(Kiwoom)를 웹소켓을 통해 클라이언트(Frontend)에 실시간으로 전송해야 합니다. 데이터는 델타 압축 상태로 Redis에 저장되므로, **서버 사이드에서 스냅샷을 재구성(Rehydration)하여** 클라이언트에는 항상 온전한(Full) 10단계 데이터를 전송해야 합니다.

## Goals
- [ ] `RedisOrderbookSubscriber` 구현: `orderbook.kiwoom.*` 채널 구독.
- [ ] `SnapshotBuilder` 구현: 델타 데이터를 받아 메모리 상에서 최신 스냅샷 유지.
- [ ] WebSocket Endpoint `/ws/orderbook/{symbol}` 구현 (`FastAPI`).
- [ ] 클라이언트 접속 시 즉시 최신 스냅샷 전송 (Initial State).

## Specs
- **Source**: Redis Pub/Sub (`orderbook.kiwoom.{symbol}`)
- **Format**: JSON (Full 10-depth snapshot)
- **Protocol**: WebSocket
- **Rate Limit**: 클라이언트당 연결 수 제한 (기본사항)

## Implementation Details
1. **Manager**: `src/api/services/stream_manager.py` (Singleton recommended)
2. **Logic**:
   - Redis 메시지 수신 (10단계, 일부 델타일 수 있음 - 현재는 Full로 저장되지만, 델타 필터 적용된 상태)
   - *Correction*: ISSUE-049에서 `should_publish`가 `True`일 때만 보내지만, 내용은 "Full Model Dump"입니다. 즉 Redis 자체에는 Full Snapshot이 날아가므로, API 서버는 별도의 Rehydration 로직 없이 **받은 데이터를 그대로 브로드캐스팅**하면 됩니다. (RFC-010 Architect 의견 재검토 필요 -> 아, 델타로 줄여서 보낸 게 아니라 '보낼지 말지'를 결정한 것임. 따라서 Redis 메시지는 항상 Full Snapshot임. OK.)
   - **Optimization Refined**: Redis 메시지(`KiwoomOrderbookData`)를 그대로 클라이언트에 토스.

## References
- [RFC-010](../governance/decisions/RFC-010_advanced_data_pipeline.md)
- [ground_truth_policy.md](../governance/ground_truth_policy.md)
