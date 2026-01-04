FROM python:3.12-slim

WORKDIR /app

# Copy entire project for editable install
COPY . .

# Install package and dependencies
RUN pip install --no-cache-dir -e .

# Default command (override in docker-compose)
CMD ["python", "-m", "src.data_ingestion.ticks.collector"]
