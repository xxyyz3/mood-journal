# Mood Journal Backend

一个心情记录系统的后端，提供增删查改和统计接口，部署在本机，
通过 ngrok 暴露公网地址，支持前端跨域调用。

## 技术栈

**后端框架**
- FastAPI：路由、依赖注入、`StreamingResponse`、中间件、异常处理
- Pydantic：入参/出参校验，`Literal`、`Field`、`BaseModel`
- SQLModel：数据模型，`table=True`、查询、`session.exec`、`session.get`
- SQLAlchemy：底层 ORM，`select`、`order_by`、`where`、`limit`

- 
**数据库**
- MySQL：生产数据存储
- SQLite：测试时的临时库，通过 `tmp_path` 隔离


**大模型**
- DeepSeek API（OpenAI 兼容）
- `openai` Python 包，`chat.completions.create`
- 单轮：`ask_deepseek_messages`
- 流式：`ask_deepseek_messages_stream`（`stream=True`）


## 接口

| 方法     | 路径 | 说明 |
|--------|---|---|
| POST   | /entries | 新增心情记录 |
| GET    | /entries | 列表，可按 mood 过滤 |
| GET    | /entries/{id} | 详情 |
| DELETE | /entries/{id} | 删除 |
| GET    | /entries/stats | 统计，按 mood 分组计数 |
| GET    | /health | 健康检查 |
| POST   | /chat  | AI对话   |
| GET    | /chat/history | AI对话历史记录 |
| GET    | /entries/summary | 用模型总结最近的心情记录 |
| GET    | /chat/stream   | 流式输出 |


## 0.02 新增内容
- 新增了接口post/get /chat------AI对话
- 新增了表ChatMessage----用于存放对话记录
- 新增了环境变量DEEPSEEK_API_KEY，DEEPSEEK_BASE_URL，DEEPSEEK_MODEL
- 新增了测试test_chat，test_chat_history，test_timeout，测试里用monkeypeach替换真实数据模型调用
- 新增了接口entries/summary 和 依赖SummaryResponse
- 新增了接口chat/stream
- 新增了封装LLM函数ask_deepseek_messages_stream
- 更新了根目录/chat下的接口，支持多窗口会话
- 更新了根目录/chat下的测试函数
- 新增了测试test_chat_sessions_isolated，test_chat_stream_timeout
- 新增了session_id字段在依赖ChatResponse中
- 新增了提示词集中到 app/prompts.py，/chat 使用 system 消息定义角色
- 新增了测试接口test_chat_stream_api_error
- 修复了接口/chat/stream中捕获异常数据没有回滚的问题


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


## 本地运行

```bash
pip install -r requirements.txt
cp .env.example .env  # 按需修改 DATABASE_URL、CORS_ORIGINS
uvicorn app.main:app --reload
