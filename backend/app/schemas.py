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
