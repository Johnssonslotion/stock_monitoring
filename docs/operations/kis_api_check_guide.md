# KIS API 실시간 체결 데이터 확인 가이드

## 📚 공식 문서

### KIS Developers 포털
- **메인**: https://apiportal.koreainvestment.com/
- **WebSocket 가이드**: https://apiportal.koreainvestment.com/apiservice/apiservice-domestic-stock-websocket
- **국내주식 실시간체결가**: TR ID `H0STCNT0`
- **해외주식 실시간체결가**: TR ID `HHDFS00000`

### 문서 위치
```
접속 → API Catalogue → 국내주식-시세 → WebSocket → 실시간시세
```

---

## 🔍 현재 코드에서 확인

### 1. 파싱 로직 확인
**국내주식 (KR):**
```
src/data_ingestion/price/kr/real_collector.py
  - Line 68-91: parse_tick() 함수
  - Field 구조: fields[0]=종목코드, [2]=현재가, [5]=전일대비, [7]=누적거래량
```

**미국주식 (US):**
```
src/data_ingestion/price/us/real_collector.py
  - 유사한 파싱 로직
```

### 2. WebSocket 메시지 핸들러
```
src/data_ingestion/price/common/websocket_base.py
  - Line 61-112: handle_message() 함수
  - 메시지 구조: message[0]이 '0' 또는 '1'로 시작
  - 파이프(|) 구분: parts[0]=타입, [1]=TR_ID, [3]=BODY
```

---

## 🧪 실시간 메시지 확인 방법

### 방법 1: Docker 로그 (내일 아침)
```bash
# 실시간 로그 모니터링
docker logs -f 2ecc7d720543

# 특정 시간대 로그
docker logs --since "2026-01-10T09:00:00+09:00" 2ecc7d720543 | grep "📨 RAW MSG"
```

### 방법 2: Redis MONITOR (현재 가능)
```bash
# Redis에 발행되는 메시지 실시간 확인
docker exec -it stock-redis redis-cli MONITOR | grep "ticker"
```

### 방법 3: 직접 WebSocket 연결 (테스트)
프로젝트에 `debug_kis.py` 파일이 있는지 확인:
```bash
cat debug_kis.py  # 있다면 직접 실행 가능
```

---

## 📋 예상 메시지 포맷

### KIS WebSocket 응답 예시 (추정)
```
# 구독 성공 응답 (JSON)
{"header":{"tr_id":"H0STCNT0"},"body":{"msg1":"SUBSCRIBE SUCCESS"}}

# 실제 체결 데이터 (Pipe 구분)
0|H0STCNT0|...|005930^60000^+500^...
```

**현재 문제:**
- Line 63: `if message[0] not in ['0', '1']` 체크
- JSON 응답은 `{`로 시작 → 통과
- 실제 데이터가 어떤 문자로 시작하는지 확인 필요

---

## 🎯 추천 작업 순서

1. **KIS API 문서 확인**
   - H0STCNT0 WebSocket 응답 포맷 확인
   - 실제 체결 데이터 구조 파악

2. **내일 아침 로그 확인** (디버그 로깅 활성화됨)
   ```bash
   docker logs 2ecc7d720543 | grep "📨 RAW MSG" | head -20
   ```

3. **메시지 포맷 분석**
   - 첫 문자가 뭔지 확인
   - 파이프 구분 여부 확인
   - TR_ID 위치 확인

4. **코드 수정**
   - 필요시 `handle_message()` 필터 조건 수정
   - 파싱 로직 조정
