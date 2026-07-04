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

log "Fetching origin/${DEPLOY_BRANCH} (force sync latest commit)"
git fetch origin "${DEPLOY_BRANCH}" --prune --force
git reset --hard FETCH_HEAD
git clean -fd

log "DEPLOY COMMIT: $(git rev-parse HEAD)"

log "Docker compose up --build"
docker compose --env-file backend/.env -f "${COMPOSE_FILE}" up -d --build --remove-orphans

log "Container status:"
docker compose -f "${COMPOSE_FILE}" ps

log "Prune dangling images (optional)"
docker image prune -f >/dev/null 2>&1 || true

log "Deploy finished successfully"