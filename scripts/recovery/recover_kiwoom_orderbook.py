
import asyncio
import os
import json
import logging
import glob
from datetime import datetime
import asyncpg
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("OrderbookRecovery")

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_NAME = os.getenv("DB_NAME", "stockval")

async def recover_orderbook(date_str="20260120"):
    pool = await asyncpg.create_pool(
        user=DB_USER, password=DB_PASSWORD, database=DB_NAME, host=DB_HOST, port=DB_PORT
    )
    
    files = glob.glob(f"data/raw/kiwoom/ws_raw_{date_str}_*.jsonl")
    logger.info(f"Discovered {len(files)} files for {date_str}")
    
    total_found = 0
    batch = []
    BATCH_SIZE = 1000

    for filepath in files:
        logger.info(f"Processing {filepath}")
        with open(filepath, 'r') as f:
            for line in f:
                try:
                    row = json.loads(line)
                    msg_str = row.get('msg', '[]')
                    data_obj = json.loads(msg_str)
                    items = data_obj.get('data', [])
                    if not isinstance(items, list): items = [items]
                    
                    for item in items:
                        if not isinstance(item, dict): continue
                        if item.get('type') != '0D': continue
                        
                        symbol = item.get('item')
                        vals = item.get('values', {})
                        
                        # FID 21 is HHMMSS for orderbook in Kiwoom
                        time_str = vals.get('21')
                        if time_str:
                            # 21 sometimes has leading/trailing space? Let's strip
                            time_str = str(time_str).strip()
                            if len(time_str) == 6:
                                ts_str = f"{date_str} {time_str}"
                                ts = datetime.strptime(ts_str, "%Y%m%d %H%M%S")
                            else:
                                # Fallback to log timestamp
                                ts = datetime.fromisoformat(row.get('ts'))
                        else:
                            ts = datetime.fromisoformat(row.get('ts'))
                        
                        record = [ts, symbol, 'KIWOOM']
                        
                        # Asks 10 levels (FID 27..36 for prices, 61..70 for volumes)
                        for i in range(10):
                            price = abs(float(vals.get(str(27 + i), 0)))
                            vol = abs(float(vals.get(str(61 + i), 0)))
                            record.extend([price, vol])
                            
                        # Bids 10 levels (FID 17..26 for prices, 71..80 for volumes)
                        for i in range(10):
                            price = abs(float(vals.get(str(17 + i), 0)))
                            vol = abs(float(vals.get(str(71 + i), 0)))
                            record.extend([price, vol])
                            
                        batch.append(tuple(record))
                        total_found += 1
                        
                        if len(batch) >= BATCH_SIZE:
                            await flush_batch(pool, batch)
                            batch = []
                            
                except Exception as e:
                    continue
                    
    if batch:
        await flush_batch(pool, batch)
        
    logger.info(f"Total {total_found} orderbooks recovered for {date_str}.")
    await pool.close()

async def flush_batch(pool, batch):
    columns = [
        'time', 'symbol', 'source',
        'ask_price1', 'ask_vol1', 'ask_price2', 'ask_vol2', 'ask_price3', 'ask_vol3', 'ask_price4', 'ask_vol4',
        'ask_price5', 'ask_vol5', 'ask_price6', 'ask_vol6', 'ask_price7', 'ask_vol7', 'ask_price8', 'ask_vol8',
        'ask_price9', 'ask_vol9', 'ask_price10', 'ask_vol10',
        'bid_price1', 'bid_vol1', 'bid_price2', 'bid_vol2', 'bid_price3', 'bid_vol3', 'bid_price4', 'bid_vol4',
        'bid_price5', 'bid_vol5', 'bid_price6', 'bid_vol6', 'bid_price7', 'bid_vol7', 'bid_price8', 'bid_vol8',
        'bid_price9', 'bid_vol9', 'bid_price10', 'bid_vol10'
    ]
    async with pool.acquire() as conn:
        # Deduplication using ON CONFLICT (requires unique constraint on time, symbol, source)
        # But copy_records_to_table doesn't support ON CONFLICT.
        # We use a temporary table and then insert with ON CONFLICT.
        # This is more robust.
        
        await conn.execute("CREATE TEMP TABLE tmp_ob AS SELECT * FROM market_orderbook WITH NO DATA")
        await conn.copy_records_to_table('tmp_ob', records=batch, columns=columns)
        
        await conn.execute("""
            INSERT INTO market_orderbook 
            SELECT * FROM tmp_ob
            ON CONFLICT (time, symbol, source) DO NOTHING
        """)
        await conn.execute("DROP TABLE tmp_ob")
        
    logger.info(f"Flushed {len(batch)} records.")

if __name__ == "__main__":
    import sys
    date = sys.argv[1] if len(sys.argv) > 1 else "20260120"
    asyncio.run(recover_orderbook(date))
