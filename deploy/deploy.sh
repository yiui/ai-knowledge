#!/usr/bin/env bash
# 服务器部署：拉代码 + docker compose 构建并启动全部服务
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

DEPLOY_BRANCH="${DEPLOY_BRANCH:-main}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yaml}"

log() { echo "[deploy] $*"; }

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "ERROR: ${REPO_ROOT} is not a git repository." >&2
  exit 1
fi

if [[ ! -f backend/.env ]]; then
  echo "ERROR: backend/.env missing. Copy backend/.env.example and configure." >&2
  exit 1
fi

log "Pull origin/${DEPLOY_BRANCH}"
git fetch origin "${DEPLOY_BRANCH}"
git reset --hard "origin/${DEPLOY_BRANCH}"

log "Docker compose up --build"
docker compose --env-file backend/.env -f "${COMPOSE_FILE}" up -d --build --remove-orphans

log "Prune dangling images (optional)"
docker image prune -f >/dev/null 2>&1 || true

# 取消健康监测
# HTTP_PORT="${HTTP_PORT:-8000}"
# if curl -sf "http://127.0.0.1:${HTTP_PORT}/health" >/dev/null 2>&1; then
#   log "Health check OK (http://127.0.0.1:${HTTP_PORT}/health)"
# else
#   log "WARN: health check failed; inspect: docker compose -f ${COMPOSE_FILE} logs -f backend frontend"
# fi

log "Deploy finished"
