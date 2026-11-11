from datetime import datetime, timezone
from sqlmodel import SQLModel, Field

class MoodEntry(SQLModel,table=True):
    id:int|None = Field(default=None,primary_key=True)
    mood:str
    content:str
    created_at:datetime = Field(index=True,nullable=False,default_factory = lambda:datetime.now(timezone.utc))
    note: str | None = None

class ChatMessage(SQLModel,table=True):
    id:int|None = Field(default=None,primary_key=True)
    role: str
    content:str
    created_at:datetime = Field(index=True,nullable=False,default_factory = lambda:datetime.now(timezone.utc))
    session_id:str = Field(index=True)
    # 消息归属的用户（存 username），用于按用户隔离聊天历史。
    # 设为可空是为了兼容升级前已经存在、没有归属信息的老消息。
    user_id:str|None = Field(default=None,index=True)

class UserMemory(SQLModel,table=True):
    id:int|None = Field(default=None,primary_key=True)
    user_id:str = Field(index=True)
    fact_content:str
    created_at:datetime = Field(default_factory = lambda:datetime.now(timezone.utc))


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)  # 必须加主键！
    username: str = Field(index=True, unique=True)
    email: str | None = None
    full_name: str | None = None
    hashed_password: str
    disabled: bool | None = False
