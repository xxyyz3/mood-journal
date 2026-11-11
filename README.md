# Mood Journal

基于 **FastAPI + MySQL** 的心情记录后端，提供心情记录的增删查改、统计与 AI 总结，并附带 AI 角色对话、基于角色档案的 RAG 问答、用户长期记忆和 JWT 鉴权。

项目使用 DeepSeek（OpenAI 兼容接口）处理对话与总结，SiliconFlow 提供向量化与重排序服务，ChromaDB 负责本地向量检索。AI 会话、RAG 历史与长期记忆按登录用户隔离；后端支持 Docker Compose 部署，`frontend/` 提供一个静态的接口测试台。

## 功能特性

- **JWT 鉴权**：用户名密码通过 `POST /auth/token` 换取 JWT，业务接口统一使用 `Authorization: Bearer <token>`，Token 默认 30 分钟过期
- **心情记录**：新增、列表、详情、删除，支持按 `mood` 过滤，字段带长度校验
- **心情统计**：返回记录总数与各 `mood` 的数量分布（最多统计 15 条）
- **AI 心情总结**：汇总最近的心情记录，交给 DeepSeek 生成一句话总结；没有记录时不调用模型
- **AI 角色对话**：按 `session_id` 组织多轮会话，保留最近 10 条上下文；对话历史按登录用户隔离，支持普通响应和流式响应
- **RAG 角色问答**：把角色档案切块、向量化后存入 ChromaDB，检索相关段落并注入长期记忆；普通接口返回命中的来源标题，流式接口支持增量输出
- **用户长期记忆**：从问答内容中提取用户的长期信息（姓名、职业、喜好等），以登录用户为维度写入 `UserMemory`，后续问答作为背景注入
- **用户管理脚本**：通过 `app/scripts/create_user.py` 创建或重置登录用户，无需额外注册接口
- **Docker 部署**：提供 Dockerfile 与 docker-compose，内置 ChromaDB 持久化卷
- **接口测试台**：`frontend/` 提供登录、连接检测、聊天流式输出和 RAG 流式问答的静态页面

## 技术栈

| 层面 | 技术 | 用途 |
| --- | --- | --- |
| 语言 | Python 3.10+（Docker 镜像使用 3.11） | 代码使用 `int \| None`、`str \| None` 等新语法 |
| Web 框架 | FastAPI | 路由、依赖注入、CORS 中间件、`StreamingResponse`、`BackgroundTasks` |
| ASGI 服务器 | Uvicorn | 本地开发与生产运行 |
| 数据校验 | Pydantic | 请求/响应模型、`Literal`、`Field` 校验 |
| ORM / 模型 | SQLModel、SQLAlchemy | 表模型、`Session`、`select / where / order_by / limit` |
| 数据库 | MySQL（PyMySQL 驱动） | 生产数据存储 |
| 数据库（测试/本地回退） | SQLite | 未配置 `DATABASE_URL` 时的默认库；测试用 `tmp_path` 临时库 |
| 数据库迁移 | Alembic | 版本化管理表结构 |
| 鉴权 | OAuth2 Password Flow、JWT（PyJWT）、pwdlib/Argon2、python-multipart | 登录、Token 签发与密码哈希 |
| 对话模型 | DeepSeek API（OpenAI Python SDK） | 心情总结、角色对话、问题改写、记忆抽取 |
| Embedding | SiliconFlow `BAAI/bge-m3` | 角色文档与问题向量化 |
| Rerank | SiliconFlow `BAAI/bge-reranker-v2-m3` | 检索结果重排序 |
| 向量数据库 | ChromaDB（PersistentClient） | 角色知识库的本地持久化与相似度检索 |
| 配置管理 | python-dotenv | 从 `.env` 读取环境变量 |
| 测试 | pytest、Starlette `TestClient`、`monkeypatch` | 接口测试、JWT 登录与外部调用隔离 |
| 数值计算 | NumPy | 余弦相似度工具函数 |
| 部署 | Docker Compose；nssm + ngrok（Windows） | 容器化部署；Windows 服务与内网穿透 |
| 前端 | 原生 HTML/CSS/JS | `frontend/` 接口测试台 |

## 架构

