# syntax=docker/dockerfile:1.7
FROM python:3.12-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq5 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# ---- dependencies -----------------------------------------------------------
FROM base AS deps
COPY requirements.txt requirements-dev.txt ./
ARG INSTALL_DEV=1
RUN if [ "$INSTALL_DEV" = "1" ]; then \
        pip install -r requirements-dev.txt; \
    else \
        pip install -r requirements.txt; \
    fi

# ---- runtime ----------------------------------------------------------------
FROM deps AS runtime

# Run as an unprivileged user; the media volume must be writable by it.
RUN groupadd --system --gid 1001 ferasha \
    && useradd --system --uid 1001 --gid ferasha --create-home ferasha

COPY --chown=ferasha:ferasha . .

RUN mkdir -p /app/media /app/staticfiles \
    && chown -R ferasha:ferasha /app/media /app/staticfiles

USER ferasha

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health/')" || exit 1

CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--threads", "2", \
     "--timeout", "60", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
