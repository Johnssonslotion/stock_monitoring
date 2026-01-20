#!/usr/bin/env python3
"""
[ISSUE-031] Data Completeness Verification
Checks for gaps in both DuckDB and TimescaleDB
"""

import duckdb
import psycopg2
from datetime import datetime, timedelta
import os

# DB Configs
DUCKDB_PATH = "data/ticks.duckdb"
PG_HOST = os.getenv("DB_HOST", "localhost")
PG_PORT = os.getenv("DB_PORT", "5432")
PG_USER = os.getenv("DB_USER", "postgres")
PG_PASS = os.getenv("DB_PASSWORD", "password")
PG_DB = os.getenv("DB_NAME", "stockval")

TARGET_DATE = "2026-01-20"

def check_duckdb_gaps():
    """Check DuckDB for data gaps"""
    print("=" * 60)
    print("DuckDB Gap Analysis")
    print("=" * 60)
    
    try:
        conn = duckdb.connect(DUCKDB_PATH, read_only=True)
        
        # Overall stats
        query = f"""
            SELECT 
                COUNT(*) as total_ticks,
                COUNT(DISTINCT symbol) as unique_symbols,
                MIN(timestamp) as first_tick,
                MAX(timestamp) as last_tick,
                COUNT(DISTINCT source) as sources
            FROM market_ticks
            WHERE DATE(timestamp) = '{TARGET_DATE}'
        """
        result = conn.execute(query).fetchone()
        
        print(f"\n📊 Overall Statistics:")
        print(f"  Total Ticks: {result[0]:,}")
        print(f"  Unique Symbols: {result[1]}")
        print(f"  First Tick: {result[2]}")
        print(f"  Last Tick: {result[3]}")
        print(f"  Data Sources: {result[4]}")
        
        # By source
        query = f"""
            SELECT source, COUNT(*) as count
            FROM market_ticks
            WHERE DATE(timestamp) = '{TARGET_DATE}'
            GROUP BY source
            ORDER BY count DESC
        """
        sources = conn.execute(query).fetchall()
        
        print(f"\n📈 By Source:")
        for source, count in sources:
            print(f"  {source}: {count:,} ticks")
        
        # Top symbols
        query = f"""
            SELECT symbol, COUNT(*) as count
            FROM market_ticks
            WHERE DATE(timestamp) = '{TARGET_DATE}'
            GROUP BY symbol
            ORDER BY count DESC
            LIMIT 10
        """
        top_symbols = conn.execute(query).fetchall()
        
        print(f"\n🔝 Top 10 Symbols by Tick Count:")
        for symbol, count in top_symbols:
            print(f"  {symbol}: {count:,} ticks")
        
        # Gap detection by hour
        query = f"""
            SELECT 
                strftime(timestamp, '%H') as hour,
                COUNT(*) as tick_count,
                COUNT(DISTINCT symbol) as symbols
            FROM market_ticks
            WHERE DATE(timestamp) = '{TARGET_DATE}'
            GROUP BY hour
            ORDER BY hour
        """
        hourly = conn.execute(query).fetchall()
        
        print(f"\n⏰ Hourly Distribution:")
        for hour, ticks, symbols in hourly:
            print(f"  {hour}:00 - {ticks:,} ticks ({symbols} symbols)")
        
        # Check for completely missing symbols
        query = f"""
            SELECT COUNT(DISTINCT symbol) as total_symbols
            FROM market_ticks
        """
        total_symbols = conn.execute(query).fetchone()[0]
        
        print(f"\n🔍 Symbol Coverage:")
        print(f"  Total symbols ever seen: {total_symbols}")
        print(f"  Symbols with data today: {result[1]}")
        if total_symbols > result[1]:
            print(f"  ⚠️  Missing: {total_symbols - result[1]} symbols have no data today")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ DuckDB check failed: {e}")

