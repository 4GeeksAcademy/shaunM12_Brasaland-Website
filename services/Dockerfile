FROM python:3.12-slim

WORKDIR /app

ENV PYTHONPATH=/app
ENV UV_LINK_MODE=copy

RUN pip install --no-cache-dir uv

COPY services/api /app
COPY packages /app/packages

EXPOSE 8000

CMD ["sh", "-c", "uv sync --frozen --no-dev && uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload"]
