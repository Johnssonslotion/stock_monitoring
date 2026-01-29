import asyncio
import os
import sys
from datetime import datetime

# Ensure project root is in path
sys.path.append(os.getcwd())

from src.verification.worker import VerificationProducer, VerificationTask, VerificationConfig

async def trigger_weekly_verification():
    producer = VerificationProducer()
    await producer.connect()
    
    symbols = await producer.get_target_symbols()
    dates = ["20260126", "20260127", "20260128", "20260129"]
    
    total_count = 0
    print(f"🚀 Starting weekly verification trigger for {len(dates)} days...")
    
    for date in dates:
        count = 0
        for symbol in symbols:
            task = VerificationTask(
                task_type="verify_db_integrity",
                symbol=symbol,
                date=date
            )
            await producer.redis.lpush(VerificationConfig.QUEUE_KEY, task.to_json())
            count += 1
        print(f"✅ Produced {count} tasks for {date}")
        total_count += count
        
    print(f"🏁 Done! Total {total_count} tasks queued in {VerificationConfig.QUEUE_KEY}")
    await producer.close()

if __name__ == "__main__":
    asyncio.run(trigger_weekly_verification())
