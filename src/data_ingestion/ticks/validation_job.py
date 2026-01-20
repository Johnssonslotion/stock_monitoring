
import duckdb
import logging
from datetime import datetime, timedelta

logger = logging.getLogger("ValidationJob")

class ValidationJob:
    def __init__(self, db_path="data/ticks.duckdb"):
        self.db_path = db_path
        self.conn = duckdb.connect(self.db_path)
        
    def run_aggregation(self):
        """
        Aggregates market_ticks into market_ticks_validation (1-minute buckets).
        Uses UPSERT strategy (ON CONFLICT DO UPDATE).
        """
        try:
            # Upsert Query
            query = """
                INSERT INTO market_ticks_validation (
                    bucket_time, symbol, tick_count_collected, 
                    volume_sum, price_open, price_high, price_low, price_close, 
                    updated_at, validation_status
                )
                SELECT 
                    time_bucket(INTERVAL '1 minute', timestamp) as bucket_time,
                    symbol,
                    count(*) as tick_count_collected,
                    sum(volume) as volume_sum,
                    first(price) as price_open,
                    max(price) as price_high,
                    min(price) as price_low,
                    last(price) as price_close,
                    CURRENT_TIMESTAMP as updated_at,
                    'VALID' as validation_status
                FROM market_ticks
                GROUP BY 1, 2
                ON CONFLICT (bucket_time, symbol) 
                DO UPDATE SET 
                    tick_count_collected = EXCLUDED.tick_count_collected,
                    volume_sum = EXCLUDED.volume_sum,
                    price_open = EXCLUDED.price_open,
                    price_high = EXCLUDED.price_high,
                    price_low = EXCLUDED.price_low,
                    price_close = EXCLUDED.price_close,
                    updated_at = EXCLUDED.updated_at;
            """
            
            self.conn.execute(query)
            logger.info("✅ Validation aggregation completed (Upsert).")
            
        except Exception as e:
            logger.error(f"❌ Aggregation failed: {e}")

    def close(self):
        self.conn.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    job = ValidationJob()
    job.run_aggregation()
    job.close()
