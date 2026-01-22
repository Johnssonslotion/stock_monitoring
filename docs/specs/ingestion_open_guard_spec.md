# Spec: Ingestion Open Guard (Zero-Tolerance)
**Status**: 🛠️ Implementing
**Issue**: [ISSUE-035](../issues/ISSUE-035.md)

## 1. 개요
장 초반(09:00:00) 대량의 데이터가 유입될 때, 시스템 초기화 지연으로 인한 데이터 유실을 방지하기 위한 선제적 방어 메커니즘입니다.

## 2. 설계 상세 (Design)

### 2.1. Pre-warmup (장 시작 전)
- **시간**: 08:50:00 (KST)
- **동작**:
    - 모든 Collector(KIS, Kiwoom)의 가상 연결 테스트.
    - Redis Pub/Sub 채널 활성화 확인.
    - DB 커넥션 풀 초기화 및 Mirror Table 정합성 체크.

### 2.2. Zero-Tolerance Buffer
- 장 시작 시점부터 첫 5분간(`09:00:00 ~ 09:05:00`)은 수집 데이터의 메모리 버퍼링 우선순위를 높임.
- Archiver가 지연될 경우 Redis Stream에 데이터를 임시 보관(TTL 1시간)하여 유실 방지.

### 2.3. Monitoring Integration
- **Sentinel**은 09:00:01 이후 수집량이 0일 경우 즉시 `P0 Alert` 발생.
- `scripts/preflight_check.py`에 Mirror Table 및 Schema Parity 체크 로직 통합.

## 3. 검증 항목
- [ ] 09:00:00 정각에 데이터 수집 시작 여부 (Log 확인)
- [ ] Redis Stream 백업 버퍼 작동 확인
- [ ] Preflight check 시 DB 쓰기 테스트 성공 여부
