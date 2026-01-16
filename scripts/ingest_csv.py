import asyncio
import asyncpg
import csv
import os
import glob
import logging
from datetime import datetime

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 환경 변수 설정 (기본값은 Docker 내부 기준, 외부 실행 시 .env 로드 필요)
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_NAME = os.getenv("DB_NAME", "stockval")

async def get_db_connection():
    """DB 연결 생성"""
    try:
        conn = await asyncpg.connect(
            user=DB_USER, 
            password=DB_PASSWORD, 
            database=DB_NAME, 
            host=DB_HOST, 
            port=DB_PORT
        )
        return conn
    except Exception as e:
        logger.error(f"❌ DB Connection Failed: {e}")
        raise

async def ingest_file(conn, file_path, table_name):
    """단일 CSV 파일 적재 (COPY 방식)"""
    filename = os.path.basename(file_path)
    logger.info(f"📂 Processing {filename} into {table_name}...")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = next(reader) # Read header
            
            # 테이블 컬럼 확인 (간단한 검증)
            # COPY 명령 실행
            # asyncpg의 copy_records_to_table은 리스트/튜플 데이터를 넣을 때 사용
            # 파일에서 직접 넣을 때는 copy_from_query나 raw copy를 써야 함.
            # 하지만 CSV 포맷이 잘 맞다면 copy_to_table을 메모리로 읽어서 쓸 수도 있음.
            # 대용량이므로 메모리 부하를 줄이기 위해 파일을 직접 읽어서 스트리밍하는 것이 좋음.
            
            f.seek(0) # Reset to beginning including header? No, COPY needs CSV format
            # COPY ... WITH (FORMAT CSV, HEADER) handles header skipping
            
            # asyncpg copy_from_stream is complex? No.
            # Use connection.copy_to_table is for exporting.
            # connection.copy_records_to_table is for inserting python objects.
            # For raw CSV file ingestion, `copy_from` isn't directly exposed as 'file path' in asyncpg due to server vs client path.
            # We are client. We read file and push data.
            
            records = []
            # Performance note: For millions of rows, reading all into memory is bad.
            # Example uses generators or chunking.
            
            # Let's use a simpler approach: Read header, then chunk read rows and use copy_records_to_table.
            # It handles types automatically? No, we need to ensure types.
            # But wait, CSV contains strings. Postgres COPY handles conversion if format matches.
            
            # Alternative: Use `conn.copy_from_stream` if we convert file to a stream? 
            # Or just use `conn.execute` with `COPY ... FROM STDIN`?
            # asyncpg allows `conn.copy_records_to_table` which takes an iterable.
            
            # Let's map headers to columns
            # Remove 'time' types mapping if handled by PG.
            
            # Re-read to skip header properly for data processing if manual
            next(reader) 
            
            batch_size = 5000
            batch = []
            total_rows = 0
            
            for row in reader:
                # Basic Type Conversion to match exact PG types if needed?
                # For `market_candles`: time(ts), symbol(text), interval(text), open(float)...
                # CSV read gives strings. asyncpg copy_records_to_table might expect native types.
                # Let's try to convert based on simple rules or let PG handle specific columns if possible.
                # Actually, simplest is to CAST in python.
                
                # Check table type
                if table_name == 'market_candles':
                    # time, symbol, interval, open, high, low, close, volume (8 cols)
                    if len(row) < 8: continue
                    # row[0] is string time, pg can parse standard ISO
                    # row[3]~row[7] are numbers
                    try:
                        valid_row = (
                            datetime.fromisoformat(row[0].replace('Z', '')), # Time
                            row[1], # Symbol
                            row[2], # Interval
                            float(row[3]), # Open
                            float(row[4]), # High
                            float(row[5]), # Low
                            float(row[6]), # Close
                            float(row[7])  # Volume
                        )
                        batch.append(valid_row)
                    except ValueError:
                        logger.warning(f"Skipping invalid row in {filename}: {row}")
                        continue
                        
                elif table_name == 'market_orderbook':
                    # time, symbol, ask1... (22 cols)
                    if len(row) < 3: continue 
                    try:
                        # Time, Symbol are 0, 1. Rest are floats.
                        valid_row = [datetime.fromisoformat(row[0].replace('Z', '')), row[1]]
                        for val in row[2:]:
                            valid_row.append(float(val) if val else None)
                        batch.append(tuple(valid_row))
                        
                    except ValueError:
                         logger.warning(f"Skipping invalid row in {filename}: {row}")
                         continue
                
                if len(batch) >= batch_size:
                    await conn.copy_records_to_table(table_name, records=batch, columns=headers)
                    total_rows += len(batch)
                    batch = []
                    
            # Insert remaining
            if batch:
                await conn.copy_records_to_table(table_name, records=batch, columns=headers)
                total_rows += len(batch)
                
            logger.info(f"✅ Successfully ingested {total_rows} rows from {filename}")
            
    except Exception as e:
        logger.error(f"❌ Failed to ingest {filename}: {e}")

async def main():
    target_dir = "scripts/data_ingest" # Input folder
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
        logger.info(f"Created input directory: {target_dir}")
        logger.info("Please place your CSV files here and run again.")
        return

    logger.info("🔌 Connecting to Database...")
    conn = await get_db_connection()
    
    try:
        # 1. Candles
        candle_files = glob.glob(os.path.join(target_dir, "*_candles.csv"))
        for f in candle_files:
            await ingest_file(conn, f, "market_candles")
            
        # 2. Orderbooks
        ob_files = glob.glob(os.path.join(target_dir, "*_orderbook.csv"))
        for f in ob_files:
            await ingest_file(conn, f, "market_orderbook")
            
        if not candle_files and not ob_files:
            logger.warning("⚠️ No matching CSV files found. (Naming: *_candles.csv, *_orderbook.csv)")
            
    finally:
        await conn.close()
        logger.info("👋 Connection closed.")

if __name__ == "__main__":
    try:
        import dotenv
        dotenv.load_dotenv()
    except ImportError:
        pass
    
    asyncio.run(main())
