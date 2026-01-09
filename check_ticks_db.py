import duckdb

try:
    conn = duckdb.connect('data/ticks.duckdb', read_only=True)
    
    # Check if table exists
    tables = conn.execute("SHOW TABLES").fetchall()
    print(f"Tables: {tables}")
    
    if tables:
        # Get row count
        count = conn.execute("SELECT COUNT(*) FROM ticks").fetchone()
        print(f"Total ticks: {count[0]}")
        
        # Get latest timestamp
        latest = conn.execute("SELECT MAX(timestamp) as latest FROM ticks").fetchone()
        print(f"Latest tick timestamp: {latest[0]}")
        
        # Get recent ticks (last 5)
        recent = conn.execute("SELECT * FROM ticks ORDER BY timestamp DESC LIMIT 5").fetchall()
        print(f"\nRecent ticks:")
        for row in recent:
            print(row)
    
    conn.close()
except Exception as e:
    print(f"Error: {e}")
