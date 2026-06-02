#!/usr/bin/env bash
# 服务器首次初始化（仅需执行一次）。需要 sudo。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

DEPLOY_PATH="${DEPLOY_PATH:-${REPO_ROOT}}"
DEPLOY_USER="${DEPLOY_USER:-$(whoami)}"
REPO_URL="${REPO_URL:-}"
DEPLOY_BRANCH="${DEPLOY_BRANCH:-main}"
DOMAIN="${DOMAIN:-_}"

log() { echo "[bootstrap] $*"; }

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root: sudo bash deploy/bootstrap.sh" >&2
  exit 1
fi

log "Install packages (git, docker, nginx, python3, node via distro or nvm)"
if command -v apt-get >/dev/null 2>&1; then
  apt-get update -qq
  apt-get install -y -qq git curl nginx python3 python3-venv python3-pip docker.io docker-compose-plugin
  if ! command -v node >/dev/null 2>&1; then
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
    apt-get install -y -qq nodejs
  fi
  systemctl enable --now docker nginx
  usermod -aG docker "${DEPLOY_USER}" || true
elif command -v yum >/dev/null 2>&1; then
  yum install -y git curl nginx python3 docker docker-compose-plugin
  systemctl enable --now docker nginx
  usermod -aG docker "${DEPLOY_USER}" || true
  log "Install Node.js 20+ manually if npm is missing (https://nodejs.org)"
else
  log "Unsupported distro; install git, docker, nginx, python3.12+, node 20+ manually"
fi

if [[ -n "${REPO_URL}" && ! -d "${DEPLOY_PATH}/.git" ]]; then
  log "Clone ${REPO_URL} -> ${DEPLOY_PATH}"
  mkdir -p "$(dirname "${DEPLOY_PATH}")"
  sudo -u "${DEPLOY_USER}" git clone -b "${DEPLOY_BRANCH}" "${REPO_URL}" "${DEPLOY_PATH}"
fi

if [[ ! -f "${DEPLOY_PATH}/backend/.env" ]]; then
  log "Create backend/.env from example — edit secrets before going live"
  cp "${DEPLOY_PATH}/backend/.env.example" "${DEPLOY_PATH}/backend/.env"
fi

if [[ ! -f "${DEPLOY_PATH}/frontend/.env" ]]; then
  cp "${DEPLOY_PATH}/deploy/frontend.env.production.example" "${DEPLOY_PATH}/frontend/.env"
fi

log "Install systemd unit"
sed "s|@DEPLOY_PATH@|${DEPLOY_PATH}|g; s|@DEPLOY_USER@|${DEPLOY_USER}|g" \
  "${DEPLOY_PATH}/deploy/ai-knowledge-backend.service" \
  >/etc/systemd/system/ai-knowledge-backend.service
systemctl daemon-reload
systemctl enable ai-knowledge-backend

if [[ "${DOMAIN}" != "_" ]]; then
  log "Install nginx site for ${DOMAIN}"
  sed "s|@DEPLOY_PATH@|${DEPLOY_PATH}|g; s|@DOMAIN@|${DOMAIN}|g" \
    "${DEPLOY_PATH}/deploy/nginx-site.conf" \
    >/etc/nginx/sites-available/ai-knowledge
  ln -sf /etc/nginx/sites-available/ai-knowledge /etc/nginx/sites-enabled/ai-knowledge
  rm -f /etc/nginx/sites-enabled/default
  nginx -t
  systemctl reload nginx
fi

log "Bootstrap done. Next:"
echo "  1. Edit ${DEPLOY_PATH}/backend/.env (DB/MinIO/JWT/LLM keys)"
echo "  2. Add server deploy key to GitHub repo (read access)"
echo "  3. Configure GitHub Actions secrets (see docs/DEPLOY.md)"
echo "  4. Run: sudo -u ${DEPLOY_USER} bash ${DEPLOY_PATH}/deploy/deploy.sh"
