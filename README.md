# Mood Journal

基于 **FastAPI + MySQL** 的心情记录后端，提供心情记录的增删查改、统计与 AI 总结，并附带 AI 角色对话和基于角色档案的 RAG 问答能力。

项目使用 DeepSeek（OpenAI 兼容接口）作为对话模型，SiliconFlow 提供向量化与重排序服务，ChromaDB 负责本地向量检索。生产数据存放在 MySQL，测试使用 SQLite 隔离；通过 Bearer Token 鉴权，并允许配置的前端来源跨域调用。

## 功能特性

- **心情记录**：新增、列表、详情、删除，支持按 `mood` 过滤，字段带长度校验
- **心情统计**：返回记录总数与各 `mood` 的数量分布（最多统计 15 条）
- **AI 心情总结**：汇总最近的心情记录，交给 DeepSeek 生成一句话总结；没有记录时不调用模型
- **AI 角色对话**：按 `session_id` 隔离多轮会话，保留最近 10 条上下文；支持普通响应和流式响应
- **RAG 角色问答**：把角色档案切块、向量化后存入 ChromaDB，检索相关段落并注入用户长期记忆，普通接口还会返回命中的来源标题
- **用户长期记忆**：从问答内容中提取用户的长期信息（姓名、职业、喜好等），写入 `UserMemory`，后续问答时作为背景注入
- **流式输出**：`/chat/stream`、`/ask/stream` 以 `text/event-stream` 增量返回文本
- **工程能力**：依赖注入、CORS、超时/上游错误映射（504/502）、Alembic 迁移、pytest 测试

## 技术栈

| 层面 | 技术 | 用途 |
| --- | --- | --- |
| 语言 | Python 3.10+ | 代码使用 `int \| None`、`str \| None` 等新语法 |
| Web 框架 | FastAPI | 路由、依赖注入、CORS 中间件、`StreamingResponse`、`BackgroundTasks` |
| ASGI 服务器 | Uvicorn | 本地开发与生产运行 |
| 数据校验 | Pydantic | 请求/响应模型、`Literal`、`Field` 校验 |
| ORM / 模型 | SQLModel、SQLAlchemy | 表模型、`Session`、`select / where / order_by / limit` |
| 数据库 | MySQL 8（PyMySQL 驱动） | 生产数据存储 |
| 数据库（测试/本地回退） | SQLite | 未配置 `DATABASE_URL` 时的默认库；测试用 `tmp_path` 临时库 |
| 数据库迁移 | Alembic | 版本化管理表结构 |
| 对话模型 | DeepSeek API（OpenAI Python SDK） | 心情总结、角色对话、问题改写、记忆抽取 |
| Embedding | SiliconFlow `BAAI/bge-m3` | 角色文档与问题向量化 |
| Rerank | SiliconFlow `BAAI/bge-reranker-v2-m3` | 检索结果重排序 |
| 向量数据库 | ChromaDB（PersistentClient） | 角色知识库的本地持久化与相似度检索 |
| 配置管理 | python-dotenv | 从 `.env` 读取环境变量 |
| 测试 | pytest、Starlette `TestClient`、`monkeypatch` | 接口测试与外部调用隔离 |
| 数值计算 | NumPy | 余弦相似度工具函数 |
| 部署 | nssm + ngrok（Windows） | 注册 Windows 服务、内网穿透 |
| 前端 | 原生 HTML/CSS/JS 占位 | `frontend/` 目录，实际前端通过 CORS 调用接口 |

## 架构

```text
请求
  │
  ▼
Router（routers/）── 鉴权、参数校验、异常映射（401 / 404 / 422 / 502 / 504）
  │
  ▼
Service（services/）── 业务逻辑、提示词拼装、检索与生成编排
  │
  ├── SQLModel / SQLAlchemy ──▶ MySQL（生产）/ SQLite（测试）
  ├── DeepSeek API ──────────▶ 对话、总结、问题改写、记忆抽取
  ├── SiliconFlow API ───────▶ Embedding、Rerank
  └── ChromaDB ──────────────▶ 角色知识库向量检索
```

