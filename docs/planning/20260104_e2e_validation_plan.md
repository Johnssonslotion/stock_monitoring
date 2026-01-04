# Phase 1-2 통합 테스트 계획 (E2E Validation)

## 페르소나 협의 결과

### 🧪 QA Engineer
"Unit 테스트만으로는 부족합니다. **실제 환경에서 Collector → Redis → Archiver → DuckDB** 전체 파이프라인이 돌아가는지 확인해야 합니다."

### 🏗️ Architect  
"SentimentAnalyzer는 LLM API Key가 필요하고 비용이 발생합니다. 기반부터 검증하는 게 맞습니다."

### 📊 Data Scientist
"뉴스 데이터가 실제로 DuckDB에 쌓이는지 확인해야 분석 작업을 시작할 수 있습니다."

### 🔧 Infrastructure Engineer
"Docker Compose로 전체 스택을 오케스트레이션해야 합니다. Redis는 필수입니다."

### 📋 PM (Decision)
"**MVP 철학**: 완전히 동작하는 최소 기능부터 검증. E2E 테스트 후 Phase 3로 진행."

---

## Proposed Changes

### [MODIFY] `deploy/docker-compose.yml`
현재 스켈레톤 상태이므로 Redis + Python App 서비스 추가:
- `redis`: 공식 이미지 (6379 포트)
- `tick-collector`: TickCollector 실행
- `tick-archiver`: TickArchiver 실행  
- `news-collector`: NewsCollector 실행

### [NEW] `Dockerfile`
Python 애플리케이션용 컨테이너 이미지 정의.

### [NEW] `Makefile` 명령 추가
- `make up`: 전체 스택 시작
- `make verify`: DuckDB 쿼리로 데이터 확인
- `make down`: 서비스 종료

---

## Verification Plan

### 1. Docker 환경 구동
```bash
make up
```

### 2. 데이터 수집 확인 (5분 대기)
```bash
# Tick 데이터
docker exec -it archiver python -c "import duckdb; conn = duckdb.connect('data/market_data.duckdb'); print(conn.execute('SELECT count(*) FROM ticks').fetchone())"

# News 데이터  
docker exec -it news-collector python -c "import duckdb; conn = duckdb.connect('data/market_data.duckdb'); print(conn.execute('SELECT * FROM news LIMIT 5').fetchall())"
```

### 3. 로그 검증
- Collector 연결 로그 확인
- Redis Pub/Sub 메시지 확인
- Archiver Batch Insert 로그 확인

### 4. Success Criteria
- ✅ TickCollector가 Upbit WebSocket에 연결
- ✅ Redis에 `tick.*` 채널 메시지 발행
- ✅ TickArchiver가 DuckDB에 데이터 저장 (최소 10건)
- ✅ NewsCollector가 RSS 파싱 및 키워드 매칭 (최소 1건)

실패 시 Troubleshooting Playbook 참조.
