#!/usr/bin/env python3
"""
DuckDB Write Performance Benchmark

목적: 즉시 INSERT vs 배치 INSERT 성능 비교
승인: RFC-008 DevOps Lead 조건부 승인 해제용
"""

import duckdb
import time
import random
from pathlib import Path
from datetime import datetime, timedelta
import statistics

# 벤치마크 설정
TOTAL_TICKS = 50000  # 5만 건 (약 10초치 데이터)
BATCH_SIZE = 5000    # 1초치 데이터
SYMBOL_POOL = ["005930", "000660", "035420", "051910", "035720"]

def generate_tick():
    """가짜 틱 데이터 생성"""
    return (
        random.choice(SYMBOL_POOL),
        datetime.now() + timedelta(microseconds=random.randint(0, 1000000)),
        random.randint(50000, 100000),  # price
        random.randint(1, 1000),        # volume
        f"EXEC{random.randint(1000000, 9999999)}",  # execution_no
        "KIS"
    )

def setup_db(db_path: Path):
    """테스트용 DB 초기화"""
    if db_path.exists():
        db_path.unlink()
    
    conn = duckdb.connect(str(db_path))
    conn.execute("""
        CREATE TABLE market_ticks (
            symbol VARCHAR,
            timestamp TIMESTAMP,
            price DOUBLE,
            volume BIGINT,
            execution_no VARCHAR,
            source VARCHAR
        )
    """)
    return conn

def benchmark_immediate_insert(conn, ticks):
    """방법 1: 즉시 INSERT (현재 방식)"""
    print("\n🔴 [Method 1] Immediate INSERT (기존 방식)")
    print(f"   - 총 {len(ticks):,}건 개별 INSERT")
    
    start_time = time.perf_counter()
    
    for tick in ticks:
        conn.execute("""
            INSERT INTO market_ticks VALUES (?, ?, ?, ?, ?, ?)
        """, tick)
    
    elapsed = time.perf_counter() - start_time
    
    print(f"   ✅ 완료: {elapsed:.2f}초")
    print(f"   📊 처리량: {len(ticks)/elapsed:.0f} writes/sec")
    
    return elapsed

def benchmark_batch_insert(conn, ticks, batch_size):
    """방법 2: 배치 INSERT (제안 방식)"""
    print(f"\n🟢 [Method 2] Batch INSERT (배치 크기: {batch_size:,})")
    print(f"   - 총 {len(ticks):,}건 → {len(ticks)//batch_size}번 배치")
    
    start_time = time.perf_counter()
    
    for i in range(0, len(ticks), batch_size):
        batch = ticks[i:i+batch_size]
        conn.executemany("""
            INSERT INTO market_ticks VALUES (?, ?, ?, ?, ?, ?)
        """, batch)
    
    elapsed = time.perf_counter() - start_time
    
    print(f"   ✅ 완료: {elapsed:.2f}초")
    print(f"   📊 처리량: {len(ticks)/elapsed:.0f} writes/sec")
    
    return elapsed

def measure_query_performance(conn):
    """읽기 성능 측정 (OLAP 쿼리)"""
    print("\n📊 [Bonus] OLAP Query Performance")
    
    # 1분봉 집계 쿼리
    start = time.perf_counter()
    result = conn.execute("""
        SELECT 
            symbol,
            DATE_TRUNC('minute', timestamp) AS minute,
            COUNT(*) AS tick_count,
            FIRST(price ORDER BY timestamp) AS open,
            MAX(price) AS high,
            MIN(price) AS low,
            LAST(price ORDER BY timestamp) AS close,
            SUM(volume) AS volume
        FROM market_ticks
        GROUP BY symbol, minute
        ORDER BY symbol, minute
    """).fetchdf()
    elapsed = time.perf_counter() - start
    
    print(f"   - 1분봉 집계: {len(result)}개 분봉 생성")
    print(f"   - 소요 시간: {elapsed*1000:.1f}ms")
    print(f"   - DuckDB OLAP 강점 확인 ✅")