```text
浏览器（frontend/ 接口测试台）
  │  Authorization: Bearer <JWT>
  ▼
FastAPI Router（auth / entries / chat / ask）
  │  get_current_user → 当前 username
  ▼
Service（业务逻辑、提示词拼装、检索与生成编排）
  │
  ├── SQLModel / SQLAlchemy ──▶ MySQL（生产）/ SQLite（测试）
  ├── DeepSeek API ──────────▶ 对话、总结、问题改写、记忆抽取
  ├── SiliconFlow API ───────▶ Embedding、Rerank
  └── ChromaDB ──────────────▶ 角色知识库向量检索
```

- `routers/` 负责 HTTP 层：解析 JWT、注入数据库会话、参数校验、把上游异常转换成 HTTP 状态码
- `services/` 承载业务逻辑，便于单独测试
- `models.py` 定义表结构，`schemas.py` 定义接口出入参，两者职责分离
- `ChatMessage` 同时保存 `/chat` 对话和 `/ask` 问答记录，并通过 `user_id`（存 username）隔离不同用户
- `app/data/chunks.json` 是角色档案的切分结果，`app/scripts/split_test.py` 负责从 `character.md` 生成它

## 鉴权与用户隔离

### 登录

`POST /auth/token` 使用 OAuth2 Password Flow，请求体为 `application/x-www-form-urlencoded`：

```bash
curl -X POST http://127.0.0.1:8000/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=alice&password=secret123"
```

```json
{"access_token": "eyJ...", "token_type": "bearer"}
```

把返回的 `access_token` 保存到 shell 变量（后续示例用 `$TOKEN` 引用）：

```bash
TOKEN="eyJ..."
```

之后访问受保护接口时携带：

```http
Authorization: Bearer <access_token>
```

JWT 使用 `SECRET_KEY` 签名、`ALGORITHM` 指定算法（示例为 HS256），payload 中包含 `sub`（用户名）与 `exp`，有效期固定为 30 分钟。Token 缺失、非法、过期或对应数据库用户不存在时返回 `401`。

### 用户来源

- `/chat`、`/chat/history`、`/chat/stream` 的用户身份取自 JWT，聊天记录按 `ChatMessage.user_id` 过滤
- `/ask`、`/ask/stream` 的用户身份同样取自 JWT，RAG 历史问题与 `UserMemory` 都按当前用户名读写
- `AskRequest` 中的 `user_id` 字段仍然可以传，但仅为兼容旧客户端保留，服务端会忽略它，防止读取或写入他人记忆
- 心情记录接口已要求登录，但 `MoodEntry` 目前没有 `user_id` 字段，记录本身仍由所有登录用户共享（见“说明与限制”）

### 创建用户

项目没有注册接口，用户通过命令行脚本创建（密码使用 Argon2 哈希后入库）：

```bash
# 在 backend/ 目录下执行
python -m app.scripts.create_user --username alice --password secret123
python -m app.scripts.create_user --username alice --password newpass --force
python -m app.scripts.create_user --username alice --password secret123 --email alice@example.com
```

脚本会使用 `DATABASE_URL` 并自动创建缺失的表。`--force` 用于重置已存在用户的密码。

## 目录结构

```text
mood-journal/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI 实例、CORS、路由注册、自动建表
│   │   ├── deps.py                 # 数据库引擎、Session 依赖、JWT 登录依赖、老库列兼容
│   │   ├── models.py               # MoodEntry / ChatMessage / UserMemory / User
│   │   ├── schemas.py              # 请求、响应与 Token 模型
│   │   ├── llm.py                  # DeepSeek 客户端（普通 / 流式）
│   │   ├── siliconflow_llm.py      # SiliconFlow Embedding 客户端
│   │   ├── prompts.py              # 对话、总结、RAG 角色提示词
│   │   ├── routers/
│   │   │   ├── auth.py             # POST /auth/token
│   │   │   ├── entries.py          # 心情记录接口
│   │   │   ├── chat.py             # AI 对话接口
│   │   │   └── rag.py              # RAG 问答接口
│   │   ├── services/
│   │   │   ├── service_auth.py     # 登录校验、JWT 签发与解析、密码哈希
│   │   │   ├── service_entries.py  # 记录查询、统计、总结
│   │   │   ├── service_chat.py     # 多轮会话、用户隔离与流式对话
│   │   │   └── service_rag.py      # 问题改写、检索、重排、记忆
│   │   ├── data/
│   │   │   ├── character.md        # 角色设定原文
│   │   │   └── chunks.json         # 按二级标题切分的文档块
│   │   └── scripts/
│   │       ├── split_test.py       # character.md -> chunks.json
│   │       └── create_user.py      # 创建 / 重置登录用户
│   ├── tests/                      # pytest 用例
│   ├── alembic/                    # 数据库迁移脚本
│   ├── alembic.ini
│   ├── requirements.txt            # Python 依赖
│   ├── .env.example                # 环境变量样例
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── .dockerignore
│   ├── body.json                   # /chat 调试请求体
│   └── body_stream.json            # /ask 调试请求体
└── frontend/
    ├── index.html                  # 接口测试台页面
    ├── app.js                      # 登录、流式聊天、流式 RAG
    └── style.css
```

