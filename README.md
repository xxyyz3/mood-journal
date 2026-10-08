# Mood Journal Backend

一个心情记录系统的后端，提供增删查改和统计接口，部署在本机，通过 ngrok 暴露公网地址，支持前端跨域调用。


## 技术栈

**后端框架**
- FastAPI：路由、依赖注入、`StreamingResponse`、中间件、异常处理
- Pydantic：入参/出参校验，`Literal`、`Field`、`BaseModel`
- SQLModel：数据模型，`table=True`、查询、`session.exec`、`session.get`
- SQLAlchemy：底层 ORM，`select`、`order_by`、`where`、`limit`

**数据库**
- MySQL：生产数据存储
- SQLite：测试时的临时库，通过 `tmp_path` 隔离

**大模型**
- DeepSeek API（OpenAI 兼容）
- `openai` Python 包，`chat.completions.create`
- 单轮：`ask_deepseek_messages`
- 流式：`ask_deepseek_messages_stream`（`stream=True`）

## 数据库迁移

首次部署前初始化数据库表：
alembic upgrade head

修改 models 后：
alembic revision --autogenerate -m "描述"
# 打开生成的脚本检查
alembic upgrade head

回滚：
alembic downgrade -1

**测试**
- pytest
- `TestClient`
- `monkeypatch` 替换外部调用
- `conftest.py` + `dependency_overrides` 做测试隔离

**部署**
- nssm：把 uvicorn 注册成 Windows 服务，开机自启
- ngrok：内网穿透，公网访问
- 日志重定向到 `D:\logs\`，配自动切割
- `pydantic-settings`（了解层面，尚未接入）

**版本控制**
- Git + GitHub
- `git pull --rebase`、`git push`、分支管理

## 接口
除 /health 和 /docs 外，所有接口都需要在请求头带：
Authorization: Bearer <API_TOKEN>

**Entries**
| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /entries | 新增心情记录 |
| GET | /entries | 列表，可按 mood 过滤 |
| GET | /entries/{id} | 详情 |
| DELETE | /entries/{id} | 删除 |
| GET | /entries/stats | 统计，按 mood 分组计数 |
| GET | /entries/summary | 用模型总结最近的心情记录 |

**Chat**
| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /chat | AI 对话 |
| GET | /chat/history | AI 对话历史记录 |
| GET | /chat/stream | 流式输出 |

**Rag**
| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /ask | 基于角色档案的 RAG 问答 |


**Health**
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /health | 健康检查 |

## Changelog

### 0.02

**Added**
- 新增接口 `POST /chat`、`GET /chat/history`、`GET /chat/stream`
- 新增表 `ChatMessage`，用于存放对话记录
- 新增环境变量 `DEEPSEEK_API_KEY`、`DEEPSEEK_BASE_URL`、`DEEPSEEK_MODEL`
- 新增接口 `GET /entries/summary` 及依赖 `SummaryResponse`
- 新增封装函数 `ask_deepseek_messages_stream`
- 新增 `session_id` 字段到 `ChatMessage`表，`ChatRequest`入参
- 新增 `app/prompts.py`，`/chat` 使用 system 消息定义角色
- 新增测试：`test_chat`、`test_chat_history`、`test_timeout`、`test_chat_sessions_isolated`、`test_chat_stream_timeout`、`test_chat_stream_api_error`
- 新增 `ask` 接口：
- 数据源：`app/data/character.md`，切分后存入 `app/data/chunks.json`

 

**Changed**
- 更新 `/chat` 接口，支持多窗口会话
- 更新 `/chat` 相关测试函数，使用 `monkeypatch` 替换真实模型调用
- 重构 `/chat`和`/entries`接口，将service部分拆开放到了/services目录下
- 检索：`jieba 分词 + 命中率 >= 0.6`
- 无相关内容时不调模型，直接返回固定文案


**Fixed**
- 修复 `/chat/stream` 中捕获异常后数据未回滚的问题

## 本地运行

```bash
pip install -r requirements.txt
cp .env.example .env  # 按需修改 DATABASE_URL、CORS_ORIGINS
uvicorn app.main:app --reload
```

.env 里需要配置的变量：
- DATABASE_URL：MySQL 连接串
- CORS_ORIGINS：允许的前端来源，逗号分隔
- DB_ECHO：是否打印 SQL，开发时 true，生产 false
- API_TOKEN：接口鉴权用的 token
- DEEPSEEK_API_KEY：DeepSeek API key
- DEEPSEEK_BASE_URL：https://api.deepseek.com
- DEEPSEEK_MODEL：deepseek-chat

跑测试：
测试使用SQLite，不污染数据源
```bash
pytest
```
## 目录结构
```
backend/
  app/
    routers/
    services/
    models.py
    schemas.py
    deps.py
    llm.py
    prompts.py
    main.py
  tests/
  alembic/
```

