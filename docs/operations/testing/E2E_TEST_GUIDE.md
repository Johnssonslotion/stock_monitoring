# 🧪 E2E 테스트 실행 가이드

## 환경 준비

### 1단계: Docker 백엔드 시작
```bash
cd /Users/bbagsang-u/workspace/stock_monitoring
docker compose -f deploy/docker-compose.yml up -d redis timescaledb api-server
```

### 2단계: 백엔드 헬스체크
```bash
curl http://localhost:8000/api/v1/health | jq
```

예상 출력:
```json
{
  "status": "healthy",
  "db": {
    "connected": true,
    "response_ms": 1
  },
  "redis": {
    "connected": true,
    "response_ms": 1
  }
}
```

### 3단계: 프론트엔드 시작 (별도 터미널)
```bash
cd /Users/bbagsang-u/workspace/stock_monitoring/src/web
VITE_API_TARGET=http://localhost:8000 npm run dev
```

출력 확인:
```
🚀 Vite Proxy Target: http://localhost:8000 (Mode: development)

  VITE v5.4.21  ready in 100 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: http://192.168.123.109:5173/
```

**⚠️ 중요**: 이 터미널을 그대로 열어둔 채로 유지하세요!

### 4단계: 브라우저에서 수동 확인 (권장)
```bash
open http://localhost:5173/
```

확인 항목:
- ✅ Dashboard 탭: Market Map이 표시되는지
- ✅ 삼성전자 클릭 → Analysis 탭 전환
- ✅ Candle Chart가 로딩되는지
- ✅ Timeframe 전환 (1M/5M/1D)
- ✅ OrderBook, Volume Histogram 표시
- ✅ System 탭: 로그 확인

---

## E2E 자동화 테스트

### 새 터미널에서 실행
```bash
cd /Users/bbagsang-u/workspace/stock_monitoring
npx playwright test tests/e2e/map-first-layout.spec.ts
```

### 옵션들
```bash
# 헤드리스 모드 (기본값)
npx playwright test tests/e2e/map-first-layout.spec.ts

# 브라우저 UI 표시 (디버깅용)
npx playwright test tests/e2e/map-first-layout.spec.ts --headed

# 특정 테스트만 실행
npx playwright test tests/e2e/map-first-layout.spec.ts -g "should start with Map"

# 상세 로그
npx playwright test tests/e2e/map-first-layout.spec.ts --reporter=list --trace on

# 실패한 테스트만 재실행
npx playwright test tests/e2e/map-first-layout.spec.ts --last-failed
```

---

## 트러블슈팅

### 문제 1: ERR_CONNECTION_REFUSED
**증상**: `net::ERR_CONNECTION_REFUSED at http://localhost:5173/`

**원인**: Vite 서버가 실행되지 않았거나 종료됨

**해결**:
```bash
# 포트 확인
lsof -ti:5173

# 없으면 재시작
cd src/web
VITE_API_TARGET=http://localhost:8000 npm run dev
```

### 문제 2: 백엔드 API 에러
**증상**: 콘솔에 `[vite] http proxy error: /api/v1/...`

**원인**: Docker 백엔드가 실행되지 않음

**해결**:
```bash
# Docker 상태 확인
docker ps | grep stock

# 없으면 시작
cd deploy
docker compose -f docker-compose.yml up -d redis timescaledb api-server
```

### 문제 3: 페이지가 로딩되지 않음
**증상**: 브라우저가 계속 로딩 중

**원인**: Mock 데이터 로직 오류 또는 무한 루프

**해결**:
```bash
# 브라우저 콘솔 확인 (F12)
# Vite 터미널 로그 확인

# 필요 시 재시작
pkill -f vite
cd src/web
npm run dev
```

---

## E2E 테스트 결과 예상

### 성공 시
```
Running 3 tests using 1 worker

  ✓  1 › should start with Map expanded (70%) and Chart collapsed (30%) (2.3s)
  ✓  2 › should slide up chart when a symbol is clicked (1.8s)
  ✓  3 › should load symbol from URL (1.5s)

  3 passed (5.6s)
```

### 실패 시
```
  ✘  1 › should start with Map expanded (70%) and Chart collapsed (30%)
  
  Error: ...
  
  at /Users/.../tests/e2e/map-first-layout.spec.ts:7:20
```

**디버깅**:
1. `test-results/` 폴더 확인
2. 스크린샷 및 비디오 확인
3. `trace.zip` 다운로드 → [trace.playwright.dev](https://trace.playwright.dev)에서 분석

---

## 수동 테스트 체크리스트

Phase 14 완료 검증을 위한 체크리스트:

### Dashboard 탭
- [ ] Market Map 렌더링
- [ ] 섹터별 색상 구분 (반도체/이차전지/자동차)
- [ ] 종목 클릭 → Analysis 탭 전환
- [ ] TickerTape 스크롤

### Analysis 탭
- [ ] Candle Chart 표시 (일봉 기본)
- [ ] Timeframe 전환 (1M/5M/1D)
- [ ] Zoom In/Out 버튼 동작
- [ ] OrderBookView 5단계 호가 표시
- [ ] VolumeHistogram Bid/Ask 분리
- [ ] MarketInfoPanel Split View (News | Related)

### System 탭
- [ ] SystemDashboard CPU/메모리 표시
- [ ] LogsView 로그 스트리밍

### 데이터 소스
- [ ] Mock Fallback 동작 (API 실패 시)
- [ ] Data Quality Badge 표시
- [ ] Simulation Mode 워닝 (필요 시)

---

## 환경 변수

```bash
# Vite 프록시 타겟 (기본값: http://localhost:8000)
VITE_API_TARGET=http://localhost:8000

# API 인증 키 (선택)
VITE_API_KEY=backtest-secret-key
```

---

## 참고 문서

- [UI Test Report](UI_TEST_REPORT.md) - 전체 테스트 시나리오
- [BACKLOG](../BACKLOG.md) - 미구현 기능 목록
- [Master Roadmap](../../strategy/master_roadmap.md) - 프로젝트 로드맵

---

**작성일**: 2026-01-16  
**작성자**: AI Agent  
**Phase**: 14 - Safe Integration
