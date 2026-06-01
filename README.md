swagger文档地址
http://127.0.0.1:8000/docs

样式2
http://127.0.0.1:8000/redoc
查看配置
http://127.0.0.1:8000/config





# 第一阶段：搭建最小可运行版本

目标：

```text
上传文档
   ↓
切分
   ↓
Embedding
   ↓
PGVector
   ↓
检索
   ↓
Gemini回答
```

## Step 1：创建项目结构

```text
ai-knowledge-base/
├── frontend/
│   ├── src/
│   └── package.json
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── services/
│   │   ├── repositories/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── core/
│   │   └── main.py
│   │
│   ├── requirements.txt
│   └── .env
│
└── docker-compose.yml
```

---

## Step 2：启动基础环境

建议 Docker。

```yaml
postgres:
  image: pgvector/pgvector:pg16

minio:
  image: minio/minio
```

先启动：

* PostgreSQL
* PGVector
* MinIO

验证：

```sql
CREATE EXTENSION vector;
```

成功即可。

---

## Step 3：FastAPI 初始化

安装：

```bash
pip install fastapi
pip install uvicorn
pip install sqlalchemy
pip install psycopg2-binary
```

创建：

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def health():
    return {"status": "ok"}
```

访问：

```text
http://localhost:8000/docs
```

---

## Step 4：接入 Gemini

安装：

```bash
pip install langchain-google-genai
```

测试：

```python
from langchain_google_genai import ChatGoogleGenerativeAI

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash"
)

response = llm.invoke("你好")
```

确认：

```text
Gemini可以返回结果
```

---

# 第二阶段：实现知识库核心

目标：

```text
上传PDF
 ↓
切分
 ↓
向量化
 ↓
存储
 ↓
问答
```

---

## Step 5：文档上传

接口：

```http
POST /documents/upload
```

先只支持：

* pdf
* txt
* md

存储到：

```text
MinIO
```

记录到：

```sql
documents
```

表：

```sql
id
filename
path
size
created_at
```

---

## Step 6：文档解析

安装：

```bash
pip install pypdf
```

使用：

```python
PyPDFLoader
```

输出：

```python
[
  page1,
  page2,
  page3
]
```

---

## Step 7：文本切块

```python
RecursiveCharacterTextSplitter
```

参数：

```python
chunk_size=500
chunk_overlap=100
```

输出：

```python
[
  chunk1,
  chunk2,
  chunk3
]
```

---

## Step 8：Embedding

安装：

```bash
pip install langchain-google-genai
```

使用：

```python
GoogleGenerativeAIEmbeddings
```

生成：

```python
vector = embedding.embed_query(text)
```

---

## Step 9：存入 PGVector

安装：

```bash
pip install langchain-postgres
```

建立：

```python
PGVector(
    embeddings=embedding,
    collection_name="knowledge"
)
```

存储：

```python
vector_store.add_documents()
```

---

## Step 10：检索测试

接口：

```http
POST /search
```

输入：

```json
{
  "query":"FastAPI是什么"
}
```

输出：

```json
[
  {
    "content":"FastAPI 是 ..."
  }
]
```

如果能搜到正确 Chunk：

```text
RAG基础完成
```

---

# 第三阶段：实现聊天

目标：

```text
用户提问
 ↓
检索相关Chunk
 ↓
构造Prompt
 ↓
Gemini
 ↓
返回答案
```

---

## Step 11：创建 Chat Service

```python
class ChatService:
    pass
```

---

## Step 12：实现 Retriever

```python
retriever = vector_store.as_retriever()
```

获取：

```python
docs = retriever.invoke(question)
```

---

## Step 13：Prompt模板

例如：

```python
你是企业知识库助手。

上下文：

{context}

问题：

{question}

请基于上下文回答。
```

---

## Step 14：实现 RAG Chain

```python
question
 ↓
retrieve
 ↓
prompt
 ↓
gemini
 ↓
answer
```

接口：

```http
POST /chat
```

返回：

```json
{
  "answer":"..."
}
```

到这里 MVP 已经可用。

---

# 第四阶段：企业化改造

## Step 15：用户系统

表：

```sql
users
```

字段：

```sql
id
username
password_hash
role
```

JWT：

```bash
pip install python-jose
```

实现：

```http
/login
/register
```

---

## Step 16：聊天记录

表：

```sql
conversations

messages
```

记录：

```text
用户问题
AI回答
时间
```

---

## Step 17：多知识库

表：

```sql
knowledge_bases
```

例如：

```text
财务知识库
研发知识库
人事知识库
```

检索时：

```python
filter={"kb_id":1}
```

---

## Step 18：权限控制

RBAC：

```text
Admin
Editor
Viewer
```

控制：

* 上传文档
* 删除文档
* 查看知识库

---

# 第五阶段：上线前优化

## Step 19：加入 Reranker

仅向量检索效果一般。

加入重排序：

```text
Question
 ↓
Top20
 ↓
Reranker
 ↓
Top5
 ↓
LLM
```

常见：

* BGE Reranker
* Jina Reranker

---

## Step 20：异步文档处理

上传后：

```text
立即返回
```

后台：

```text
解析
切块
Embedding
入库
```

可用：

* Celery
* RQ
* Dramatiq

---

## Step 21：Docker 化

最终：

```text
Vue3
FastAPI
PostgreSQL
PGVector
MinIO
Redis
```

统一：

```bash
docker compose up -d
```

---

# 最终架构

```text
Vue3
  ↓
FastAPI
  ├── Auth
  ├── Chat
  ├── Knowledge
  └── File
          ↓
      MinIO

Chat
 ↓
LangChain
 ↓
Retriever
 ↓
Reranker
 ↓
PGVector
 ↓
Gemini

PostgreSQL
 ↓
Users
Chats
Documents
KnowledgeBases
```

开发顺序严格按：

**环境搭建 → Gemini 接入 → PDF 上传 → 向量化 → 检索 → RAG 问答 → 用户系统 → 多知识库 → 权限 → Reranker → 异步任务**


