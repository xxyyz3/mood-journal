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
- 新增 `session_id` 字段到 `ChatResponse`
- 新增 `app/prompts.py`，`/chat` 使用 system 消息定义角色
- 新增测试：`test_chat`、`test_chat_history`、`test_timeout`、`test_chat_sessions_isolated`、`test_chat_stream_timeout`、`test_chat_stream_api_error`

**Changed**
- 更新 `/chat` 接口，支持多窗口会话
- 更新 `/chat` 相关测试函数，使用 `monkeypatch` 替换真实模型调用

**Fixed**
- 修复 `/chat/stream` 中捕获异常后数据未回滚的问题

## 本地运行

```bash
pip install -r requirements.txt
cp .env.example .env  # 按需修改 DATABASE_URL、CORS_ORIGINS
uvicorn app.main:app --reload
```

跑测试：

```bash
pytest
```

---

如果你愿意，我下一轮可以只做一件事：**帮你把这份 README 里的“技术栈”和“Changelog”压缩成 GitHub 首页 30 秒能读完的版本**，现在这份偏“开发日志”，放仓库里合适，放首页略长。
