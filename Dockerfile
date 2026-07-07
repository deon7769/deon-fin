FROM node:24-slim AS web

WORKDIR /web

COPY web/package*.json ./
RUN npm ci

COPY web/ ./
ARG NEXT_PUBLIC_AUTH_ENABLED=false
ENV NEXT_TELEMETRY_DISABLED=1
ENV NEXT_PUBLIC_API_URL=/api
ENV NEXT_PUBLIC_AUTH_ENABLED=$NEXT_PUBLIC_AUTH_ENABLED
RUN npm run build


FROM python:3.12-slim-bookworm

WORKDIR /app
ARG APP_UID=1000
ARG APP_GID=1000

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN groupadd --gid "$APP_GID" app \
    && useradd --uid "$APP_UID" --gid "$APP_GID" --create-home --shell /usr/sbin/nologin app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini ./alembic.ini
COPY src ./src
COPY scripts ./scripts
COPY --from=web /web/out ./web_dist

RUN mkdir -p /app/data \
    && chown -R app:app /app

EXPOSE 8000

USER app

CMD ["python", "-m", "src.cli", "serve", "--host", "0.0.0.0", "--port", "8000"]
