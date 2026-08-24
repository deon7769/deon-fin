#!/usr/bin/env bash
# Idempotent Cloud Agent bootstrap for Deon Fin.
# Prepares Python + Node dependencies, local env files, and the static
# Next.js build that the FastAPI backend serves same-origin at /.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> Installing Python dependencies"
python3 -m pip install --user --upgrade pip
python3 -m pip install --user -r requirements.txt

echo "==> Ensuring local env files exist (local-first defaults)"
# .env.example ships non-empty placeholder Pluggy credentials, which are all
# the app needs to boot in local-first (SQLite) mode. Real Pluggy credentials
# are only required for live Open Finance sync and can be supplied later.
[ -f .env ] || cp .env.example .env
[ -f web/.env.local ] || cp web/.env.example web/.env.local

echo "==> Installing frontend dependencies"
cd web
npm ci

echo "==> Building Next.js static export (same-origin /api)"
NEXT_TELEMETRY_DISABLED=1 \
NEXT_PUBLIC_API_URL=/api \
NEXT_PUBLIC_AUTH_ENABLED=false \
  npm run build
cd "$ROOT"

echo "==> Publishing static build to web_dist/"
rm -rf web_dist
cp -r web/out web_dist

echo "==> Install complete"
