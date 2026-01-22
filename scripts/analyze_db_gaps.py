import duckdb
import pandas as pd
from datetime import datetime, timedelta

# Connect to DuckDB
conn = duckdb.connect('data/ticks.duckdb', read_only=True)

print("# 분봉 데이터 갭 분석 (2026-01-01 ~ 2026-01-19)")
print("=" * 80)

# Check if candles table exists
tables = conn.execute("SHOW TABLES").fetchall()
print(f"\n## 사용 가능한 테이블:")
for table in tables:
    print(f"  - {table[0]}")

# Try to find candle/minute data
# Typical table names: candles_1m, market_candles, minute_bars, etc.
candle_tables = [t[0] for t in tables if 'candle' in t[0].lower() or 'minute' in t[0].lower() or 'bar' in t[0].lower()]

if not candle_tables:
    print("\n⚠️ 분봉 전용 테이블을 찾을 수 없습니다.")
    print("   market_ticks 테이블에서 분봉 집계를 시도합니다...\n")
    
    # Check market_ticks
    try:
        # Get date range
        date_range = conn.execute("""
            SELECT 
                DATE(MIN(time)) as first_date,
                DATE(MAX(time)) as last_date,
                COUNT(DISTINCT DATE(time)) as trading_days,
                COUNT(DISTINCT symbol) as symbols_count
            FROM market_ticks
        """).fetchdf()
        
        print("## market_ticks 현황:")
        print(date_range.to_string(index=False))
        
        # Get daily coverage by symbol
        daily_coverage = conn.execute("""
            SELECT 
                symbol,
                DATE(time) as date,
                COUNT(*) as tick_count,
                MIN(time) as first_tick,
                MAX(time) as last_tick
            FROM market_ticks
            WHERE DATE(time) >= '2026-01-01'
            GROUP BY symbol, DATE(time)
            ORDER BY date, symbol
        """).fetchdf()
        
        print(f"\n## 일별 종목별 틱 데이터 현황:")
        print(f"총 {len(daily_coverage)} 개의 (종목, 날짜) 조합 확인됨\n")
        
        # Identify gaps
        target_symbols = [
            '000100', '000270', '000660', '005380', '005490', '005930',
            '006400', '012330', '042700', '068270', '069500', '091180',
            '091210', '091230', '102110', '122630', '207940', '233740',
            '247540', '252670', '305540', '373220'
        ]
        
        # Generate expected trading days (excluding weekends for simplicity)
        start_date = datetime(2026, 1, 1)
        end_date = datetime(2026, 1, 19)
        expected_dates = []
        current = start_date
        while current <= end_date:
            # Skip weekends (rough approximation)
            if current.weekday() < 5:  # Mon-Fri
                expected_dates.append(current.date())
            current += timedelta(days=1)
        
        print(f"## 예상 거래일: {len(expected_dates)}일")
        print(f"   ({expected_dates[0]} ~ {expected_dates[-1]})\n")
        
        # Find missing data
        actual_coverage = set()
        for _, row in daily_coverage.iterrows():
            actual_coverage.add((row['symbol'], str(row['date'])))
        
        missing_data = []
        for symbol in target_symbols:
            for date in expected_dates:
                if (symbol, str(date)) not in actual_coverage:
                    missing_data.append({'symbol': symbol, 'date': str(date)})
        
        if missing_data:
            missing_df = pd.DataFrame(missing_data)
            print(f"## 누락된 데이터 (총 {len(missing_df)} 건):")
            print("\n### 종목별 누락 현황:")
            symbol_gaps = missing_df.groupby('symbol').size().sort_values(ascending=False)
            print(symbol_gaps.to_string())
            
            # Save to file
            missing_df.to_csv('data/missing_minute_data_inventory.csv', index=False)
            print(f"\n✅ 누락 데이터 목록 저장: data/missing_minute_data_inventory.csv")
            
        else:
            print("✅ 모든 종목의 모든 거래일 데이터가 존재합니다!")
            
    except Exception as e:
        print(f"❌ 오류: {e}")
else:
    print(f"\n## 분봉 테이블 발견: {candle_tables}")
    # Query the candle table directly
    for table in candle_tables:
        print(f"\n### {table} 현황:")
        try:
            summary = conn.execute(f"""
                SELECT 
                    COUNT(*) as total_rows,
                    COUNT(DISTINCT symbol) as symbols,
                    MIN(time) as first_time,
                    MAX(time) as last_time
                FROM {table}
            """).fetchdf()
            print(summary.to_string(index=False))
        except Exception as e:
            print(f"   오류: {e}")

conn.close()
