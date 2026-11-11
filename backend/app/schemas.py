from sqlmodel import SQLModel
from datetime import datetime
from pydantic import Field
from pydantic import BaseModel
from typing import Literal

class MoodEntryCreate(SQLModel):
    mood:str = Field(max_length=20)
    content:str = Field(max_length=200)

class MoodEntryRead(MoodEntryCreate):
    id:int
    created_at: datetime

class ChatRequest(BaseModel):
    message: str = "一句话介绍一下你自己"
    session_id: str

class ChatResponse(BaseModel):
    reply:str

class ChatMessageCreate(ChatRequest):
    role:Literal["user","assistant"]
    content:str

class ChatMessageRead(BaseModel):
    id: int
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime

class SummaryResponse(BaseModel):
    summary:str

class AskResponse(BaseModel):
    answer:str
    sources:list[str]

class AskRequest(BaseModel):
    # 已废弃：服务端一律以 JWT 中的当前用户为准，此字段仅为兼容旧客户端而保留
    user_id: str | None = Field(
        default=None,
        description="已废弃：服务端以 JWT 当前用户为准，此字段会被忽略",
    )
    question:str
    session_id:str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str | None = None