## 快速开始

### 环境要求

- Python 3.10+（Docker 镜像使用 3.11）
- MySQL（推荐 8.0+）；本地试用也可直接用 SQLite
- DeepSeek API Key（对话、总结、问题改写、记忆抽取）
- SiliconFlow API Key（Embedding 与 Rerank）
- 可选：Docker / Docker Compose；ngrok（需要公网访问时）

### 方式一：Docker Compose（推荐）

Compose 只启动后端服务，**不包含 MySQL**；请先创建一个后端容器可访问的 MySQL 数据库（或在 `DATABASE_URL` 中使用 SQLite 做临时演示，但容器重建后数据会丢失）：

```sql
CREATE DATABASE mood_journal CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

```bash
cd backend
cp .env.example .env
# 编辑 .env：至少填写 DATABASE_URL、SECRET_KEY、ALGORITHM、
# DEEPSEEK_API_KEY、DEEPSEEK_BASE_URL、SILICONFLOW_API_KEY、SILICONFLOW_BASE_URL
docker compose up -d --build
```

容器内启动后：

- API：`http://127.0.0.1:8000`
- Swagger：`http://127.0.0.1:8000/docs`
- 查看日志：`docker compose logs -f backend`
- 创建登录用户：

```bash
docker compose exec backend python -m app.scripts.create_user \
  --username alice --password secret123
```

Compose 会把宿主机的 `backend/chroma_db/` 挂载到容器 `/app/chroma_db`，避免重建容器后丢失向量库。若 MySQL 运行在宿主机，`DATABASE_URL` 中的主机名在 Docker Desktop 下可用 `host.docker.internal`；Linux 下可使用宿主机 IP 或额外配置 `host-gateway`。

### 方式二：本地运行

```bash
git clone https://github.com/xxyyz3/mood-journal.git
cd mood-journal/backend

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# 编辑 .env，填入数据库、JWT 与模型服务配置
```

如果使用 MySQL，请先创建数据库：

```sql
CREATE DATABASE mood_journal CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

只想快速试用时，可把 `DATABASE_URL` 改为 SQLite：

```dotenv
DATABASE_URL=sqlite:///./mood_journal.db
```

创建登录用户并启动服务：

```bash
# 在 backend/ 目录下执行；脚本会自动建表
python -m app.scripts.create_user --username alice --password secret123
uvicorn app.main:app --reload
```

- API：`http://127.0.0.1:8000`
- Swagger：`http://127.0.0.1:8000/docs`
- ReDoc：`http://127.0.0.1:8000/redoc`

首次启动时，ChromaDB 集合为空，程序会读取 `app/data/chunks.json` 中的 8 个文档块，调用 SiliconFlow Embedding 生成向量并写入 `backend/chroma_db/`。这一步需要有效的 `SILICONFLOW_API_KEY` 和网络；后续启动会直接复用已有集合。

### 启动前端接口测试台

前端是无需构建的静态页面，默认后端地址为 `http://127.0.0.1:8000`，CORS 默认允许 `localhost:5173` / `127.0.0.1:5173`：

```bash
# 在仓库根目录执行
python -m http.server 5173 --directory frontend
```

浏览器打开 `http://127.0.0.1:5173`，在左侧填写后端地址并登录后即可测试聊天和 RAG 流式接口。RAG 页保留了 `user_id` 输入框，但后端以 JWT 中的用户为准，该字段会被忽略。直接以 `file://` 打开页面通常会被 CORS 拦截，建议通过静态服务器访问。

## 配置项

