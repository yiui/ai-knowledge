#!/usr/bin/env bash
# 服务器首次初始化：安装 Docker、克隆仓库、准备 backend/.env
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

DEPLOY_PATH="${DEPLOY_PATH:-${REPO_ROOT}}"
DEPLOY_USER="${DEPLOY_USER:-$(whoami)}"
REPO_URL="${REPO_URL:-}"
DEPLOY_BRANCH="${DEPLOY_BRANCH:-main}"

log() { echo "[bootstrap] $*"; }

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root: sudo bash deploy/bootstrap.sh" >&2
  exit 1
fi

if command -v apt-get >/dev/null 2>&1; then
  apt-get update -qq
  apt-get install -y -qq git curl ca-certificates
  if ! command -v docker >/dev/null 2>&1; then
    curl -fsSL https://get.docker.com | sh
  fi
  apt-get install -y -qq docker-compose-plugin 2>/dev/null || true
  systemctl enable --now docker
  usermod -aG docker "${DEPLOY_USER}" || true
elif command -v yum >/dev/null 2>&1 || command -v dnf >/dev/null 2>&1; then
  (command -v dnf >/dev/null && dnf install -y git curl docker docker-compose-plugin) \
    || yum install -y git curl docker docker-compose-plugin
  systemctl enable --now docker
  usermod -aG docker "${DEPLOY_USER}" || true
else
  log "Install Docker Engine + Compose plugin manually: https://docs.docker.com/engine/install/"
fi

if [[ -n "${REPO_URL}" && ! -d "${DEPLOY_PATH}/.git" ]]; then
  mkdir -p "$(dirname "${DEPLOY_PATH}")"
  sudo -u "${DEPLOY_USER}" git clone -b "${DEPLOY_BRANCH}" "${REPO_URL}" "${DEPLOY_PATH}"
fi

if [[ ! -f "${DEPLOY_PATH}/backend/.env" ]]; then
  cp "${DEPLOY_PATH}/backend/.env.example" "${DEPLOY_PATH}/backend/.env"
  log "Created backend/.env — edit POSTGRES_PASSWORD, MINIO_*, JWT, LLM keys"
fi

log "Bootstrap done."
echo "  1. Edit ${DEPLOY_PATH}/backend/.env"
echo "  2. Add server deploy key to GitHub"
echo "  3. bash ${DEPLOY_PATH}/deploy/deploy.sh"
