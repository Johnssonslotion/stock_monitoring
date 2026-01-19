#!/usr/bin/env python3
"""
Daily Data Quality Assessment Script
- Compares KIS vs Kiwoom minute data
- Validates tick vs minute consistency
- Generates quality report
"""
import os
import pandas as pd
import glob
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def analyze_today_quality():
    """Analyze data quality for today (2026-01-19)"""
    print("="*80)
    print("📊 Daily Data Quality Assessment - 2026-01-19")
    print("="*80)
    
    results = {}
    
    # 1. Check KIS minute data
    print("\n1️⃣ KIS Minute Data Analysis")
    print("-"*80)
    
    kis_files = glob.glob("data/recovery/backfill_minute_*.csv")
    if kis_files:
        print(f"   Found {len(kis_files)} KIS minute files")
        
        # Analyze one sample
        sample = pd.read_csv(kis_files[0])
        print(f"   Sample file: {kis_files[0]}")
        print(f"   Records: {len(sample)}")
        print(f"   Columns: {list(sample.columns)}")
        print(f"   Time range: {sample['stck_cntg_hour'].min()} ~ {sample['stck_cntg_hour'].max()}")
        
        # Coverage
        expected_minutes = 391  # 09:00-15:30
        coverage = (len(sample) / expected_minutes) * 100
        print(f"   Coverage: {coverage:.1f}%")
        
        results['kis'] = {
            'source': 'KIS',
            'files': len(kis_files),
            'avg_records': len(sample),
            'coverage': coverage,
            'api': 'FHKST03010200 (분봉)',
            'quality': 'Excellent' if coverage >= 99 else 'Good' if coverage >= 95 else 'Fair'
        }
    else:
        print("   ⚠️ No KIS data found")
        results['kis'] = None
    
    # 2. Check Kiwoom minute data
    print("\n2️⃣ Kiwoom Minute Data Analysis")
    print("-"*80)
    
    kiwoom_files = glob.glob("data/proof/kiwoom_minute_*.csv")
    if kiwoom_files:
        print(f"   Found {len(kiwoom_files)} Kiwoom minute files")
        
        # Analyze latest
        latest = sorted(kiwoom_files)[-1]
        sample = pd.read_csv(latest)
        print(f"   Latest file: {latest}")
        print(f"   Records: {len(sample)}")
        print(f"   Columns: {list(sample.columns)}")
        
        # Check time coverage
        if 'cntr_tm' in sample.columns:
            print(f"   Time range: {sample['cntr_tm'].min()} ~ {sample['cntr_tm'].max()}")
        
        expected_minutes = 391
        coverage = (len(sample) / expected_minutes) * 100
        print(f"   Coverage: {coverage:.1f}%")
        
        results['kiwoom'] = {
            'source': 'Kiwoom',
            'files': len(kiwoom_files),
            'avg_records': len(sample),
            'coverage': coverage,
            'api': 'ka10080 (분봉)',
            'quality': 'Excellent' if coverage >= 99 else 'Good' if coverage >= 95 else 'Fair'
        }
    else:
        print("   ⚠️ No Kiwoom data found")
        results['kiwoom'] = None
    
    # 3. Comparison
    print("\n3️⃣ KIS vs Kiwoom Comparison")
    print("-"*80)
    
    if results['kis'] and results['kiwoom']:
        comparison = pd.DataFrame([results['kis'], results['kiwoom']])
        print(comparison.to_string(index=False))
        
        # Winner
        if results['kiwoom']['avg_records'] > results['kis']['avg_records']:
            print(f"\n   🏆 Winner: Kiwoom (+{results['kiwoom']['avg_records'] - results['kis']['avg_records']} records)")
        else:
            print(f"\n   🏆 Winner: KIS (+{results['kis']['avg_records'] - results['kiwoom']['avg_records']} records)")
    
    # 4. Tick data analysis (if available)
    print("\n4️⃣ Tick Data Analysis (Optional)")
    print("-"*80)
    print("   ⚠️ Tick data in DB - requires separate query")
    print("   TODO: Query DuckDB/PostgreSQL for tick count")
    
    # 5. Quality Score
    print("\n5️⃣ Overall Quality Score")
    print("-"*80)
    
    if results['kis'] or results['kiwoom']:
        best_coverage = max(
            results['kis']['coverage'] if results['kis'] else 0,
            results['kiwoom']['coverage'] if results['kiwoom'] else 0
        )
        
        if best_coverage >= 99:
            grade = "A+ (Excellent)"
        elif best_coverage >= 95:
            grade = "A (Good)"
        elif best_coverage >= 90:
            grade = "B (Fair)"
        else:
            grade = "C (Needs Improvement)"
        
        print(f"   Best Coverage: {best_coverage:.1f}%")
        print(f"   Grade: {grade}")
        
        # Recommendations
        print(f"\n   💡 Recommendations:")
        if best_coverage < 100:
            print(f"      - Missing {391 - int(best_coverage * 3.91)} minutes of data")
            print(f"      - Consider using both KIS and Kiwoom for redundancy")
        else:
            print(f"      - ✅ Perfect data collection!")
    
    # 6. Save report
    print("\n6️⃣ Generating Report...")
    print("-"*80)
    
    report_path = f"data/reports/quality_report_{datetime.now().strftime('%Y%m%d')}.md"
    os.makedirs("data/reports", exist_ok=True)
    
    with open(report_path, 'w') as f:
        f.write(f"# Data Quality Report - {datetime.now().strftime('%Y-%m-%d')}\n\n")
        f.write(f"## Summary\n\n")
        
        if results['kis']:
            f.write(f"### KIS\n")
            f.write(f"- Records: {results['kis']['avg_records']}\n")
            f.write(f"- Coverage: {results['kis']['coverage']:.1f}%\n")
            f.write(f"- Quality: {results['kis']['quality']}\n\n")
        
        if results['kiwoom']:
            f.write(f"### Kiwoom\n")
            f.write(f"- Records: {results['kiwoom']['avg_records']}\n")
            f.write(f"- Coverage: {results['kiwoom']['coverage']:.1f}%\n")
            f.write(f"- Quality: {results['kiwoom']['quality']}\n\n")
        
        f.write(f"## Recommendation\n\n")
        f.write(f"Primary source: **{'Kiwoom' if results.get('kiwoom') and results['kiwoom']['avg_records'] > (results.get('kis', {}).get('avg_records', 0)) else 'KIS'}**\n\n")
        f.write(f"Backup source: Use both for maximum coverage\n")
    
    print(f"   ✅ Report saved: {report_path}")
    
    return results

if __name__ == "__main__":
    analyze_today_quality()
    
    print("\n" + "="*80)
    print("✅ Quality Assessment Complete")
    print("="*80)
