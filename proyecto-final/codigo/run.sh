#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
RAIZ_DEL_REPO="$(cd ../.. && pwd)"

if [ ! -f "$RAIZ_DEL_REPO/.env" ]; then
  echo "Falta el .env en la raíz del repo. Desde la raíz: cp .env.example .env  y completá las keys."
  exit 1
fi
command -v uv >/dev/null || { echo "Falta uv: https://docs.astral.sh/uv/getting-started/installation/"; exit 1; }

if command -v docker >/dev/null; then
  docker compose up -d --wait redis
elif command -v redis-cli >/dev/null && redis-cli ping >/dev/null 2>&1; then
  echo "Redis ya está corriendo."
elif command -v brew >/dev/null; then
  brew list redis >/dev/null 2>&1 || brew install redis
  brew services start redis
  sleep 2
else
  echo "Necesitás Docker o Redis 8+ corriendo en localhost:6379."
  exit 1
fi

uv sync
uv run python -m app.rag.ingesta
echo "API en http://localhost:8000/docs"
uv run uvicorn app.api.principal:aplicacion --port 8000
