#!/bin/sh
# Ponto de entrada do container.
# SEED_DEMO=true popula o banco com as páginas de demonstração antes de subir
# (o seed é idempotente). PORT é definido por plataformas como o Render.
set -e

if [ "${SEED_DEMO:-false}" = "true" ]; then
    python -m scripts.seed_demo
fi

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers --forwarded-allow-ips="*"
