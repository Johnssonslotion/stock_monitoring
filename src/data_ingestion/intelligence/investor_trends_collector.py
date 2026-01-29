"""
InvestorTrendsCollector - 투자자별 매매동향 수집기

Pillar 8: Market Intelligence & Rotation Analysis
RFC: RFC-010
ISSUE: ISSUE-050

투자자별(외국인/기관/개인) 순매수 데이터를 수집하여
investor_trends 테이블에 저장합니다.

TR ID: FHKST01010900 (주식현재가 투자자) - 검증 완료 (2026-01-29)

Usage:
    collector = InvestorTrendsCollector()
    await collector.run()
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

import asyncpg
import yaml

from src.api_gateway.hub.clients.kis_client import KISClient

logger = logging.getLogger("InvestorTrendsCollector")

# Config
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_NAME = os.getenv("DB_NAME", "stockval")

# TR ID (검증 완료)
TR_INVESTOR = "FHKST01010900"


class InvestorTrendsCollector:
    """
    투자자별 매매동향 수집기

    - 외국인, 기관, 개인 순매수량/대금 수집
    - API Hub Queue를 통한 Rate Limit 준수
    - 장 마감 후 (15:40 KST 이후) 일일 배치 수집

    Attributes:
        kis_client: KIS API 클라이언트
        db_pool: PostgreSQL 연결 풀
        symbols: 수집 대상 종목 리스트
    """

    def __init__(self):
        self.kis_client: Optional[KISClient] = None
        self.db_pool: Optional[asyncpg.Pool] = None
        self.symbols: List[str] = []
        self._is_running = False

    async def init_db(self) -> None:
        """
        데이터베이스 연결 및 테이블 검증

        Raises:
            RuntimeError: investor_trends 테이블이 없는 경우
        """
        conn = await asyncpg.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            host=DB_HOST,
            port=DB_PORT
        )
        try:
            exists = await conn.fetchval(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'investor_trends')"
            )
            if not exists:
                logger.warning(
                    "Table 'investor_trends' not found. "
                    "Run: psql -f sql/migrations/007_pillar8_market_intelligence.sql"
                )
                # 테이블이 없어도 계속 진행 (개발 편의)
            else:
                logger.info("Database schema verified: investor_trends table exists")
        finally:
            await conn.close()

        # Connection Pool 생성
        self.db_pool = await asyncpg.create_pool(
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            host=DB_HOST,
            port=DB_PORT,
            min_size=2,
            max_size=10
        )
        logger.info("Database connection pool created")

    async def init_kis_client(self) -> None:
        """KIS API 클라이언트 초기화 및 토큰 발급"""
        self.kis_client = KISClient()
        await self.kis_client.connect()

        # 토큰 발급
        token = await self.kis_client.refresh_token()
        logger.info(f"KIS token acquired: {token[:20]}...")

    async def load_symbols(self) -> None:
        """
        configs/kr_symbols.yaml에서 수집 대상 종목 로드
        """
        try:
            with open("configs/kr_symbols.yaml", "r") as f:
                config = yaml.safe_load(f)

            # 재귀적으로 모든 symbol 추출
            self._extract_symbols(config.get("symbols", {}))

            logger.info(f"Loaded {len(self.symbols)} symbols for investor trends collection")

        except FileNotFoundError:
            logger.warning("configs/kr_symbols.yaml not found, using default symbols")
            self.symbols = ["005930", "000660", "035720"]  # 삼성전자, SK하이닉스, 카카오
        except Exception as e:
            logger.error(f"Failed to load symbols: {e}")
            self.symbols = ["005930"]

    def _extract_symbols(self, data: Any) -> None:
        """재귀적으로 심볼 추출"""
        if isinstance(data, list):
            for item in data:
                self._extract_symbols(item)
        elif isinstance(data, dict):
            if "symbol" in data:
                self.symbols.append(data["symbol"])
            else:
                for value in data.values():
                    self._extract_symbols(value)

    async def fetch_investor_data(self, symbol: str) -> Optional[List[Dict[str, Any]]]:
        """
        단일 종목의 투자자별 매매동향 조회

        Args:
            symbol: 종목코드 (예: "005930")

        Returns:
            투자자 데이터 리스트 또는 None (실패 시)
        """
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",  # 주식
            "FID_INPUT_ISCD": symbol
        }

        try:
            result = await self.kis_client.execute(
                tr_id=TR_INVESTOR,
                params=params
            )

            if result.get("status") == "success":
                data = result.get("data", [])
                logger.debug(f"Fetched {len(data)} records for {symbol}")
                return data
            else:
                logger.warning(f"API returned non-success for {symbol}: {result}")
                return None

        except Exception as e:
            logger.error(f"Failed to fetch investor data for {symbol}: {e}")
            return None

    def transform_record(self, symbol: str, row: Dict[str, Any]) -> Dict[str, Any]:
        """
        API 응답을 DB 레코드로 변환

        Args:
            symbol: 종목코드
            row: API 응답의 단일 레코드

        Returns:
            DB INSERT용 딕셔너리
        """
        # 날짜 파싱
        date_str = row.get("stck_bsop_date", "")
        if date_str:
            dt = datetime.strptime(date_str, "%Y%m%d")
        else:
            dt = datetime.now()

        return {
            "time": dt,
            "symbol": symbol,
            # 외국인
            "foreign_buy": self._safe_int(row.get("frgn_shnu_vol")),
            "foreign_sell": self._safe_int(row.get("frgn_seln_vol")),
            "foreign_net": self._safe_int(row.get("frgn_ntby_qty")),
            "foreign_amount": self._safe_int(row.get("frgn_ntby_tr_pbmn")),
            # 기관
            "institution_buy": self._safe_int(row.get("orgn_shnu_vol")),
            "institution_sell": self._safe_int(row.get("orgn_seln_vol")),
            "institution_net": self._safe_int(row.get("orgn_ntby_qty")),
            "institution_amount": self._safe_int(row.get("orgn_ntby_tr_pbmn")),
            # 개인
            "retail_buy": self._safe_int(row.get("prsn_shnu_vol")),
            "retail_sell": self._safe_int(row.get("prsn_seln_vol")),
            "retail_net": self._safe_int(row.get("prsn_ntby_qty")),
            "retail_amount": self._safe_int(row.get("prsn_ntby_tr_pbmn")),
            # 메타
            "source": "KIS"
        }

    @staticmethod
    def _safe_int(value: Any) -> Optional[int]:
        """안전한 정수 변환"""
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    async def save_records(self, records: List[Dict[str, Any]]) -> int:
        """
        DB에 레코드 저장

        Args:
            records: 저장할 레코드 리스트

        Returns:
            저장된 레코드 수
        """
        if not records or not self.db_pool:
            return 0

        async with self.db_pool.acquire() as conn:
            try:
                # Batch INSERT with ON CONFLICT
                saved = 0
                for record in records:
                    result = await conn.execute("""
                        INSERT INTO investor_trends (
                            time, symbol,
                            foreign_buy, foreign_sell, foreign_net, foreign_amount,
                            institution_buy, institution_sell, institution_net, institution_amount,
                            retail_buy, retail_sell, retail_net, retail_amount,
                            source
                        ) VALUES (
                            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15
                        )
                        ON CONFLICT (time, symbol) DO UPDATE SET
                            foreign_buy = EXCLUDED.foreign_buy,
                            foreign_sell = EXCLUDED.foreign_sell,
                            foreign_net = EXCLUDED.foreign_net,
                            foreign_amount = EXCLUDED.foreign_amount,
                            institution_buy = EXCLUDED.institution_buy,
                            institution_sell = EXCLUDED.institution_sell,
                            institution_net = EXCLUDED.institution_net,
                            institution_amount = EXCLUDED.institution_amount,
                            retail_buy = EXCLUDED.retail_buy,
                            retail_sell = EXCLUDED.retail_sell,
                            retail_net = EXCLUDED.retail_net,
                            retail_amount = EXCLUDED.retail_amount,
                            source = EXCLUDED.source
                    """,
                        record["time"],
                        record["symbol"],
                        record["foreign_buy"],
                        record["foreign_sell"],
                        record["foreign_net"],
                        record["foreign_amount"],
                        record["institution_buy"],
                        record["institution_sell"],
                        record["institution_net"],
                        record["institution_amount"],
                        record["retail_buy"],
                        record["retail_sell"],
                        record["retail_net"],
                        record["retail_amount"],
                        record["source"]
                    )
                    saved += 1

                return saved

            except Exception as e:
                logger.error(f"Database save error: {e}")
                return 0

    async def collect_symbol(self, symbol: str) -> int:
        """
        단일 종목의 투자자 데이터 수집 및 저장

        Args:
            symbol: 종목코드

        Returns:
            저장된 레코드 수
        """
        # 1. API 호출
        raw_data = await self.fetch_investor_data(symbol)
        if not raw_data:
            return 0

        # 2. 데이터 변환
        records = [self.transform_record(symbol, row) for row in raw_data]

        # 3. DB 저장
        saved = await self.save_records(records)

        logger.info(f"[{symbol}] Saved {saved} investor trend records")
        return saved

    async def collect_all(self) -> Dict[str, int]:
        """
        모든 종목의 투자자 데이터 수집

        Returns:
            종목별 저장 건수 딕셔너리
        """
        results = {}
        total = len(self.symbols)

        for i, symbol in enumerate(self.symbols, 1):
            logger.info(f"[{i}/{total}] Collecting {symbol}...")

            try:
                count = await self.collect_symbol(symbol)
                results[symbol] = count
            except Exception as e:
                logger.error(f"Failed to collect {symbol}: {e}")
                results[symbol] = 0

            # Rate Limit 대응 (0.5초 간격)
            await asyncio.sleep(0.5)

        return results

    async def run_once(self) -> Dict[str, Any]:
        """
        단일 실행 (테스트/수동 실행용)

        Returns:
            실행 결과 요약
        """
        start_time = datetime.now()

        # 초기화
        await self.init_db()
        await self.init_kis_client()
        await self.load_symbols()

        # 수집
        results = await self.collect_all()

        # 정리
        if self.kis_client:
            await self.kis_client.disconnect()
        if self.db_pool:
            await self.db_pool.close()

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        summary = {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration,
            "symbols_processed": len(results),
            "total_records": sum(results.values()),
            "results": results
        }

        logger.info(f"Collection completed: {summary['total_records']} records in {duration:.1f}s")
        return summary

    async def run(self) -> None:
        """
        데몬 모드 실행 (장 마감 후 자동 수집)

        매일 15:40 KST 이후에 수집을 시작하고,
        다음 날 15:40까지 대기합니다.
        """
        self._is_running = True

        # 초기화
        await self.init_db()
        await self.init_kis_client()
        await self.load_symbols()

        logger.info("InvestorTrendsCollector daemon started")

        while self._is_running:
            try:
                # 장 마감 시간 확인 (15:40 KST)
                await self._wait_for_market_close()

                # 수집 실행
                logger.info("Starting daily investor trends collection...")
                results = await self.collect_all()

                total = sum(results.values())
                logger.info(f"Daily collection completed: {total} records from {len(results)} symbols")

                # 다음 수집까지 대기 (다음 날 15:40)
                await self._sleep_until_next_run()

            except asyncio.CancelledError:
                logger.info("Collector daemon cancelled")
                break
            except Exception as e:
                logger.error(f"Collection error: {e}")
                await asyncio.sleep(300)  # 5분 후 재시도

        # 정리
        if self.kis_client:
            await self.kis_client.disconnect()
        if self.db_pool:
            await self.db_pool.close()

        logger.info("InvestorTrendsCollector daemon stopped")

    async def _wait_for_market_close(self) -> None:
        """장 마감 시간(15:40 KST)까지 대기"""
        import pytz

        tz_kr = pytz.timezone("Asia/Seoul")
        now = datetime.now(tz_kr)

        # 오늘 15:40
        market_close = now.replace(hour=15, minute=40, second=0, microsecond=0)

        if now < market_close:
            wait_seconds = (market_close - now).total_seconds()
            logger.info(f"Waiting {wait_seconds/60:.1f} minutes until market close (15:40 KST)")
            await asyncio.sleep(wait_seconds)

    async def _sleep_until_next_run(self) -> None:
        """다음 수집 시간까지 대기 (다음 날 15:40)"""
        import pytz

        tz_kr = pytz.timezone("Asia/Seoul")
        now = datetime.now(tz_kr)

        # 다음 날 15:40
        next_run = (now + timedelta(days=1)).replace(hour=15, minute=40, second=0, microsecond=0)

        wait_seconds = (next_run - now).total_seconds()
        logger.info(f"Next collection scheduled at {next_run.strftime('%Y-%m-%d %H:%M')} KST")
        await asyncio.sleep(wait_seconds)

    def stop(self) -> None:
        """데몬 중지"""
        self._is_running = False


# CLI Entry Point
async def main():
    """CLI 진입점"""
    import argparse

    parser = argparse.ArgumentParser(description="Investor Trends Collector (Pillar 8)")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--symbol", type=str, help="Collect single symbol only")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    # 로깅 설정
    level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    collector = InvestorTrendsCollector()

    if args.symbol:
        # 단일 종목 수집
        await collector.init_db()
        await collector.init_kis_client()
        collector.symbols = [args.symbol]
        result = await collector.collect_symbol(args.symbol)
        print(f"Collected {result} records for {args.symbol}")

    elif args.once:
        # 1회 실행
        summary = await collector.run_once()
        print(f"\nSummary: {summary['total_records']} records from {summary['symbols_processed']} symbols")

    else:
        # 데몬 모드
        await collector.run()


if __name__ == "__main__":
    asyncio.run(main())