- `routers/` 只负责 HTTP 层：依赖注入数据库会话、校验 Token、把上游异常转换成 HTTP 状态码
- `services/` 承载业务逻辑，便于单独测试
- `models.py` 定义表结构，`schemas.py` 定义接口出入参，两者职责分离
- `ChatMessage` 同时保存 `/chat` 对话和 `/ask` 问答记录，以 `session_id` 关联
- `app/data/chunks.json` 是角色档案的切分结果，`app/scripts/split_test.py` 负责从 `character.md` 生成它

## 目录结构

```text
mood-journal/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI 实例、CORS、路由注册、自动建表
│   │   ├── deps.py                 # 数据库引擎、Session 依赖、Bearer Token 校验
│   │   ├── models.py               # MoodEntry / ChatMessage / UserMemory
│   │   ├── schemas.py              # 请求与响应模型
│   │   ├── llm.py                  # DeepSeek 客户端（普通 / 流式）
│   │   ├── siliconflow_llm.py      # SiliconFlow Embedding 客户端
│   │   ├── prompts.py              # 对话、总结、RAG 角色提示词
│   │   ├── routers/
│   │   │   ├── entries.py          # 心情记录接口
│   │   │   ├── chat.py             # AI 对话接口
│   │   │   └── rag.py              # RAG 问答接口
│   │   ├── services/
│   │   │   ├── service_entries.py  # 记录查询、统计、总结
│   │   │   ├── service_chat.py     # 多轮会话与流式对话
│   │   │   └── service_rag.py      # 问题改写、检索、重排、记忆
│   │   ├── data/
│   │   │   ├── character.md        # 角色设定原文
│   │   │   └── chunks.json         # 按二级标题切分的文档块
│   │   └── scripts/
│   │       └── split_test.py       # character.md -> chunks.json
│   ├── tests/                      # pytest 用例
│   ├── alembic/                    # 数据库迁移脚本
│   ├── alembic.ini
│   ├── requirements.txt            # 依赖清单（当前为空，见下方说明）
│   ├── .evn.example                # 环境变量样例
│   ├── body.json                   # /chat 调试请求体
│   └── body_stream.json            # /ask 调试请求体（需补 user_id）
└── frontend/
    ├── index.html                  # 静态页面占位
    ├── app.js
    └── style.css
```

## 快速开始

### 1. 环境要求

- Python 3.10+
- MySQL（推荐 8.0+；本地试用也可直接用 SQLite）
- DeepSeek API Key（对话、总结、问题改写、记忆抽取）
- SiliconFlow API Key（Embedding 与 Rerank）
- 可选：ngrok（需要公网访问时）

### 2. 安装依赖

```bash
git clone https://github.com/xxyyz3/mood-journal.git
cd mood-journal/backend

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

`requirements.txt` 目前为空，尚未锁定依赖版本。可先按代码实际使用到的包安装：

```bash
pip install fastapi "uvicorn[standard]" sqlmodel pymysql python-dotenv \
            openai requests numpy chromadb alembic pytest httpx
```

### 3. 配置环境变量

```bash
# 在 backend/ 目录下执行
cp .evn.example .env
```

然后按需修改 `.env`。样例文件未包含 SiliconFlow 相关变量，使用 RAG 功能时需额外补充：

```dotenv
DATABASE_URL=mysql+pymysql://root:your_password@127.0.0.1:3306/mood_journal?charset=utf8mb4
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
DB_ECHO=false
API_TOKEN=your-token-here
DEEPSEEK_API_KEY=sk-xxxx
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
SILICONFLOW_API_KEY=sk-xxxx
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1
```

只想在本地快速试用时，可以把 `DATABASE_URL` 改为 SQLite：

```dotenv
DATABASE_URL=sqlite:///./mood_journal.db
```

### 4. 初始化数据库

```bash
# 需要在 backend/ 目录下执行，alembic/env.py 会读取 DATABASE_URL
alembic upgrade head
```

说明：应用启动时还会执行 `SQLModel.metadata.create_all()`，自动补齐缺失的表（例如尚无迁移脚本的 `usermemory`）。生产环境仍建议以 Alembic 迁移为准。

### 5. 启动服务

```bash
# 后端使用 app.xxx 绝对导入，必须在 backend/ 目录下运行
uvicorn app.main:app --reload
```

- API 地址：`http://127.0.0.1:8000`
- Swagger 文档：`http://127.0.0.1:8000/docs`
- ReDoc：`http://127.0.0.1:8000/redoc`

