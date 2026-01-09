# Pillar 3 외부망 브라우저 접속 검증 체크리스트

이 문서는 `.ai-rules.md`의 품질 게이트 기준에 따라 내부망 테스트뿐만 아니라 **외부망(원격 브라우저)**에서의 실제 접속 및 동작을 검증하기 위한 수동 테스트 가이드입니다.

## 🌐 서버 정보
- **서버 내부 IP**: `10.0.1.157`
- **대시보드 URL**: `http://10.0.1.157:5173`
- **API 서버 URL**: `http://10.0.1.157:8000`
- **웹소켓 URL**: `ws://10.0.1.157:8000/ws`

## ✅ 외부망 테스트 체크리스트

### UI-EXT-01: 외부망 브라우저 접속 확인
- [ ] 원격 PC/노트북의 브라우저에서 `http://10.0.1.157:5173` 접속
- [ ] Antigravity Terminal 헤더 및 글래스모피즘 UI가 정상 렌더링되는지 확인
- [ ] 브라우저 개발자 도구(F12) 콘솔에 오류 메시지가 없는지 확인

### UI-EXT-02: 동적 호스트 기반 API/WS 연결 확인
- [ ] 브라우저 개발자 도구(F12) → Network 탭 열기
- [ ] 콘솔에서 다음 명령어 실행: `console.log(window.location.hostname)`
- [ ] 반환 값이 `10.0.1.157`인지 확인 (localhost가 아님)
- [ ] Network 탭에서 `http://10.0.1.157:8000/api/v1/ticks/...` 요청이 200 OK로 성공하는지 확인
- [ ] WS 탭에서 `ws://10.0.1.157:8000/ws` 연결이 101 Switching Protocols로 성공하는지 확인

### UI-EXT-03: 실시간 데이터 수신 확인
- [ ] 대시보드 우측 상단 "WS: CONNECTED" 상태 표시 확인 (초록색)
- [ ] 좌측 TickerPanel에 실시간 체결 내역이 표시되는지 확인
- [ ] 우측 OrderbookChart에 호가 잔량 그래프가 표시되는지 확인
- [ ] 브라우저 개발자 도구 → WS 탭에서 메시지 수신 확인 (market_ticker, market_orderbook)
- [ ] 5초 이상 관찰하여 실시간으로 데이터가 업데이트되는지 확인

## 🔍 디버깅 가이드

### 연결 실패 시 점검 사항
1. **방화벽 확인**: 서버의 5173, 8000 포트가 외부에서 접근 가능한지 확인
   ```bash
   # 서버에서 실행
   sudo ufw status
   sudo ufw allow 5173
   sudo ufw allow 8000
   ```

2. **서비스 가동 확인**:
   ```bash
   docker ps | grep -E "api-server|dashboard-ui"
   ```

3. **API 헬스체크**:
   ```bash
   curl http://10.0.1.157:8000/health
   ```

4. **웹소켓 연결 테스트** (브라우저 콘솔):
   ```javascript
   const ws = new WebSocket('ws://10.0.1.157:8000/ws');
   ws.onopen = () => console.log('✅ WebSocket Connected');
   ws.onerror = (e) => console.error('❌ WebSocket Error:', e);
   ```

## 📝 검증 완료 기준
- [ ] 3개의 외부망 테스트(UI-EXT-01~03)가 모두 체크됨
- [ ] 브라우저 콘솔에 치명적인 오류 없음
- [ ] 실시간 데이터가 5초 이상 지속적으로 업데이트됨
- [ ] `test_registry.md`의 해당 항목을 ✅ Pass로 업데이트

## 🎯 검증 결과 보고
검증 완료 후 다음 명령어로 테스트 레지스트리를 업데이트하세요:
```markdown
# test_registry.md 업데이트 예시
| UI-EXT-01 | ... | ✅ Pass | 2026-01-08 외부망(10.0.1.157) 접속 성공 |
```
