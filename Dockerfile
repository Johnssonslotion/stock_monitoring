FROM python:3.12-slim

WORKDIR /app

# Copy dependency files and README
COPY pyproject.toml README.md ./

# Install dependencies using pip (pyproject.toml uses PEP 621 format)
RUN pip install --no-cache-dir -e .

# Copy application code
COPY . .

# Default command (override in docker-compose)
CMD ["python", "-m", "src.data_ingestion.ticks.collector"]
