FROM python:3.12-slim

WORKDIR /app

ENV PYTHONPATH=/app
ENV UV_LINK_MODE=copy

RUN pip install --no-cache-dir uv

COPY services/api /app
COPY packages /app/packages

EXPOSE 8000

# Exclude .venv from --reload: uv sync writes site-packages under the bind-mounted
# /app and would otherwise restart the API mid-request (UI sees "socket hang up").
CMD ["sh", "-c", "uv sync --frozen --no-dev && uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload --reload-exclude '.venv' --reload-exclude '**/.venv/**' --reload-exclude '**/site-packages/**'"]
