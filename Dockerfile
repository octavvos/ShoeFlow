FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

COPY --from=ghcr.io/astral-sh/uv:0.8.0 /uv /usr/local/bin/uv

WORKDIR /app

# prod uchun "--no-dev", dev uchun bo'sh qoldiriladi (docker-compose.yml'ga qarang)
ARG UV_SYNC_ARGS="--no-dev"
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project $UV_SYNC_ARGS

COPY . .

# staticfiles va media — docker volume'lar; papkalar oldindan yaratilsa, volume shu egasini oladi
RUN useradd --create-home --uid 1000 app \
    && mkdir -p /app/staticfiles /app/media \
    && chown -R app:app /app
USER app

EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
