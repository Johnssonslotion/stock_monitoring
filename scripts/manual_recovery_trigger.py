import asyncio
import os
import sys

# Ensure project root is in path
sys.path.append(os.getcwd())

from src.verification.worker import VerificationProducer

async def main():
    producer = VerificationProducer()
    print("🚀 Triggering manual daily verification tasks for today...")
    count = await producer.produce_daily_tasks()
    print(f"✅ Successfully produced {count} tasks. Check verification-worker logs for processing.")
    await producer.close()

if __name__ == "__main__":
    asyncio.run(main())
