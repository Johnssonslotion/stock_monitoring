import os
import json
import logging
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
import aiofiles

logger = logging.getLogger("RawLogger")

class RawWebSocketLogger:
    """
    WebSocket 원본 메시지 저장 로거
    - JSONL 포맷 저장
    - 1시간 단위 파일 로테이션
    - 24시간 보존 정책 (1일치)
    """
    
    def __init__(self, log_dir: str = "data/raw", retention_hours: int = 24):
        self.log_dir = Path(log_dir)
        self.retention_hours = retention_hours
        self.current_file_path = None
        self.current_hour = None
        self.file_handle = None
        self.queue = asyncio.Queue()
        self.logger_task = None
        
        # 디렉토리 생성
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
    async def start(self):
        """비동기 로깅 태스크 시작"""
        self.logger_task = asyncio.create_task(self._process_queue())
        asyncio.create_task(self._cleanup_old_logs())
        logger.info(f"💾 Raw Logger Started (Dir: {self.log_dir}, Retention: {self.retention_hours}h)")

    async def log(self, message: str, direction: str = "RX"):
        """로그 큐에 추가 (Non-blocking)"""
        try:
            timestamp = datetime.now().isoformat()
            entry = {
                "ts": timestamp,
                "dir": direction,  # RX=수신, TX=송신
                "msg": message
            }
            self.queue.put_nowait(entry)
        except Exception as e:
            logger.error(f"Failed to queue log: {e}")

    async def _process_queue(self):
        """큐에서 꺼내서 파일에 쓰기"""
        while True:
            try:
                entry = await self.queue.get()
                await self._write_to_file(entry)
                self.queue.task_done()
            except Exception as e:
                logger.error(f"Log processing error: {e}")
                await asyncio.sleep(1)

    async def _write_to_file(self, entry: dict):
        """파일 저장 및 로테이션 처리"""
        now = datetime.fromisoformat(entry["ts"])
        hour_key = now.strftime("%Y%m%d_%H")
        
        # 시간 변경 또는 파일 안 열림 -> 파일 로테이션
        if self.current_hour != hour_key or self.file_handle is None:
            await self._rotate_file(hour_key)
            
        if self.file_handle:
            await self.file_handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
            await self.file_handle.flush()

    async def _rotate_file(self, hour_key: str):
        """파일 교체"""
        if self.file_handle:
            await self.file_handle.close()
            
        filename = f"ws_raw_{hour_key}.jsonl"
        self.current_file_path = self.log_dir / filename
        self.current_hour = hour_key
        
        self.file_handle = await aiofiles.open(self.current_file_path, mode='a', encoding='utf-8')
        logger.info(f"📄 Rotated log file to: {filename}")

    async def _cleanup_old_logs(self):
        """오래된 로그 삭제 (매시간 실행)"""
        while True:
            try:
                cutoff = datetime.now() - timedelta(hours=self.retention_hours)
                min_retention = datetime.now() - timedelta(hours=48)  # 최소 2일 보존
                cnt = 0
                protected = 0
                
                for file_path in self.log_dir.glob("ws_raw_*.jsonl"):
                    # 파일명에서 시간 추출: ws_raw_20260109_17.jsonl
                    try:
                        name_part = file_path.stem.replace("ws_raw_", "")
                        file_time = datetime.strptime(name_part, "%Y%m%d_%H")
                        
                        # 최소 2일치는 절대 삭제 금지
                        if file_time < min_retention:
                            if file_time < cutoff:
                                file_path.unlink()
                                cnt += 1
                            else:
                                # retention 범위 내이지만 아직 살아있음
                                pass
                        else:
                            # 2일 이내 - 보호됨
                            protected += 1
                            
                    except ValueError:
                        continue # 날짜 형식이 아니면 무시
                
                if cnt > 0:
                    logger.info(f"🧹 Cleaned up {cnt} old log files (Protected: {protected} files within 48h)")
                    
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
                
            await asyncio.sleep(3600)  # 1시간 대기
