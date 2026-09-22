# Mood Journal Backend

一个心情记录系统的后端，提供增删查改和统计接口，部署在本机，
通过 ngrok 暴露公网地址，支持前端跨域调用。

## 技术栈

- FastAPI：Web 框架
- SQLModel + MySQL：数据模型和数据库
- pytest：单元测试，每个测试使用独立临时数据库
- nssm + ngrok：Windows 服务常驻 + 公网穿透

## 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /entries | 新增心情记录 |
| GET | /entries | 列表，可按 mood 过滤 |
| GET | /entries/{id} | 详情 |
| DELETE | /entries/{id} | 删除 |
| GET | /entries/stats | 统计，按 mood 分组计数 |
| GET | /health | 健康检查 |
| POST | /chat  | AI对话   |
| GET  | /chat/history | AI对话历史记录 |




## 0.02 新增内容
- 新增了接口post/get /chat------AI对话
- 新增了表ChatMessage----用于存放对话记录
- 新增了环境变量DEEPSEEK_API_KEY，DEEPSEEK_BASE_URL，DEEPSEEK_MODEL
- 新增了测试test_chat，test_chat_history，test_timeout，测试里用monkeypeach替换真实数据模型调用


## 本地运行

```bash
pip install -r requirements.txt
cp .env.example .env  # 按需修改 DATABASE_URL、CORS_ORIGINS
uvicorn app.main:app --reload