| 变量 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `DATABASE_URL` | 生产必填 | `sqlite:///./mood_journal.db` | SQLAlchemy 连接串。生产使用 `mysql+pymysql://用户:密码@主机:3306/库名?charset=utf8mb4`；Alembic 也读取该变量 |
| `SECRET_KEY` | 是 | 无 | JWT 签名密钥，务必替换为随机长字符串；未配置时登录接口会失败 |
| `ALGORITHM` | 是 | 无 | JWT 签名算法，样例配置为 `HS256` |
| `CORS_ORIGINS` | 否 | `http://localhost:5173,http://127.0.0.1:5173` | 允许的前端来源，逗号分隔 |
| `DB_ECHO` | 否 | `false` | 是否打印 SQL，开发时设为 `true` |
| `DEEPSEEK_API_KEY` | 是 | 无 | DeepSeek API Key；缺少时 `llm.py` 初始化客户端会失败 |
| `DEEPSEEK_BASE_URL` | 是 | 无 | DeepSeek API 地址，例如 `https://api.deepseek.com` |
| `DEEPSEEK_MODEL` | 否 | `deepseek-chat` | 对话模型名 |
| `SILICONFLOW_API_KEY` | 是 | 无 | SiliconFlow API Key，用于 Embedding 和 Rerank；缺少时启动会失败 |
| `SILICONFLOW_BASE_URL` | 是 | 无 | SiliconFlow OpenAI 兼容地址，例如 `https://api.siliconflow.cn/v1` |

> 注意：`llm.py` 与 `siliconflow_llm.py` 在模块导入时就创建 OpenAI 客户端，缺少对应的 API Key 会导致应用启动失败。
>
> Rerank 请求地址在代码中固定为 `https://api.siliconflow.cn/v1/rerank`，不随 `SILICONFLOW_BASE_URL` 变化。
>
> JWT 有效期固定为 30 分钟（`service_auth.ACCESS_TOKEN_EXPIRE_MINUTES`）。
>
> 后端通过 `load_dotenv()` 读取 `.env`，因此请在 `backend/` 目录启动 uvicorn、pytest 和 Alembic。

## 接口说明

除 `/auth/token`、`/health`、`/docs` 等文档路径外，所有接口都需要在请求头携带：

```http
Authorization: Bearer <access_token>
```

### Auth

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/auth/token` | 用用户名密码换取 JWT（form-urlencoded） |

登录失败（用户名或密码错误）返回 `401`；表单缺少字段返回 `422`。

### Health

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/health` | 健康检查，返回 `{"status": "ok"}` |

### Entries

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/entries` | 新增心情记录 |
| GET | `/entries` | 记录列表，可选 `?mood=` 过滤 |
| GET | `/entries/{entry_id}` | 记录详情 |
| DELETE | `/entries/{entry_id}` | 删除记录，返回 `204` |
| GET | `/entries/stats` | 统计总数与 `mood` 分布，可选 `?mood=` 过滤 |
| GET | `/entries/summary` | 用模型总结最近的心情记录 |

字段约束：`mood` 最长 20 字符，`content` 最长 200 字符。所有 Entries 接口都需要登录，但记录目前不按用户隔离。新增记录示例：

```bash
curl -X POST http://127.0.0.1:8000/entries \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"mood": "happy", "content": "今天天气很好"}'
```

返回：

```json
{
  "mood": "happy",
  "content": "今天天气很好",
  "id": 1,
  "created_at": "2026-11-11T10:00:00Z"
}
```

统计接口返回：

```json
{"total": 3, "by_mood": {"happy": 2, "calm": 1}}
```

说明：`/entries/stats` 当前最多统计 15 条记录，`/entries/summary` 只取最近 15 条记录；`/entries/summary` 在没有记录时返回固定文案 `还没有心情记录喵~`，不会调用模型。

### Chat

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/chat` | AI 角色对话，返回完整回复 |
| POST | `/chat/stream` | AI 角色对话，流式返回文本增量 |
| GET | `/chat/history?session_id=...` | 查询当前用户在某个会话下的历史消息 |

请求体：

```json
{"message": "今天好累", "session_id": "demo"}
```

- `message` 有默认值 `一句话介绍一下你自己`，`session_id` 必填
- 每次对话会读取该用户在该 `session_id` 下最近 10 条消息作为上下文
- 普通接口返回 `{"reply": "..."}`；上游超时返回 `504`，上游错误返回 `502`
- 历史接口返回 `id`、`role`、`content`、`created_at`，按时间升序，不返回 `session_id` 或 `user_id`
- 对话记录写入 `ChatMessage`，`role` 为 `user` 或 `assistant`，`user_id` 存当前用户名

