# 구현 계획: 뉴스 데이터 수집기 (NewsCollector)

## Goal Description
Phase 2의 시작점인 `NewsCollector`를 구현한다.
거래량/가격(Tick) 뿐만 아니라, **시장 심리(Sentiment)**에 영향을 주는 텍스트 데이터를 수집하여 장기 전략(Long-term)의 기반을 마련한다.

## User Review Required
> [!NOTE]
> **Data Source Scope**
> - **RSS**: Google News (US/KR Politics), Major Economic News (MK, HK).
> - **Keywords**: `Election`, `Trump`, `Geopolitics` (US) / `금투세`, `테마주`, `오너리스크` (KR).
> - **Constraint**: 오라클 프리티어 메모리(24GB) 보호를 위해 브라우저(Selenium) 없이 `aiohttp` + `feedparser` 등 경량 라이브러리만 사용.

## Proposed Changes

### [NEW] `src/data_ingestion/news/collector.py`
-   **Class**: `NewsCollector`
-   **Features**:
    -   `fetch_rss(url)`: 비동기 RSS 파싱.
    -   `filter_keywords(text)`: 정치/테마 키워드 매칭 여부 확인 (Regex).
    -   `save_to_duckdb(items)`: `news` 테이블에 저장.
-   **Cycle**: `apscheduler` 또는 `asyncio.sleep` 활용하여 1시간 주기 Polling.

### [NEW] `src/data_ingestion/news/sources.yaml`
-   수집할 RSS URL 모음 및 키워드 리스트 관리 (하드코딩 방지).

### [NEW] `tests/test_news_collector.py`
-   Mock RSS 데이터를 이용한 필터링 및 저장 로직 테스트.

## Verification Plan
### Automated Tests
```bash
poetry run pytest tests/test_news_collector.py
```
-   실제 RSS를 1회 긁어오는지 확인하는 통합 테스트 포함 (네트워크 연결 확인).

### Manual Verification
-   `make run-news-collector` 실행 후 DuckDB `news` 테이블에 데이터(제목, 링크, 키워드매칭결과)가 쌓이는지 쿼리로 확인.