首次启动时，ChromaDB 集合为空，程序会读取 `app/data/chunks.json` 中的 8 个文档块，调用 SiliconFlow Embedding 生成向量并写入 `backend/chroma_db/`。这一步需要有效的 `SILICONFLOW_API_KEY` 和网络；后续启动会直接复用已有集合。

### 6. 前端

`frontend/` 目前只是静态占位页面（`app.js`、`style.css` 为空），尚未接入接口。默认 CORS 允许 `http://localhost:5173` 和 `http://127.0.0.1:5173`，可在此基础上开发 Vite 前端，或修改 `CORS_ORIGINS` 适配自己的开发地址。

## 配置项

| 变量 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `DATABASE_URL` | 生产必填 | `sqlite:///./mood_journal.db` | SQLAlchemy 连接串。生产使用 `mysql+pymysql://用户:密码@主机:3306/库名?charset=utf8mb4`；Alembic 强制要求该变量存在 |
| `API_TOKEN` | 是 | 无 | 受保护接口的 Bearer Token。未配置时受保护接口返回 500 |
| `CORS_ORIGINS` | 否 | `http://localhost:5173,http://127.0.0.1:5173` | 允许的前端来源，逗号分隔 |
| `DB_ECHO` | 否 | `false` | 是否打印 SQL，开发时设为 `true` |
| `DEEPSEEK_API_KEY` | AI 功能必填 | 无 | DeepSeek API Key |
| `DEEPSEEK_BASE_URL` | AI 功能必填 | 无 | DeepSeek API 地址，例如 `https://api.deepseek.com` |
| `DEEPSEEK_MODEL` | 否 | `deepseek-chat` | 对话模型名 |
| `SILICONFLOW_API_KEY` | RAG 必填 | 无 | SiliconFlow API Key，用于 Embedding 和 Rerank |
| `SILICONFLOW_BASE_URL` | RAG 必填 | 无 | SiliconFlow OpenAI 兼容地址，例如 `https://api.siliconflow.cn/v1` |

> 注意：Rerank 请求地址在代码中固定为 `https://api.siliconflow.cn/v1/rerank`，不随 `SILICONFLOW_BASE_URL` 变化。
>
> 后端通过 `load_dotenv()` 读取当前工作目录下的 `.env`，因此请在 `backend/` 目录启动 uvicorn、pytest 和 Alembic。

## 接口说明

所有接口默认返回 JSON；`/health` 和 `/docs` 等文档路径无需鉴权。其余接口需在请求头携带：

```http
Authorization: Bearer <API_TOKEN>
```

鉴权使用 `secrets.compare_digest` 做常量时间比较。缺少或错误 Token 返回 `401`；服务端未配置 `API_TOKEN` 返回 `500`。

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

字段约束：`mood` 最长 20 字符，`content` 最长 200 字符。新增记录示例：

