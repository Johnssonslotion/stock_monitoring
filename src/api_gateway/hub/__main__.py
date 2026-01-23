"""
API Gateway Hub Worker - Main Entry Point

`python -m src.api_gateway.hub` 실행 시 진입점
"""
import asyncio
from .worker import main

if __name__ == "__main__":
    asyncio.run(main())
