# CSV Data Ingestion Guide

이 문서는 외부(Windows/HTS 등)에서 수집한 주식 CSV 데이터를 로컬 서버 DB로 적재하는 방법을 안내합니다.

## 1. 사전 준비
- **Python 3.8 이상** 설치
- 필요한 라이브러리 설치:
  ```bash
  pip install asyncpg python-dotenv
  ```

## 2. 데이터 파일 준비
`scripts/data_ingest/` 폴더에 CSV 파일을 위치시킵니다.
파일 이름은 반드시 다음 규칙을 따라야 자동으로 인식됩니다.

- **분봉/일봉 데이터**: `*_candles.csv` (예: `samsung_2025_candles.csv`)
- **호가 데이터**: `*_orderbook.csv` (예: `samsung_2025_orderbook.csv`)

### CSV 템플릿 확인
`scripts/templates/` 폴더 내의 예제 파일을 참고하세요.
- `candles_template.csv`: `time,symbol,interval,open,high,low,close,volume`
- `orderbook_template.csv`: `time,symbol,ask_price1,ask_vol1...`

## 3. 적재 실행
프로젝트 루트(`stock_monitoring`)에서 다음 명령어를 실행합니다.

```bash
# 로컬(Mac)에서 바로 실행 시
python scripts/ingest_csv.py

# Docker 컨테이너 내부에서 실행 시 (권장)
docker exec -it dashboard-ui python scripts/ingest_csv.py
```
*(주의: 로컬 실행 시 DB 접속 정보가 `.env` 파일에 올바르게 설정되어 있어야 합니다.)*

## 4. 결과 확인
로그에 `✅ Successfully ingested...` 메시지가 뜨면 성공입니다.
DB에서 데이터가 잘 들어갔는지 확인하려면:
```bash
make db-shell
SELECT count(*) FROM market_candles;
```
