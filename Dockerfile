
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY mcp-servers/ ./mcp-servers/
COPY tests/ ./tests/
COPY scripts/ ./scripts/

EXPOSE 8000 8003 8004 8005 8006

CMD ["uvicorn", "backend.gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]
