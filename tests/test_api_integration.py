import pytest
import asyncpg
import os
from fastapi.testclient import TestClient
from src.api.main import app
from datetime import datetime, timezone

# 설정 로드
DB_HOST = os.getenv("DB_HOST", "stock-timescale")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_NAME = os.getenv("DB_NAME", "stockval")
API_AUTH_SECRET = os.getenv("API_AUTH_SECRET", "super-secret-key")

@pytest.mark.asyncio
async def test_api_db_integration():
    """API와 DB 간의 통합 데이터 조회 검증 (Gate 2)"""
    
    # 1. DB에 테스트 데이터 직접 주입
    conn = await asyncpg.connect(
        user=DB_USER, password=DB_PASSWORD, database=DB_NAME, host=DB_HOST, port=DB_PORT
    )
    test_symbol = "INTEG_TEST_99"
    ts = datetime.now(timezone.utc)
    
    try:
        # 기존 데이터 삭제 (멱등성)
        await conn.execute("DELETE FROM market_ticks WHERE symbol = $1", test_symbol)
        
        # 틱 데이터 삽입
        await conn.execute("""
            INSERT INTO market_ticks (time, symbol, price, volume, change)
            VALUES ($1, $2, $3, $4, $5)
        """, ts, test_symbol, 1234.5, 100, 5.5)
        
        # 2. API를 통해 조회 수행
        # TestClient는 자체 루프를 사용하므로 앱의 startup을 기다려야 함
        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/ticks/{test_symbol}", 
                headers={"x-api-key": API_AUTH_SECRET}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) >= 1
            assert data[0]["symbol"] == test_symbol
            assert data[0]["price"] == 1234.5
            
    finally:
        # 데이터 클린업
        await conn.execute("DELETE FROM market_ticks WHERE symbol = $1", test_symbol)
        await conn.close()

@pytest.mark.asyncio
async def test_orderbook_integration():
    """호가 데이터 대용량 멀티컬럼 조회 검증 (Gate 2)"""
    conn = await asyncpg.connect(
        user=DB_USER, password=DB_PASSWORD, database=DB_NAME, host=DB_HOST, port=DB_PORT
    )
    test_symbol = "OB_INTEG_TEST"
    ts = datetime.now(timezone.utc)
    
    try:
        # 호가 더미 데이터 구성 (22개 컬럼)
        row = [ts, test_symbol]
        for i in range(20): row.append(float(i))
        
        await conn.execute(f"""
            INSERT INTO market_orderbook (
                time, symbol,
                ask_price1, ask_vol1, ask_price2, ask_vol2, ask_price3, ask_vol3, ask_price4, ask_vol4, ask_price5, ask_vol5,
                bid_price1, bid_vol1, bid_price2, bid_vol2, bid_price3, bid_vol3, bid_price4, bid_vol4, bid_price5, bid_vol5
            ) VALUES ({','.join(['$'+str(i+1) for i in range(22)])})
        """, *row)
        
        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/orderbook/{test_symbol}", 
                headers={"x-api-key": API_AUTH_SECRET}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["symbol"] == test_symbol
            assert data["ask_price1"] == 0.0
            
    finally:
        await conn.execute("DELETE FROM market_orderbook WHERE symbol = $1", test_symbol)
        await conn.close()
