FROM python:3.12-slim

WORKDIR /app

# Install dependencies directly (avoid complex pyproject.toml build)
RUN pip install --no-cache-dir \
    pandas==2.3.3 \
    numpy==2.4.0 \
    ccxt==4.5.30 \
    redis==7.1.0 \
    duckdb==1.4.3 \
    pydantic==2.12.5 \
    pyyaml==6.0.3 \
    python-dotenv==1.2.1 \
    feedparser==6.0.12 \
    aiohttp \
    streamlit==1.41.1 \
    plotly==5.24.1 \
    watchdog==6.0.0 \
    fastapi==0.109.2 \
    uvicorn==0.27.1 \
    websockets==12.0 \
    asyncpg==0.29.0 \
    yfinance==0.2.36 \
    finance-datareader==0.9.60 \
    aiofiles

# Copy application code
COPY . .

# Set Python path to include src directory
ENV PYTHONPATH="/app:${PYTHONPATH}"

# Default command (override in docker-compose)
CMD ["python", "-m", "src.data_ingestion.ticks.collector"]
