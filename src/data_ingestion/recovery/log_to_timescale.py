import os
import json
import logging
import asyncio
import asyncpg
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger("LogToTimescale")
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

class LogToTimescaleIngester:
    """
    Ingest raw JSONL logs (KIS/Kiwoom) into TimescaleDB market_ticks.
    """
    def __init__(self, db_url: str = None, target_table: str = "market_ticks"):
        self.db_url = db_url or os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/stockval")
        self.target_table = target_table

    async def ingest_file(self, file_path: str, provider: str = "KIWOOM"):
        """Ingest a single log file"""
        logger.info(f"🚚 Ingesting {file_path} (Provider: {provider})")
        
        ticks = []
        batch_size = 5000
        total_count = 0
        
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    if provider == "KIWOOM":
                        parsed = self._parse_kiwoom_line(data)
                    else:
                        parsed = self._parse_kis_line(data)
                    
                    if parsed:
                        ticks.extend(parsed)
                        
                    if len(ticks) >= batch_size:
                        await self._bulk_insert(ticks)
                        total_count += len(ticks)
                        ticks = []
                        
                except Exception as e:
                    logger.error(f"Error parsing line: {e}")
                    continue
        
        if ticks:
            await self._bulk_insert(ticks)
            total_count += len(ticks)
            
        logger.info(f"✅ Ingested {total_count} ticks from {file_path}")

    def _parse_kiwoom_line(self, data: Dict) -> List[Dict]:
        """Parse Kiwoom 0B type ticks"""
        results = []
        msgs = []
        
        # Kiwoom logs usually have "msg" which is a JSON string
        if "msg" in data:
            try:
                msg_content = data["msg"]
                if isinstance(msg_content, str):
                    try:
                        inner = json.loads(msg_content)
                    except:
                        return []
                else:
                    inner = msg_content

                if isinstance(inner, dict):
                    if "data" in inner: msgs = inner["data"]
                    else: msgs = [inner]
                elif isinstance(inner, list):
                    msgs = inner
            except Exception:
                return []
        else:
            msgs = [data]

        for m in msgs:
            if m.get("type") == "0B": # 주식체결
                vals = m.get("values", {})
                symbol = m.get("item")
                # Field 20: 체결시간 (HHMMSS)
                time_str = vals.get("20")
                if not (symbol and time_str): continue
                
                date_part = "2026-01-20" 
                try:
                    # Some time strings might have leading/trailing spaces
                    time_str = time_str.strip()
                    ts = datetime.strptime(f"{date_part} {time_str}", "%Y-%m-%d %H%M%S")
                    results.append({
                        "time": ts,
                        "symbol": symbol,
                        "price": abs(float(vals["10"])),
                        "volume": abs(float(vals["15"])),
                        "source": "KIWOOM",
                        "execution_no": vals.get("13") # 체결번호
                    })
                except: continue
        return results

    def _parse_kis_line(self, data: Dict) -> List[Dict]:
        """Parse KIS H0STCNT0 type ticks"""
        results = []
        msg = data.get("msg", "")
        if not isinstance(msg, str) or "|" not in msg: return []
        
        parts = msg.split("|")
        if len(parts) < 4: return []
        
        tr_id = parts[1]
        if tr_id not in ["H0STCNT0", "H1STCNT0"]: return []
        
        payload = parts[3]
        ticks_raw = payload.split("^")
        try:
            symbol = ticks_raw[0]
            time_str = ticks_raw[1] # HHMMSS
            price = abs(float(ticks_raw[2]))
            vol = float(ticks_raw[12])
            
            date_part = "2026-01-20"
            ts = datetime.strptime(f"{date_part} {time_str}", "%Y-%m-%d %H%M%S")
            
            results.append({
                "time": ts,
                "symbol": symbol,
                "price": price,
                "volume": vol,
                "source": "KIS",
                "execution_no": None # KIS H0STCNT0 lacks unique execution ID
            })
        except: pass
            
        return results

    async def _bulk_insert(self, ticks: List[Dict]):
        if not ticks: return
        conn = await asyncpg.connect(self.db_url)
        try:
            columns = ['time', 'symbol', 'price', 'volume', 'source', 'execution_no']
            records = [tuple(t.get(col) for col in columns) for t in ticks]
            
            async with conn.transaction():
                # Create temp table without indices
                await conn.execute(f"CREATE TEMPORARY TABLE temp_ticks (LIKE {self.target_table}) ON COMMIT DROP")
                # Copy to temp table
                await conn.copy_records_to_table('temp_ticks', records=records, columns=columns)
                # Insert to main table with de-duplication
                # ON CONFLICT DO NOTHING relies on the unique indices on common columns
                await conn.execute(f"""
                    INSERT INTO {self.target_table} ({', '.join(columns)})
                    SELECT {', '.join(columns)} FROM temp_ticks
                    ON CONFLICT DO NOTHING
                """)
        except Exception as e:
            logger.error(f"Bulk insert to {self.target_table} failed: {e}")
        finally:
            await conn.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    parser.add_argument("--provider", default="KIWOOM")
    parser.add_argument("--table", default="market_ticks")
    args = parser.parse_args()
    
    ingester = LogToTimescaleIngester(target_table=args.table)
    asyncio.run(ingester.ingest_file(args.file, args.provider))
