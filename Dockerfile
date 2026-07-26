FROM python:3.12.11-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    CHAFFMEM_ARTIFACT_DIR=/app/artifacts/runs

WORKDIR /app

RUN addgroup --system chaffmem \
    && adduser --system --ingroup chaffmem --home /nonexistent chaffmem \
    && mkdir -p /app/artifacts/runs \
    && chown -R chaffmem:chaffmem /app/artifacts

COPY pyproject.toml README.md requirements.lock ./
COPY src ./src
COPY configs ./configs
COPY data ./data

RUN python -m pip install --requirement requirements.lock \
    && python -m pip install --no-deps .

USER chaffmem

EXPOSE 8000

CMD ["chaffmem", "serve", "--host", "0.0.0.0", "--port", "8000"]
