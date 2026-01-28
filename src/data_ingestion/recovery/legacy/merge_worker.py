import duckdb
import os
import glob
import logging
import argparse
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MergeWorker")

# Constants
MAIN_DB_PATH = "data/ticks.duckdb"
RECOVERY_DIR = "data/recovery"

def merge_recovery_data(cleanup=False):
    """
    Looks for recovery_temp_*.duckdb files and merges them into main ticks.duckdb.
    Uses ATTACH logic to minimize memory usage.
    """
    pattern = os.path.join(RECOVERY_DIR, "recovery_temp_*.duckdb")
    temp_files = glob.glob(pattern)
    
    if not temp_files:
        logger.info("No temporary recovery files found.")
        return

    logger.info(f"Found {len(temp_files)} recovery files. Starting merge...")
    
    # Connect to MAIN DB
    try:
        conn = duckdb.connect(MAIN_DB_PATH)
        
        # Ensure main table exists
        conn.execute("""
            CREATE TABLE IF NOT EXISTS market_ticks (
                symbol VARCHAR,
                timestamp TIMESTAMP,
                price DOUBLE,
                volume INT,
                source VARCHAR,
                execution_no VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        for temp_file in temp_files:
            try:
                logger.info(f"Merging {temp_file}...")
                
                # ATTACH temp db
                conn.execute(f"ATTACH '{temp_file}' AS temp_db")
                
                # INSERT OR IGNORE execution_no for deduplication
                # Note: DuckDB doesn't strictly support INSERT OR IGNORE on generic tables easily without constraints.
                # Standard SQL merge:
                count_query = "SELECT COUNT(*) FROM temp_db.market_ticks"
                count = conn.execute(count_query).fetchone()[0]
                
                if count > 0:
                    # Using INSERT ... SELECT ... WHERE NOT EXISTS for deduplication
                    query = """
                        INSERT INTO main.market_ticks 
                        SELECT * FROM temp_db.market_ticks t1
                        WHERE NOT EXISTS (
                            SELECT 1 FROM main.market_ticks t2 
                            WHERE t2.execution_no = t1.execution_no
                            AND t2.symbol = t1.symbol
                        )
                    """
                    conn.execute(query)
                    logger.info(f"Merged {count} rows from {temp_file}")
                else:
                    logger.info(f"Skipping empty file {temp_file}")

                # DETACH
                conn.execute("DETACH temp_db")
                
                # Delete file if cleanup is True
                if cleanup:
                    os.remove(temp_file)
                    logger.info(f"Deleted {temp_file}")
                    
            except Exception as e:
                logger.error(f"Failed to merge {temp_file}: {e}")
                # Try to detach if stuck
                try: conn.execute("DETACH temp_db") 
                except: pass

        conn.close()
        logger.info("✅ All merges completed successfully.")
        
    except Exception as e:
        logger.critical(f"Critical DB Error during merge: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Merge Recovery Data to Main DB')
    parser.add_argument('--cleanup', action='store_true', help='Delete temporary files after merge')
    args = parser.parse_args()
    
    merge_recovery_data(cleanup=args.cleanup)
