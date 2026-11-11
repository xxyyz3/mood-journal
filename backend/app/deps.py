import os

from sqlalchemy import inspect, text
from sqlmodel import SQLModel, create_engine, Session
from typing import Generator
from dotenv import load_dotenv
from fastapi.security import OAuth2PasswordBearer

load_dotenv()
sqlite_url = os.getenv("DATABASE_URL", "sqlite:///./mood_journal.db")
echo = os.getenv("DB_ECHO", "false").lower() == "true"
engine = create_engine(sqlite_url, echo=echo)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    _ensure_chat_message_user_id()


def _ensure_chat_message_user_id():
    """给升级前的老库补上 chatmessage.user_id 列。

    create_all() 只会创建缺失的表，不会修改已存在的表，所以老数据库
    需要这一步兼容处理，否则新代码写入 user_id 时会报“未知列”。
    该函数是幂等的：列已存在时直接返回。
    """
    inspector = inspect(engine)
    if "chatmessage" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("chatmessage")}
    if "user_id" in columns:
        return

    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE chatmessage ADD COLUMN user_id VARCHAR(255)"))

    # 索引创建失败不影响主流程（例如数据库账号没有建索引权限）
    try:
        with engine.begin() as conn:
            conn.execute(
                text("CREATE INDEX ix_chatmessage_user_id ON chatmessage (user_id)")
            )
    except Exception:
        pass


def get_session() -> Generator[Session,None,None]:
    with Session(engine) as session:
        yield session