def check_timescale_gaps():
    """Check TimescaleDB for data gaps"""
    print("\n" + "=" * 60)
    print("TimescaleDB Gap Analysis")
    print("=" * 60)
    
    try:
        conn = psycopg2.connect(
            host=PG_HOST,
            port=PG_PORT,
            user=PG_USER,
            password=PG_PASS,
            database=PG_DB
        )
        cur = conn.cursor()
        
        # Check if table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'market_ticks'
            )
        """)
        table_exists = cur.fetchone()[0]
        
        if not table_exists:
            print("⚠️  market_ticks table does not exist in TimescaleDB")
            conn.close()
            return
        
        # Overall stats
        cur.execute(f"""
            SELECT 
                COUNT(*) as total_ticks,
                COUNT(DISTINCT symbol) as unique_symbols,
                MIN(timestamp) as first_tick,
                MAX(timestamp) as last_tick
            FROM market_ticks
            WHERE DATE(timestamp) = '{TARGET_DATE}'
        """)
        result = cur.fetchone()
        
        print(f"\n📊 Overall Statistics:")
        print(f"  Total Ticks: {result[0]:,}")
        print(f"  Unique Symbols: {result[1]}")
        print(f"  First Tick: {result[2]}")
        print(f"  Last Tick: {result[3]}")
        
        # By source (if column exists)
        try:
            cur.execute(f"""
                SELECT source, COUNT(*) as count
                FROM market_ticks
                WHERE DATE(timestamp) = '{TARGET_DATE}'
                GROUP BY source
                ORDER BY count DESC
            """)
            sources = cur.fetchall()
            
            print(f"\n📈 By Source:")
            for source, count in sources:
                print(f"  {source}: {count:,} ticks")
        except:
            print("\n📈 By Source: (source column not available)")
        
        # Hourly distribution
        cur.execute(f"""
            SELECT 
                EXTRACT(HOUR FROM timestamp) as hour,
                COUNT(*) as tick_count,
                COUNT(DISTINCT symbol) as symbols
            FROM market_ticks
            WHERE DATE(timestamp) = '{TARGET_DATE}'
            GROUP BY hour
            ORDER BY hour
        """)
        hourly = cur.fetchall()
        
        print(f"\n⏰ Hourly Distribution:")
        for hour, ticks, symbols in hourly:
            print(f"  {int(hour):02d}:00 - {ticks:,} ticks ({symbols} symbols)")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ TimescaleDB check failed: {e}")

def compare_databases():
    """Compare data between DuckDB and TimescaleDB"""
    print("\n" + "=" * 60)
    print("Database Comparison")
    print("=" * 60)
    
    try:
        # DuckDB count
        duck_conn = duckdb.connect(DUCKDB_PATH, read_only=True)
        duck_count = duck_conn.execute(f"""
            SELECT COUNT(*) FROM market_ticks 
            WHERE DATE(timestamp) = '{TARGET_DATE}'
        """).fetchone()[0]
        duck_conn.close()
        
        # TimescaleDB count
        pg_conn = psycopg2.connect(
            host=PG_HOST, port=PG_PORT, user=PG_USER, 
            password=PG_PASS, database=PG_DB
        )
        cur = pg_conn.cursor()
        cur.execute(f"""
            SELECT COUNT(*) FROM market_ticks 
            WHERE DATE(timestamp) = '{TARGET_DATE}'
        """)
        pg_count = cur.fetchone()[0]
        pg_conn.close()
        
        print(f"\n📊 Tick Count Comparison:")
        print(f"  DuckDB: {duck_count:,} ticks")
        print(f"  TimescaleDB: {pg_count:,} ticks")
        
        diff = abs(duck_count - pg_count)
        if diff > 0:
            pct = (diff / max(duck_count, pg_count)) * 100
            print(f"  ⚠️  Difference: {diff:,} ticks ({pct:.2f}%)")
            
            if duck_count > pg_count:
                print(f"  → DuckDB has more data (TimescaleDB missing {diff:,} ticks)")
            else:
                print(f"  → TimescaleDB has more data (DuckDB missing {diff:,} ticks)")
        else:
            print(f"  ✅ Databases are in sync!")
            
    except Exception as e:
        print(f"❌ Comparison failed: {e}")

if __name__ == "__main__":
    print(f"\n🔍 Data Completeness Check for {TARGET_DATE}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    check_duckdb_gaps()
    check_timescale_gaps()
    compare_databases()
    
    print("\n" + "=" * 60)
    print("✅ Gap Analysis Complete")
    print("=" * 60)