def main():
    print("=" * 60)
    print("🧪 DuckDB Write Performance Benchmark")
    print("=" * 60)
    print(f"📋 설정:")
    print(f"   - 총 틱 수: {TOTAL_TICKS:,}건")
    print(f"   - 배치 크기: {BATCH_SIZE:,}건 (1초치)")
    print(f"   - 종목 수: {len(SYMBOL_POOL)}개")
    
    # 테스트 데이터 생성
    print(f"\n🔧 테스트 데이터 생성 중...")
    ticks = [generate_tick() for _ in range(TOTAL_TICKS)]
    print(f"   ✅ {len(ticks):,}건 생성 완료")
    
    # ===== Test 1: Immediate INSERT =====
    db_path_immediate = Path("benchmark_immediate.duckdb")
    conn_immediate = setup_db(db_path_immediate)
    
    time_immediate = benchmark_immediate_insert(conn_immediate, ticks)
    conn_immediate.close()
    
    # ===== Test 2: Batch INSERT =====
    db_path_batch = Path("benchmark_batch.duckdb")
    conn_batch = setup_db(db_path_batch)
    
    time_batch = benchmark_batch_insert(conn_batch, ticks, BATCH_SIZE)
    
    # OLAP 쿼리 성능 측정
    measure_query_performance(conn_batch)
    conn_batch.close()
    
    # ===== 결과 비교 =====
    print("\n" + "=" * 60)
    print("📊 최종 결과 비교")
    print("=" * 60)
    
    improvement = ((time_immediate - time_batch) / time_immediate) * 100
    speedup = time_immediate / time_batch
    
    print(f"\n⏱️  소요 시간:")
    print(f"   - Immediate INSERT: {time_immediate:.2f}초")
    print(f"   - Batch INSERT:     {time_batch:.2f}초")
    print(f"\n🚀 성능 개선:")
    print(f"   - 속도 향상:  {speedup:.1f}배")
    print(f"   - 시간 절감:  {improvement:.1f}%")
    
    # 실제 운영 환경 시뮬레이션
    real_tps = 5000  # 실제 예상 TPS
    real_time_immediate = real_tps * (time_immediate / TOTAL_TICKS)
    real_time_batch = real_tps * (time_batch / TOTAL_TICKS)
    
    print(f"\n🏭 실제 운영 환경 (5,000 ticks/sec 가정):")
    print(f"   - Immediate INSERT: {real_time_immediate:.2f}초 소요 (1초 내 처리 {'✅' if real_time_immediate < 1 else '❌'})")
    print(f"   - Batch INSERT:     {real_time_batch:.2f}초 소요 (1초 내 처리 {'✅' if real_time_batch < 1 else '❌'})")
    
    # RFC-008 조건 충족 판정
    print(f"\n" + "=" * 60)
    print("🎯 RFC-008 DevOps Lead 조건부 승인 판정")
    print("=" * 60)
    
    if speedup >= 2.0 and real_time_batch < 1.0:
        print("✅ APPROVED: 배치 INSERT 효과 입증됨")
        print(f"   - {speedup:.1f}배 속도 향상 (목표: 2배 이상)")
        print(f"   - 실시간 처리 가능 (1초 내 {real_time_batch:.2f}초)")
        print("\n👉 다음 단계: EnhancedTickCollector 구현 시작")
    else:
        print("⚠️ CONDITIONAL: 추가 최적화 필요")
        if speedup < 2.0:
            print(f"   - 속도 향상 부족: {speedup:.1f}배 (목표: 2배 이상)")
        if real_time_batch >= 1.0:
            print(f"   - 실시간 처리 불가: {real_time_batch:.2f}초 (목표: 1초 이내)")
    
    # 청소
    print(f"\n🧹 벤치마크 파일 정리...")
    db_path_immediate.unlink()
    db_path_batch.unlink()
    print("   ✅ 완료")

if __name__ == "__main__":
    main()
