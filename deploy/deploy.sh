#!/usr/bin/env bash
# 在服务器上执行：拉取代码、更新依赖、构建前端、重启服务。
# GitHub Actions 通过 SSH 调用此脚本完成发布。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

DEPLOY_BRANCH="${DEPLOY_BRANCH:-main}"
# 生产建议: export COMPOSE_FILE=docker-compose.prod.yaml
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yaml}"
BACKEND_SERVICE="${BACKEND_SERVICE:-ai-knowledge-backend}"

log() { echo "[deploy] $*"; }

log "Repository: ${REPO_ROOT}"
log "Branch: ${DEPLOY_BRANCH}"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "ERROR: ${REPO_ROOT} is not a git repository. Run deploy/bootstrap.sh first." >&2
  exit 1
fi

log "Pull latest from origin/${DEPLOY_BRANCH}"
git fetch origin "${DEPLOY_BRANCH}"
git reset --hard "origin/${DEPLOY_BRANCH}"

if [[ ! -f backend/.env ]]; then
  echo "ERROR: backend/.env missing. Copy backend/.env.example and configure secrets." >&2
  exit 1
fi

log "Start infrastructure (Postgres, MinIO)"
set -a
# shellcheck disable=SC1091
source "${REPO_ROOT}/backend/.env"
set +a
export MINIO_ROOT_USER="${MINIO_ACCESS_KEY:-admin}"
export MINIO_ROOT_PASSWORD="${MINIO_SECRET_KEY:?MINIO_SECRET_KEY required in backend/.env}"
docker compose -f "${COMPOSE_FILE}" up -d

log "Install / update backend"
cd "${REPO_ROOT}/backend"
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install -q -U pip
python -m pip install -q -e .
deactivate
cd "${REPO_ROOT}"

log "Build frontend"
cd "${REPO_ROOT}/frontend"
if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi
if command -v npm >/dev/null 2>&1; then
  npm ci
  npm run build
else
  echo "ERROR: npm not found. Install Node.js 20+ on the server." >&2
  exit 1
fi
cd "${REPO_ROOT}"

restart_backend() {
  if systemctl is-active --quiet "${BACKEND_SERVICE}" 2>/dev/null; then
    sudo systemctl restart "${BACKEND_SERVICE}"
    return
  fi
  if systemctl --user is-active --quiet "${BACKEND_SERVICE}" 2>/dev/null; then
    systemctl --user restart "${BACKEND_SERVICE}"
    return
  fi
  log "WARN: systemd unit ${BACKEND_SERVICE} not found or not active; skip restart"
  log "      Run deploy/bootstrap.sh or install deploy/ai-knowledge-backend.service"
}

reload_nginx() {
  if command -v nginx >/dev/null 2>&1 && sudo nginx -t >/dev/null 2>&1; then
    sudo systemctl reload nginx
    log "Nginx reloaded"
  else
    log "WARN: nginx not configured; serve frontend/dist manually if needed"
  fi
}

log "Restart application"
restart_backend
reload_nginx

if curl -sf "http://127.0.0.1:8000/health" >/dev/null 2>&1; then
  log "Backend health check OK"
else
  log "WARN: backend /health not reachable on 127.0.0.1:8000 (service may still be starting)"
fi

log "Deploy finished"
