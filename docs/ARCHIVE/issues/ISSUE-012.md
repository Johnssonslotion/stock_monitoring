# ISSUE-012: KIS WebSocket Approval Key가 적용되지 않음

**상태**: Open  
**우선순위**: P0 (긴급 - 데이터 수집 중단)  
**유형**: bug  
**생성일**: 2026-01-19  
**담당**: Developer

## 문제 설명
유효한 API 자격 증명에도 불구하고 KIS 데이터 수집이 완전히 실패하고 있습니다. 모든 구독 시도가 "invalid approval : NOT FOUND" 오류를 반환합니다.

## 근본 원인 분석
1. **KIS API 키는 유효함** (테스트 성공):
   - REST 토큰 생성: ✅ 작동
   - Approval key 생성: ✅ 작동 (유효한 UUID 반환: `915536bf-ed26-4d69-a906-34c8b84991ea`)

2. **문제 위치**: `src/data_ingestion/price/common/websocket_dual.py`
   - 171번 라인: `if not target_ws or not self.approval_key:`
   - `self.approval_key`가 None일 때 구독 요청 차단
   - Approval key는 발급되지만 매니저 인스턴스에 설정되지 않음

3. **증거**:
   - Raw WebSocket 로그(`data/raw/ws_raw_*.jsonl`)에 TX (송신) 메시지가 전혀 없음
   - RX (수신) 오류 메시지만 존재
   - 로그에 "✅ KIS Approval key obtained" 표시되지만 구독은 여전히 실패

## 영향
- KIS로부터 틱 데이터 수집 전무 (0 ticks)
- 2026-01-16 이후 데이터 갭 발생
- Kiwoom 단독 운영으로 부분 커버리지만 가능 (~93K ticks/day)

## 완료 조건 (AC)
- [ ] `DualWebSocketManager`에 `self.approval_key`가 올바르게 설정됨
- [ ] Raw WebSocket 로그에 구독 TX 메시지 나타남
- [ ] KIS 틱 데이터가 유입 시작 (market_ticks 테이블에서 확인)
- [ ] 로그에 "invalid approval : NOT FOUND" 오류가 없음

## 제안 해결방안
1. `unified_collector.py`와 `websocket_dual.py` 초기화 시퀀스 검토
2. `KISAuthManager.get_approval_key()`에서 받은 approval_key가 매니저로 전달되는지 확인
3. Approval_key 생명주기를 추적하는 로깅 추가
4. kis-service 재시작으로 테스트

## 기술 상세 (Technical Details)
- **서비스**: deploy-kis-service-1
- **영향 파일**:
    - `src/data_ingestion/price/common/websocket_dual.py`
    - `src/data_ingestion/price/common/kis_auth.py`
    - `src/data_ingestion/price/unified_collector.py`
- **로그 위치**: `/home/ubuntu/workspace/stock_monitoring/data/raw/ws_raw_*.jsonl`

## 관련 정보
- **검증 보고서**: 데이터 수집 상태 검증 완료 (2026-01-19)
- **Kiwoom 상태**: 정상 수집 중 (Heartbeat 재연결 이슈는 경미)
- **관련 이슈**: ISSUE-003 (API Error Handling), ISSUE-007 (WebSocket 연결 관리자)
