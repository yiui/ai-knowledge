# 部署指南 · Deployment Guide

本项目提供完整的生产环境部署方案，包含 Docker Compose 一键部署、Nginx 反向代理和 systemd 服务管理。

---

## 📁 文件说明

| 文件 | 用途 | 适用场景 |
|------|------|----------|
| `deploy.sh` | 生产部署入口脚本 | **日常更新部署**：拉取最新代码 → 重新构建镜像 → 启动服务 |
| `bootstrap.sh` | 服务器首次初始化脚本 | **全新服务器**：安装 Docker + Git → 克隆仓库 → 创建 `.env` 模板 |
| `nginx-site.conf` | Nginx 站点配置模板 | 需要宿主机 Nginx 反向代理（替代直接暴露容器端口） |
| `ai-knowledge-backend.service` | systemd 服务单元模板 | 非 Docker 部署时用于管理后端进程 |
| `frontend.env.production.example` | 前端生产环境变量示例 | 参考用，Docker Compose 部署时通过 build args 传入 |

---

## 🚀 快速部署（全新服务器）

### 步骤 1：首次初始化

在目标服务器上以 **root** 执行：

```bash
# 克隆仓库后执行（或直接通过 curl 远程执行）
sudo bash deploy/bootstrap.sh
```

脚本会自动完成：
- 安装 Docker Engine + Docker Compose Plugin
- 安装 Git、curl 等基础工具
- 将当前用户加入 `docker` 组
- 如果指定了 `REPO_URL`，自动克隆仓库
- 从 `.env.example` 创建 `backend/.env` 模板

**支持的环境变量**：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DEPLOY_PATH` | 脚本所在仓库根目录 | 项目部署路径 |
| `DEPLOY_USER` | 当前用户 | Docker 组的用户 |
| `REPO_URL` | 空（跳过克隆） | Git 仓库地址 |
| `DEPLOY_BRANCH` | `main` | 要克隆的分支 |

带自动克隆的示例：

```bash
REPO_URL=git@github.com:your-org/ai-knowledge.git DEPLOY_BRANCH=main sudo -E bash deploy/bootstrap.sh
```

### 步骤 2：配置环境变量

```bash
vim backend/.env
```

必须配置的项目：

```env
# LLM（至少配置一个）
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-xxxxxxxx

# Embedding
EMBEDDING_PROVIDER=openai_compat
EMBEDDING_API_KEY=your-key
EMBEDDING_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
EMBEDDING_MODEL=text-embedding-v4

# 数据库密码
POSTGRES_PASSWORD=<生成强密码>

# MinIO 凭证
MINIO_ACCESS_KEY=<生成强密码>
MINIO_SECRET_KEY=<生成强密码>

# JWT 密钥
JWT_SECRET=<生成随机长字符串>
```

> 生成随机密钥：`openssl rand -hex 32`

### 步骤 3：启动服务

```bash
bash deploy/deploy.sh
```

或手动执行：

```bash
docker compose --env-file backend/.env -f docker-compose.prod.yaml up -d --build
```

### 步骤 4：验证部署

```bash
# 检查所有容器运行状态
docker compose -f docker-compose.prod.yaml ps

# 健康检查
curl http://localhost:8000/health

# 查看配置
curl http://localhost:8000/config | jq
```

服务端口：

| 服务 | 端口 | 说明 |
|------|------|------|
| 前端 (Nginx) | `${HTTP_PORT:-8080}` | 用户访问入口 |
| 后端 (FastAPI) | `8000` | API 服务 |
| PostgreSQL | `5432` | 数据库 |
| MinIO API | `9000` | 对象存储 |
| MinIO Console | `9001` | MinIO Web 管理界面 |

---

## 🔄 日常更新

代码更新后，在项目根目录执行：

```bash
bash deploy/deploy.sh
```

脚本执行流程：

1. 校验 git 仓库和 `backend/.env` 是否存在
2. `git fetch origin main` + `git reset --hard origin/main`
3. `docker compose up -d --build --remove-orphans`（自动重建有变更的镜像）
4. 清理悬空镜像 (`docker image prune -f`)

**自定义参数**：

```bash
# 指定分支
DEPLOY_BRANCH=develop bash deploy/deploy.sh