流式示例：

```bash
curl -N -X POST http://127.0.0.1:8000/chat/stream \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "今天好累", "session_id": "demo"}'
```

响应 `Content-Type` 为 `text/event-stream`，但返回的是**纯文本增量**，没有 SSE 的 `data:` 帧前缀。由于接口是 `POST`，浏览器的 `EventSource` 无法直接使用，建议用 `fetch` 读取 `response.body`：

```javascript
const res = await fetch("/chat/stream", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
  },
  body: JSON.stringify({ message: "今天好累", session_id: "demo" }),
});
const reader = res.body.getReader();
const decoder = new TextDecoder();
const output = document.querySelector("#output");
while (true) {
  const { value, done } = await reader.read();
  if (done) break;
  output.textContent += decoder.decode(value, { stream: true });
}
```

对话过程中发生超时或上游错误时，流里会分别出现 `[API响应超时]`、`[API错误]`，本轮消息不会落库。

### RAG 问答

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/ask` | 基于角色档案的 RAG 问答 |
| POST | `/ask/stream` | RAG 问答，流式返回文本增量 |

请求体：

```json
{"question": "她住在哪里？", "session_id": "demo"}
```

`question`、`session_id` 必填；`user_id` 为已废弃的可选字段，传了也会被忽略。普通接口返回：

```json
{
  "answer": "...",
  "sources": ["## 住址"]
}
```

- `sources` 是命中文档块的首行标题，结构为字符串数组
- 没有检索到相关内容时返回 `"answer": "文档中没有相关内容"`，`sources` 为空；此时直接返回固定文案，不生成回答，但仍会尝试抽取长期记忆
- 命中资料时，普通接口把本轮问答写入 `ChatMessage`，并触发一次长期记忆抽取
- 命中资料时，流式接口在响应结束后通过 `BackgroundTasks` 落库并抽取记忆，因此客户端收到完整回复不代表后台任务已经完成

## RAG 流程

1. **问题改写**：取同一用户在同一 `session_id` 下最近 5 条用户问题，让 DeepSeek 结合上下文把当前问题改写成更利于检索的关键词句；无历史时直接使用原问题
2. **向量化**：调用 SiliconFlow `BAAI/bge-m3` 生成问题向量
3. **向量召回**：ChromaDB 语义检索 `top_k=5`
4. **重排**：流式接口把召回的 5 个文档块交给 `BAAI/bge-reranker-v2-m3` 重排后取前 3；非流式接口直接使用召回的 5 个文档块
5. **生成**：把当前用户的 `UserMemory` 背景和命中文档拼进提示词，要求模型只依据资料回答
6. **落库与记忆**：命中资料时把问答写入 `ChatMessage`（带 `user_id`）；再用 DeepSeek 从对话中抽取用户长期信息，写入 `UserMemory`

角色知识库的构建：

- 原始资料：`app/data/character.md`
- 切分脚本：`app/scripts/split_test.py`，按 `##` 二级标题切分，写出 `app/data/chunks.json`
- 建立索引：应用启动时若 `chroma_db` 集合为空，自动向量化并写入
- 重建索引：删除 `backend/chroma_db/` 后重启服务；修改 `character.md` 后先重新生成 `chunks.json`

```bash
# 在 backend/ 目录下重新切分角色文档
python -m app.scripts.split_test
```

## 数据库模型

| 表 | 字段 | 说明 |
| --- | --- | --- |
| `moodentry` | `id`、`mood`、`content`、`created_at`、`note` | 心情记录，`created_at` 建索引；`note` 暂未在创建与详情模型中暴露 |
| `chatmessage` | `id`、`role`、`content`、`created_at`、`session_id`、`user_id` | AI 对话与 RAG 问答记录，`created_at`、`session_id`、`user_id` 建索引；`user_id` 存用户名，可空以兼容老数据 |
| `usermemory` | `id`、`user_id`、`fact_content`、`created_at` | 用户长期记忆，`user_id` 存用户名并建索引 |
| `user` | `id`、`username`、`email`、`full_name`、`hashed_password`、`disabled` | 登录用户，`username` 唯一索引，密码使用 Argon2 哈希 |

### 建表与迁移

应用启动时会执行 `SQLModel.metadata.create_all()`，自动创建当前模型对应的缺失表；`deps._ensure_chat_message_user_id()` 还会为升级前的老库补上 `chatmessage.user_id` 列和索引，这一步是幂等的。

