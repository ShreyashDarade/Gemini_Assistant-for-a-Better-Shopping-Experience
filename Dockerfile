# syntax=docker/dockerfile:1
FROM python:3.13-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev --no-install-project

FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PATH="/app/.venv/bin:$PATH"
RUN useradd --system --uid 10001 --create-home app && mkdir /data && chown app /data
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY app ./app
COPY gunicorn.conf.py ./
ENV DATABASE_URL=sqlite+aiosqlite:////data/shopping_assistant.db
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(urllib.request.urlopen('http://localhost:8000/live').status != 200)"
CMD ["gunicorn", "app.main:app", "-c", "gunicorn.conf.py"]