# 指定 compose 文件
COMPOSE_FILE=docker-compose.staging.yaml bash deploy/deploy.sh
```

---

## 🌐 Nginx 反向代理（可选）

当需要域名访问、SSL 终止或与其他站点共用 80/443 端口时，使用宿主机 Nginx 替代直接暴露容器端口。

### 配置步骤

1. 复制配置模板：

```bash
sudo cp deploy/nginx-site.conf /etc/nginx/sites-available/ai-knowledge
```

2. 替换占位符：

```bash
sudo sed -i 's|@DOMAIN@|kb.your-domain.com|g' /etc/nginx/sites-available/ai-knowledge
sudo sed -i 's|@DEPLOY_PATH@|/opt/ai-knowledge|g' /etc/nginx/sites-available/ai-knowledge
```

3. 启用站点：

```bash
sudo ln -s /etc/nginx/sites-available/ai-knowledge /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

4. 配置 SSL（推荐使用 Certbot）：

```bash
sudo certbot --nginx -d kb.your-domain.com
```

> **注意**：使用 Nginx 反向代理时，前端 `VITE_API_BASE_URL` 应设为空字符串（同域代理），且 Docker Compose 的前端端口可以不映射到宿主机。

---

## 🔧 运维操作

### 服务管理

```bash
# 查看所有容器状态
docker compose -f docker-compose.prod.yaml ps

# 查看后端日志（实时跟踪）
docker compose -f docker-compose.prod.yaml logs -f backend

# 查看前端日志
docker compose -f docker-compose.prod.yaml logs -f frontend

# 重启单个服务
docker compose -f docker-compose.prod.yaml restart backend

# 无缓存重建（强制重新构建镜像层）
docker compose -f docker-compose.prod.yaml build --no-cache backend
docker compose -f docker-compose.prod.yaml up -d backend
```

### 数据备份

```bash
# PostgreSQL 备份
docker exec ai-postgres pg_dump -U postgres ai_kb > backup_$(date +%Y%m%d).sql

# MinIO 数据备份（直接备份数据卷）
docker run --rm -v ai-knowledge_minio_data:/data -v $(pwd):/backup alpine tar czf /backup/minio_backup_$(date +%Y%m%d).tar.gz -C /data .
```

### 故障排查

```bash
# 进入容器排查
docker exec -it ai-backend bash
docker exec -it ai-postgres psql -U postgres -d ai_kb

# 检查容器资源占用
docker stats ai-backend ai-postgres ai-minio ai-frontend

# 查看 MinIO 是否正常
curl http://localhost:9000/health
```

### 完整清理

```bash
# 停止并删除所有容器、网络（保留数据卷）
docker compose -f docker-compose.prod.yaml down

# 停止并删除所有容器、网络、数据卷（⚠️ 数据不可恢复）
docker compose -f docker-compose.prod.yaml down -v
```

---

## 📋 环境变量速查

部署相关环境变量：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DEPLOY_BRANCH` | `main` | `deploy.sh` 拉取的分支 |
| `COMPOSE_FILE` | `docker-compose.prod.yaml` | 使用的 Compose 文件 |
| `HTTP_PORT` | `8080` | 前端容器对外端口 |
| `DEPLOY_PATH` | 仓库根目录 | `bootstrap.sh` 的项目路径 |
| `REPO_URL` | 空 | `bootstrap.sh` 克隆的仓库地址 |

---

## 🏗️ 架构说明

生产环境 Compose 架构：

```text
┌────────────────────────────────────────────┐
│              ai-net (bridge)               │
│                                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │ postgres │  │  minio   │  │ backend  │ │
│  │  :5432   │  │:9000/9001│  │  :8000   │ │
│  └──────────┘  └──────────┘  └────┬─────┘ │
│                                   │        │
│                          ┌────────▼─────┐  │
│                          │  frontend    │  │
│                          │  :80 (8080)  │  │
│                          └──────────────┘  │
└────────────────────────────────────────────┘
```

- 所有服务通过 `ai-net` 内部网络通信
- `backend` 等待 `postgres` 健康检查通过后才启动
- `frontend` 内嵌 Nginx，将 `/auth`、`/chat` 等 API 路由代理到 `backend:8000`
- 容器间使用服务名通信：`postgres`、`minio`、`backend`（Compose 自动 DNS 解析）
