FROM node:24-slim AS web

WORKDIR /web

COPY web/package*.json ./
RUN npm ci

COPY web/ ./
ENV NEXT_TELEMETRY_DISABLED=1
ENV NEXT_PUBLIC_API_URL=/api
RUN npm run build


FROM python:3.12-slim-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY scripts ./scripts
COPY --from=web /web/out ./web_dist

RUN mkdir -p /app/data

EXPOSE 8000

CMD ["python", "-m", "src.cli", "serve", "--host", "0.0.0.0", "--port", "8000"]