```bash
curl -X POST http://127.0.0.1:8000/entries \
  -H "Authorization: Bearer $API_TOKEN" \
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
| GET | `/chat/history?session_id=...` | 查询某个会话的历史消息 |

请求体：

```json
{"message": "今天好累", "session_id": "demo"}
```

- `message` 有默认值 `一句话介绍一下你自己`，`session_id` 必填
- 每次对话会读取该 `session_id` 下最近 10 条消息作为上下文
- 普通接口返回 `{"reply": "..."}`；上游超时返回 `504`，上游错误返回 `502`
- 历史接口返回 `id`、`role`、`content`、`created_at`，按时间升序，不返回 `session_id`
- 对话记录写入 `ChatMessage`，`role` 为 `user` 或 `assistant`

流式示例：

```bash
curl -N -X POST http://127.0.0.1:8000/chat/stream \
  -H "Authorization: Bearer $API_TOKEN" \
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
{"user_id": "u1", "question": "她住在哪里？", "session_id": "demo"}
```

`user_id`、`question`、`session_id` 均必填。普通接口返回：

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

1. **问题改写**：取同一 `session_id` 最近 5 条用户问题，让 DeepSeek 结合上下文把当前问题改写成更利于检索的关键词句
2. **向量化**：调用 SiliconFlow `BAAI/bge-m3` 生成问题向量
3. **向量召回**：ChromaDB 语义检索 `top_k=5`
4. **重排**：流式接口把召回的 5 个文档块交给 `BAAI/bge-reranker-v2-m3` 重排后取前 3；非流式接口直接使用召回的 5 个文档块
5. **生成**：把 `UserMemory` 中的用户背景和命中文档拼进提示词，要求模型只依据资料回答
6. **落库与记忆**：命中资料时把问答写入 `ChatMessage`；再用 DeepSeek 从对话中抽取用户长期信息，写入 `UserMemory`（`user_id` 维度）

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
| `chatmessage` | `id`、`role`、`content`、`created_at`、`session_id` | AI 对话与 RAG 问答记录，`created_at`、`session_id` 建索引 |
| `usermemory` | `id`、`user_id`、`fact_content`、`created_at` | 用户长期记忆，`user_id` 建索引 |

迁移命令（均在 `backend/` 目录下执行）：

```bash
alembic upgrade head                          # 升级到最新版本
alembic revision --autogenerate -m "描述"     # 根据模型改动生成迁移
alembic downgrade -1                          # 回滚一个版本
```

当前 Alembic 版本链覆盖 `moodentry` 和 `chatmessage` 的建表与 `note` 字段调整；`usermemory` 由启动时的 `create_all()` 创建，尚未生成对应迁移脚本。

## 测试

```bash
cd backend
API_TOKEN=test pytest -q
```

Windows PowerShell：

```powershell
$env:API_TOKEN = "test"
pytest -q
```

测试通过以下方式隔离外部依赖：

- `conftest.py` 用 `tmp_path` 创建临时 SQLite 库，并通过 `app.dependency_overrides` 替换 `get_session`
- 用 `monkeypatch` 替换 DeepSeek 调用，避免测试消耗真实额度
- 覆盖 `entries` 的 CRUD、过滤、统计、总结、404/422，`chat` 的历史、会话隔离、超时、流式错误，以及 RAG 的答案与空检索场景

注意：导入 `app.main` 时会初始化 ChromaDB，首次运行若没有现成的 `backend/chroma_db/`，仍会调用 SiliconFlow 生成向量，因此跑测试前也需要配置 `SILICONFLOW_API_KEY`。另外，RAG 用例尚未同步 `AskRequest` 的 `user_id` 字段，当前直接运行会因 422 参数校验失败。

## 部署

仓库不包含部署脚本，当前采用 Windows 单机部署：

- **进程管理**：用 [nssm](https://nssm.cc/) 把 `uvicorn app.main:app` 注册为 Windows 服务，开机自启
- **公网访问**：ngrok 将本机端口映射到公网，当前项目主页指向 ngrok 的 `/docs`
- **日志**：uvicorn 日志重定向到 `D:\logs\`，并配置自动切割
- **数据库**：本机 MySQL，连接串通过 `DATABASE_URL` 注入
- **配置**：生产 `.env` 中开启 `DB_ECHO=false`，设置强随机 `API_TOKEN`，并限制 `CORS_ORIGINS`

使用 Docker、Nginx 或云服务器部署时，可直接复用 `uvicorn` 的启动方式。

## 说明与限制

- `requirements.txt` 当前为空，依赖未锁定版本，部署前建议按实际环境补全
- 仓库尚未配置 CI，也没有 Dockerfile / compose 文件
- `/entries/stats`、`/entries/summary` 只处理 15 条记录
- 流式接口虽然声明 `text/event-stream`，但输出的是纯文本增量，不是标准 SSE 事件流
- Rerank 地址硬编码为 `https://api.siliconflow.cn/v1/rerank`，接入兼容代理时需要改代码
- `UserMemory` 目前只有写入和查询，没有独立的读取、修改或删除接口，也没有对应的 Alembic 迁移
- `frontend/` 为静态占位，仓库内没有可运行的前端应用
