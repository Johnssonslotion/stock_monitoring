import pandas as pd
import glob
from datetime import datetime, timedelta

print("# 분봉 데이터 수집 필요 구간 정의 (2026-01-01 ~ 2026-01-19)")
print("=" * 80)

# Target symbols
target_symbols = [
    '000100', '000270', '000660', '005380', '005490', '005930',
    '006400', '012330', '042700', '068270', '069500', '091180',
    '091210', '091230', '102110', '122630', '207940', '233740',
    '247540', '252670', '305540', '373220'
]

# Generate expected trading days (Jan 1 - Jan 19, excluding weekends)
start_date = datetime(2026, 1, 1)
end_date = datetime(2026, 1, 19)
expected_dates = []
current = start_date
while current <= end_date:
    # Skip weekends
    if current.weekday() < 5:  # Mon-Fri
        expected_dates.append(current.strftime('%Y-%m-%d'))
    current += timedelta(days=1)

print(f"\n## 분석 대상:")
print(f"  - 종목 수: {len(target_symbols)}")
print(f"  - 기간: 2026-01-01 ~ 2026-01-19")
print(f"  - 예상 거래일: {len(expected_dates)}일 (주말 제외)")
print(f"    {expected_dates[0]} ~ {expected_dates[-1]}")

# Check what we have in recovery folder
print(f"\n## 현재 복구 완료 현황:")
recovery_files = glob.glob("data/recovery/backfill_minute_*.csv")
print(f"  - 복구 파일 수: {len(recovery_files)}")

# Parse recovered dates from files
recovered_data = {}
for f in recovery_files:
    try:
        symbol = f.split('_')[2]
        df = pd.read_csv(f)
        if 'stck_bsop_date' in df.columns:
            dates = df['stck_bsop_date'].unique()
            recovered_data[symbol] = [str(d) for d in dates]
    except:
        pass

print(f"  - 데이터 보유 종목 수: {len(recovered_data)}")

# Identify gaps
print(f"\n## 추가 수집 필요 데이터:")

missing_inventory = []

for symbol in target_symbols:
    if symbol in recovered_data:
        # Check if we have all dates
        has_dates = set(recovered_data[symbol])
        expected_set = set([d.replace('-', '') for d in expected_dates])
        missing_dates = expected_set - has_dates
        
        if missing_dates:
            for missing_date in sorted(missing_dates):
                # Convert YYYYMMDD to YYYY-MM-DD
                formatted_date = f"{missing_date[:4]}-{missing_date[4:6]}-{missing_date[6:8]}"
                missing_inventory.append({
                    'symbol': symbol,
                    'date': formatted_date,
                    'status': 'PARTIAL'
                })
    else:
        # No data for this symbol at all
        for date in expected_dates:
            missing_inventory.append({
                'symbol': symbol,
                'date': date,
                'status': 'MISSING_ALL'
            })

if missing_inventory:
    missing_df = pd.DataFrame(missing_inventory)
    
    print(f"\n### 총 누락 건수: {len(missing_df)}")
    print(f"\n### 종목별 누락 현황:")
    symbol_summary = missing_df.groupby('symbol').size().sort_values(ascending=False)
    print(symbol_summary.to_string())
    
    print(f"\n### 날짜별 누락 현황:")
    date_summary = missing_df.groupby('date').size().sort_values(ascending=False)
    print(date_summary.head(10).to_string())
    
    # Save full inventory
    missing_df.to_csv('data/missing_minute_data_upload_spec.csv', index=False)
    print(f"\n✅ 업로드 명세 저장: data/missing_minute_data_upload_spec.csv")
    
    # Generate summary by date
    summary_by_date = missing_df.groupby('date').agg({
        'symbol': lambda x: ','.join(sorted(set(x)))
    }).reset_index()
    summary_by_date.columns = ['date', 'missing_symbols']
    summary_by_date.to_csv('data/missing_by_date_summary.csv', index=False)
    print(f"✅ 날짜별 요약 저장: data/missing_by_date_summary.csv")
    
else:
    print("\n✅ 모든 종목의 모든 거래일 데이터가 존재합니다!")

print("\n" + "=" * 80)
print("분석 완료. 외부 업로드를 위한 명세가 준비되었습니다.")
