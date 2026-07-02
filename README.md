# AI 智能知识库系统 · AI Knowledge Base

> 基于 FastAPI + Vue 3 + LangChain + PGVector 构建的企业级 RAG（检索增强生成）知识库系统。支持多格式文档解析、向量化检索、Reranker 重排序、多知识库管理与流式对话。

<p align="center">
  <img src="https://img.shields.io/badge/python-3.12-blue?logo=python" alt="Python 3.12">
  <img src="https://img.shields.io/badge/fastapi-0.115+-009688?logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/vue-3.x-4FC08D?logo=vue.js" alt="Vue 3">
  <img src="https://img.shields.io/badge/vite-8.x-646CFF?logo=vite" alt="Vite 8">
  <img src="https://img.shields.io/badge/postgresql-16-4169E1?logo=postgresql" alt="PostgreSQL 16">
  <img src="https://img.shields.io/badge/docker-ready-2496ED?logo=docker" alt="Docker">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
</p>

---

## 🖥️ 在线演示

> **演示地址**：[http://101.43.5.219:8080/](http://101.43.5.219:8080/)
>
> **演示账号**：`admin` / `123456`

---

## 目录

- [在线演示](#-在线演示)
- [核心特性](#-核心特性)
- [系统架构](#-系统架构)
- [技术栈](#-技术栈)
- [项目结构](#-项目结构)
- [快速开始](#-快速开始)
- [配置说明](#-配置说明)
- [API 概览](#-api-概览)
- [生产部署](#-生产部署)
- [开发路线图](#-开发路线图)
- [贡献指南](#-贡献指南)

---

## 🌟 核心特性

- **多格式文档解析** — 支持 PDF（含 OCR 图片识别）、TXT、Markdown、Excel（`.xlsx` / `.xls`），上传后自动解析、切块、向量化。
- **完整 RAG 链路** — 文档切块 → 向量嵌入 → PGVector 存储 → 语义检索 → Reranker 重排序 → LLM 生成回答。
- **多模型统一接入** — LLM / Embedding / Reranker 均通过 `Provider` + `API Key` + `Base URL` 统一配置，支持 Gemini、DeepSeek、Ollama、阿里云百炼等。
- **多知识库管理** — 支持按业务线创建独立知识库，用户级别数据隔离，级联删除自动清理文档与向量。
- **流式对话 (SSE)** — 基于 Server-Sent Events 的实时流式响应，支持会话管理、历史记录持久化与自动标题生成。
- **异步文档处理** — 上传接口秒级响应，文档解析与向量化在后台异步执行，不影响系统吞吐。
- **容器化部署** — 提供开发与生产两套 Docker Compose 编排，一键启动全部服务。

---

## 🏗️ 系统架构

```text
┌──────────────────────────────────────────────────────────────┐
│                  Frontend (Vue 3 + Vite + Element Plus)       │
│                        Port: 8080 (dev) / 80 (prod)           │
└────────────────────────────┬─────────────────────────────────┘
                             │ HTTP + SSE (streaming)
┌────────────────────────────▼─────────────────────────────────┐
│                  Backend (FastAPI + Uvicorn)                  │
│                        Port: 8000                              │
│  ┌───────────┐ ┌───────────┐ ┌──────────────┐ ┌───────────┐ │
│  │   Auth    │ │   Chat    │ │  Knowledge   │ │  Document │ │
│  │  (JWT)    │ │  (RAG)    │ │  Base CRUD   │ │  Upload   │ │
│  └───────────┘ └─────┬─────┘ └──────────────┘ └─────┬─────┘ │
│                      │                               │       │
│  ┌───────────────────┼───────────────────────────────┼─────┐ │
│  │            Service Layer                          │     │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────┴───┐ │ │
│  │  │ Chunking │ │Embedding │ │ Reranker │ │  Parser   │ │ │
│  │  │ (500/100)│ │ Service  │ │ Service  │ │ (PyMuPDF  │ │ │
│  │  │          │ │          │ │          │ │  + OCR)   │ │ │
│  │  └──────────┘ └────┬─────┘ └────┬─────┘ └───────────┘ │ │
│  └────────────────────┼────────────┼──────────────────────┘ │
└───────────────────────┼────────────┼────────────────────────┘
                        │            │
        ┌───────────────▼──┐  ┌──────▼───────────┐
        │  PGVector        │  │  MinIO            │
        │  (PostgreSQL 16) │  │  (Object Storage) │
        └──────────────────┘  └──────────────────┘
```

**数据流**：
1. **文档入库** — 上传 → MinIO 存储 → 后台异步解析 → 切块 → 向量嵌入 → PGVector
2. **智能问答** — 用户提问 → 向量检索 (Top-20) → Reranker 重排序 (Top-4) → 构建 Prompt → LLM 流式生成 → SSE 推送

---

## 🛠️ 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| **前端框架** | Vue 3 + Vite 8 + TypeScript 6 | 现代化响应式前端 |
| **UI 组件库** | Element Plus 2.14 | 企业级 Vue 3 组件库 |
| **状态管理** | Pinia | Vue 3 官方状态管理 |
| **HTTP / SSE** | Axios + Fetch API | 常规请求 + 流式响应 |
| **后端框架** | FastAPI + Uvicorn | 高性能异步 Python Web 框架 |
| **ORM / 迁移** | SQLAlchemy 2.0 + Alembic | 数据库 ORM 与版本迁移 |
| **认证** | JWT (python-jose) + bcrypt | 无状态认证与密码哈希 |
| **AI 编排** | LangChain (Core, Google GenAI, OpenAI, Ollama, Community, Postgres, Text Splitters) | LLM 应用开发框架 |
| **LLM 提供商** | Gemini / DeepSeek / Ollama | 可配置切换 |
| **Embedding** | 阿里云百炼 (DashScope) / Ollama | OpenAI 兼容接口 |
| **Reranker** | 百炼 qwen3-rerank / DashScope gte-rerank / Ollama | 多后端支持，自动 fallback |
| **向量数据库** | PGVector (pgvector/pgvector:pg16) | PostgreSQL 向量扩展 |
| **对象存储** | MinIO | S3 兼容协议 |
| **文档解析** | PyMuPDF + RapidOCR / pdf2image / pypdf / openpyxl / xlrd | PDF（含 OCR）+ Excel + TXT + MD |
| **容器化** | Docker + Docker Compose | 开发与生产环境编排 |

---

## 📁 项目结构

```text
ai-knowledge/
├── frontend/                       # 前端项目 (Vue 3 + Vite)
│   ├── src/
│   │   ├── api/                    # API 调用层 (auth, chat, document, knowledgeBase, conversation)
│   │   ├── components/             # 可复用组件 (Chat, UploadPanel, icons)
│   │   ├── config/                 # 配置（API 地址、上传限制）
│   │   ├── router/                 # Vue Router 路由定义
│   │   ├── stores/                 # Pinia 状态管理 (auth)
│   │   ├── utils/                  # 工具函数（时间格式化、上传校验）
│   │   └── views/                  # 页面视图 (Chat, Login, Register, KnowledgeBase)
│   ├── Dockerfile                  # 多阶段构建：node:22-alpine → nginx:alpine
│   ├── nginx.conf                  # 容器内 Nginx 反向代理配置
│   └── package.json
│
├── backend/                        # 后端项目 (FastAPI)
│   ├── app/
│   │   ├── api/
│   │   │   ├── deps.py             # 依赖注入 (DB session, 当前用户)
│   │   │   └── routes/             # 路由模块 (auth, chat, conversations, documents, knowledge_bases, search)
│   │   ├── core/                   # 核心模块
│   │   │   ├── config.py           # Pydantic Settings 配置管理
│   │   │   ├── llm.py              # LLM 路由器 (gemini | ollama | deepseek)
│   │   │   ├── embeddings.py       # Embedding 工厂 (openai_compat | ollama)
│   │   │   ├── rerankers/          # Reranker 客户端（多后端 + fallback）
│   │   │   ├── security.py         # JWT + bcrypt
│   │   │   └── minio_client.py     # MinIO 客户端
│   │   ├── db/                     # 数据库引擎与会话管理
│   │   ├── models/                 # SQLAlchemy 数据模型 (User, KnowledgeBase, Document, Conversation, Message)
│   │   ├── schemas/                # Pydantic 请求/响应模型
│   │   ├── services/               # 业务逻辑层
│   │   │   ├── chat_service.py     # RAG 对话（检索→重排→生成）
│   │   │   ├── ingest_service.py   # 文档入库流水线（下载→解析→切块→向量化）
│   │   │   ├── parser_service.py   # 多格式解析器（PDF/OCR/TXT/MD/Excel）
│   │   │   ├── chunk_service.py    # 文本切块（RecursiveCharacterTextSplitter）
│   │   │   ├── embedding_service.py # 向量嵌入服务
│   │   │   ├── vector_service.py   # 向量检索与删除
│   │   │   ├── rerank_service.py   # Reranker 封装
│   │   │   ├── vector_store.py     # PGVector 连接管理
│   │   │   └── ...                 # auth, conversation, document, knowledge_base 服务
│   │   └── main.py                 # FastAPI 应用入口
│   ├── Dockerfile                  # python:3.12-slim-bookworm
│   ├── pyproject.toml              # Python 依赖 (uv/pip)
│   └── .env.example                # 环境变量模板
│
├── deploy/                         # 部署工具
│   ├── deploy.sh                   # 生产部署脚本 (git pull + docker compose)
│   ├── bootstrap.sh                # 服务器首次初始化 (安装 Docker, 克隆仓库)
│   ├── nginx-site.conf             # 宿主机 Nginx 反向代理模板
│   └── frontend.env.production.example
│
├── docs/                           # 文档
│   ├── DEPLOY.md                   # 部署详细说明
│   ├── monio.md                    # MinIO 配置说明
│   ├── postgre.md                  # PostgreSQL 配置说明
│   └── python.md                   # Python 环境说明
│
├── docker-compose.yaml             # 本地开发 (PostgreSQL + MinIO)
└── docker-compose.prod.yaml        # 生产环境 (全栈一键部署)
```

---

## 🚀 快速开始

### 环境要求

| 工具 | 版本要求 | 说明 |
|------|----------|------|
| Python | **3.12.x** | 后端运行环境 |
| Node.js | **^20.19.0 或 >=22.12.0** | 前端构建环境（推荐使用 nvm/fnm 管理版本） |
| Docker + Docker Compose | 最新版 | 基础设施容器化 |

### 1. 启动基础设施

```bash
# 启动 PostgreSQL (PGVector) 和 MinIO
docker compose up -d postgres minio
```

服务信息：

| 服务 | 地址 | 账号/密码 |
|------|------|-----------|
| PostgreSQL | `localhost:5432` | `postgres` / `postgres`，数据库 `ai_kb` |
| MinIO API | `localhost:9000` | `admin` / `admin123456` |
| MinIO Console | `localhost:9001` | `admin` / `admin123456` |

### 2. 配置环境变量

```bash
cd backend
cp .env.example .env
# 编辑 .env，填入 LLM / Embedding 的 API Key 等必要配置
```

最小配置示例（使用 DeepSeek + 阿里云百炼嵌入）：

```env
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-your-key

EMBEDDING_PROVIDER=openai_compat
EMBEDDING_API_KEY=your-dashscope-key
EMBEDDING_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
EMBEDDING_MODEL=text-embedding-v4

POSTGRES_PASSWORD=postgres
MINIO_ACCESS_KEY=admin
MINIO_SECRET_KEY=admin123456
JWT_SECRET=your-random-secret-string
```

### 3. 启动后端

```bash
cd backend

# 创建虚拟环境
python3.12 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -e .            # 基于 pyproject.toml
# 或使用 uv:
# uv sync

# 启动开发服务器（热重载）
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. 启动前端

```bash
cd frontend

npm install
npm run dev
```

访问 `http://localhost:8080` 进入应用。

### 5. 访问 API 文档

| 文档 | 地址 |
|------|------|
| Swagger UI（交互式） | http://127.0.0.1:8000/docs |
| ReDoc | http://127.0.0.1:8000/redoc |
| 系统配置 | http://127.0.0.1:8000/config |
| 健康检查 | http://127.0.0.1:8000/health |

---

## ⚙️ 配置说明

所有配置集中在 `backend/.env` 中，通过 `pydantic-settings` 加载。核心配置项：

### LLM 大模型

```env
LLM_PROVIDER=deepseek          # gemini | ollama | deepseek
# Gemini
GEMINI_API_KEY=                # 必填（LLM_PROVIDER=gemini 时）
GEMINI_MODEL=gemini-2.5-flash
# DeepSeek
DEEPSEEK_API_KEY=              # 必填（LLM_PROVIDER=deepseek 时）
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2
```

### Embedding 向量模型

```env
EMBEDDING_PROVIDER=openai_compat   # openai_compat (百炼/OpenAI) | ollama
EMBEDDING_API_KEY=
EMBEDDING_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
EMBEDDING_MODEL=text-embedding-v4
EMBEDDING_DIMENSIONS=0             # 0 = 模型默认
EMBEDDING_BATCH_SIZE=20            # 单次最大条数（百炼限制 20 条）
```

### Reranker 重排序

```env
RERANK_ENABLED=true
RERANK_PROVIDER=openai_compat      # openai_compat | dashscope | ollama
RERANK_MODEL=qwen3-rerank
RERANK_API_KEY=
RERANK_BASE_URL=
VECTOR_RECALL_K=20                 # 向量检索召回数
RERANK_TOP_K=4                     # 重排序后送入 LLM 的数量
```

### 数据库与存储

```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=
POSTGRES_DB=ai_kb

MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=
MINIO_SECRET_KEY=
MINIO_BUCKET=documents
MINIO_SECURE=false
```

### 其他

```env
JWT_SECRET=change-me-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=10080           # 7 天

CHAT_MAX_MESSAGES=50               # 单会话最大消息数
UPLOAD_ALLOWED_EXTENSIONS=pdf,txt,md,xlsx,xls
UPLOAD_MAX_SIZE_MB=20
```

> **注意**：生产环境通过 `docker-compose.prod.yaml` 自动覆盖 `POSTGRES_HOST=postgres` 和 `MINIO_ENDPOINT=minio:9000`，无需手动修改。

---

## 📡 API 概览

### 认证

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| POST | `/auth/register` | — | 用户注册 |
| POST | `/auth/login` | — | 登录，返回 JWT |
| GET | `/auth/me` | Bearer | 获取当前用户信息 |

### 知识库

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| GET | `/knowledge-bases` | Bearer | 列出用户的知识库 |
| POST | `/knowledge-bases` | Bearer | 创建知识库 |
| DELETE | `/knowledge-bases/{id}` | Bearer | 删除知识库（级联删除文档与向量） |

### 文档

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| POST | `/documents/upload` | Bearer | 上传文档（异步解析入库） |
| GET | `/documents?knowledge_base_id=` | Bearer | 列出知识库下的文档 |
| DELETE | `/documents/{id}` | Bearer | 删除文档与关联向量 |

### 对话

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| POST | `/chat` | Bearer | 非流式对话 |
| POST | `/chat/stream` | Bearer | 流式对话 (SSE) |
| GET | `/conversations` | Bearer | 列出会话 |
| POST | `/conversations` | Bearer | 创建会话 |
| GET | `/conversations/{id}` | Bearer | 获取会话详情与消息 |
| PATCH | `/conversations/{id}` | Bearer | 更新会话（标题/知识库） |
| DELETE | `/conversations/{id}` | Bearer | 删除会话 |
| POST | `/conversations/{id}/chat/stream` | Bearer | 会话内流式对话 (SSE) |

### 检索

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| POST | `/search` | Bearer | 向量语义搜索 |

### 系统

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| GET | `/health` | — | 健康检查 |
| GET | `/config` | — | 系统配置信息 |
| GET | `/docs` | — | Swagger UI |
| GET | `/redoc` | — | ReDoc |

---

## 🐳 生产部署

详细部署说明参见 [`docs/DEPLOY.md`](docs/DEPLOY.md) 和 [`deploy/`](deploy/) 目录。

### Docker Compose 一键部署

```bash
# 1. 确保 backend/.env 已配置
cp backend/.env.example backend/.env
vim backend/.env

# 2. 构建并启动全部服务
docker compose --env-file backend/.env -f docker-compose.prod.yaml up -d --build

# 3. 查看运行状态
docker compose -f docker-compose.prod.yaml ps
```

### 新服务器首次部署

```bash
# 以 root 执行 bootstrap.sh，自动安装 Docker 并克隆仓库
curl -fsSL https://raw.githubusercontent.com/<your-repo>/main/deploy/bootstrap.sh | bash
```

### 更新部署

```bash
cd deploy
./deploy.sh   # git pull + docker compose up -d --build
```

### 常用运维命令

| 操作 | 命令 |
|------|------|
| 查看后端日志 | `docker compose -f docker-compose.prod.yaml logs -f backend` |
| 进入后端容器 | `docker exec -it ai-backend bash` |
| 无缓存重建后端 | `docker compose -f docker-compose.prod.yaml build --no-cache backend` |
| 重启单个服务 | `docker compose -f docker-compose.prod.yaml restart backend` |
| 清理环境（含数据卷） | `docker compose -f docker-compose.prod.yaml down -v` |

---

## 📅 开发路线图

- [x] 基础 RAG 链路：文档上传 → 解析 → 切块 → 向量化 → 检索 → LLM 回答
- [x] 多格式文档支持（PDF + OCR、TXT、MD、Excel）
- [x] 多知识库管理与用户级别隔离
- [x] JWT 认证与用户体系
- [x] 会话管理（多轮对话、历史持久化、自动标题）
- [x] SSE 流式响应
- [x] Reranker 重排序（百炼 / DashScope / Ollama 多后端）
- [x] 多 LLM 提供商支持（Gemini / DeepSeek / Ollama）
- [x] Docker Compose 生产部署
- [ ] 混合检索（向量 + BM25 全文检索）
- [ ] RBAC 细粒度权限（Admin / Editor / Viewer）
- [ ] 异步任务队列（Celery / RQ + Redis）替代 BackgroundTasks
- [ ] 云端 SaaS 化部署
- [ ] 监控与可观测性（日志、指标、链路追踪）

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request。

### 开发流程

1. Fork 本仓库
2. 创建特性分支：`git checkout -b feature/your-feature`
3. 提交更改：`git commit -m 'feat: add some feature'`
4. 推送到分支：`git push origin feature/your-feature`
5. 提交 Pull Request

### 提交规范

遵循 [Conventional Commits](https://www.conventionalcommits.org/)：

- `feat:` 新功能
- `fix:` 问题修复
- `docs:` 文档更新
- `refactor:` 代码重构
- `chore:` 构建/工具变更

---

## 📄 许可证

本项目基于 MIT 许可证开源。详见 [LICENSE](LICENSE) 文件。

---

## 🙏 致谢

本项目基于以下开源项目构建：

- [FastAPI](https://fastapi.tiangolo.com/) — 现代 Python Web 框架
- [LangChain](https://www.langchain.com/) — LLM 应用开发框架
- [PGVector](https://github.com/pgvector/pgvector) — PostgreSQL 向量扩展
- [Element Plus](https://element-plus.org/) — Vue 3 组件库
- [MinIO](https://min.io/) — 高性能对象存储
