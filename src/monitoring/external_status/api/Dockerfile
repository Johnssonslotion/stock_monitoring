FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir fastapi uvicorn asyncpg

COPY main.py .

EXPOSE 8080

CMD ["uvicorn", "main.py", "--host", "0.0.0.0", "--port", "8080"]