现有 Alembic 版本链只覆盖早期的 `moodentry`、`chatmessage` 与 `note` 字段调整；`user`、`usermemory` 和 `chatmessage.user_id` 依赖启动时自动建表/补列，尚无对应迁移脚本。全新库可以先让应用自动建表，也可以先执行迁移，但不要对已经由 `create_all()` 建好的库重复执行初始迁移。

迁移命令（均在 `backend/` 目录下执行）：

```bash
alembic upgrade head                          # 升级到最新版本
alembic revision --autogenerate -m "描述"     # 根据模型改动生成迁移
alembic downgrade -1                          # 回滚一个版本
```

## 测试

```bash
cd backend
SECRET_KEY=test-secret ALGORITHM=HS256 pytest -q
```

如果 `.env` 中已经配置了 `SECRET_KEY` 和 `ALGORITHM`，直接执行 `pytest -q` 即可。Windows PowerShell：

```powershell
$env:SECRET_KEY = "test-secret"
$env:ALGORITHM = "HS256"
pytest -q
```

测试通过以下方式隔离外部依赖：

- `conftest.py` 用 `tmp_path` 创建临时 SQLite 库，自动创建 `tester` 用户并调用 `/auth/token` 登录，随后为所有请求自动带上 JWT
- 通过 `app.dependency_overrides` 替换 `get_session`，测试不会污染生产数据库
- 大多数外部调用通过 `monkeypatch` 替换，覆盖鉴权、聊天、RAG 与用户隔离场景

注意：导入 `app.main` 时会创建 DeepSeek / SiliconFlow 客户端并初始化 ChromaDB，因此跑测试前至少需要配置 `DEEPSEEK_API_KEY`、`SILICONFLOW_API_KEY` 等变量；首次运行若没有现成的 `backend/chroma_db/`，还会调用 SiliconFlow 生成向量。部分 RAG 用例（例如空检索场景的记忆抽取）仍会访问真实 DeepSeek 服务，完全离线运行前需要补充相应 mock。

## 部署

### Docker Compose

仓库提供 `backend/Dockerfile` 与 `backend/docker-compose.yml`，镜像基于 Python 3.11，启动 `uvicorn app.main:app --host 0.0.0.0 --port 8000`。Compose 只包含后端服务，MySQL 需单独提供；`chroma_db` 通过宿主机目录挂载持久化。生产使用时请替换 `.env.example` 中的 `SECRET_KEY`、数据库密码和模型服务密钥。

### Windows 单机

项目也支持 Windows 单机部署：

- **进程管理**：用 [nssm](https://nssm.cc/) 把 `uvicorn app.main:app` 注册为 Windows 服务，开机自启
- **公网访问**：ngrok 将本机端口映射到公网，当前项目主页指向 ngrok 的 `/docs`
- **日志**：uvicorn 日志重定向到 `D:\logs\`，并配置自动切割
- **数据库**：本机 MySQL，连接串通过 `DATABASE_URL` 注入
- **配置**：生产 `.env` 中设置强随机 `SECRET_KEY`、强密码，并限制 `CORS_ORIGINS`

无论使用哪种部署方式，都应避免把 `.env` 提交到仓库，并在公网环境启用 HTTPS。

## 说明与限制

- 心情记录接口已要求登录，但 `MoodEntry` 尚无 `user_id` 字段，记录仍是所有登录用户共享的
- 升级前的老 `ChatMessage.user_id` 为空，升级后不会出现在任何用户的历史或对话上下文中
- `user`、`usermemory` 与 `chatmessage.user_id` 依赖启动时自动建表/补列，尚未生成 Alembic 迁移
- `/entries/stats`、`/entries/summary` 只处理 15 条记录
- 流式接口虽然声明 `text/event-stream`，但输出的是纯文本增量，不是标准 SSE 事件流
- Rerank 地址硬编码为 `https://api.siliconflow.cn/v1/rerank`，接入兼容代理时需要改代码
- `UserMemory` 目前只有写入和查询，没有独立的读取、修改或删除接口
- 没有注册、改密等用户管理接口，用户只能通过命令行脚本创建或重置
- 仓库尚未配置 CI；Docker Compose 不包含 MySQL，需要外部数据库
- 部分测试依赖真实的 DeepSeek / SiliconFlow 服务，未配置密钥时无法完全离线运行
