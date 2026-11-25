FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./

RUN uv sync --frozen --no-dev

COPY src/ ./src/

EXPOSE 8000

CMD ["uv", "run", "--no-sync", "uvicorn", "src.adapters.inbound.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
