
import duckdb
import os

db_path = "data/ticks.duckdb"

if not os.path.exists(db_path):
    print(f"Error: {db_path} does not exist")
    exit(1)

conn = duckdb.connect(db_path)
try:
    # Check total count for today
    query = """
        SELECT source, count(*), min(timestamp), max(timestamp)
        FROM market_ticks
        WHERE strftime(timestamp, '%Y-%m-%d') = '2026-01-20'
        GROUP BY source
    """
    results = conn.execute(query).fetchall()
    for row in results:
        print(f"Source: {row[0]}, Count: {row[1]}, Min: {row[2]}, Max: {row[3]}")
    
    # Check sample if count > 0
    if result[0][0] > 0:
        sample = conn.execute("SELECT * FROM market_ticks WHERE strftime(timestamp, '%Y-%m-%d') = '2026-01-20' LIMIT 1").fetchall()
        print(f"Sample: {sample}")

except Exception as e:
    print(f"Error querying DuckDB: {e}")
finally:
    conn.close()
