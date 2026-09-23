from datetime import datetime, timezone
from sqlmodel import SQLModel, Field

class MoodEntry(SQLModel,table=True):
    id:int|None = Field(default=None,primary_key=True)
    mood:str
    content:str
    created_at:datetime = Field(index=True,nullable=False,default_factory = lambda:datetime.now(timezone.utc))

class ChatMessage(SQLModel,table=True):
    id:int|None = Field(default=None,primary_key=True)
    role: str
    content:str
    created_at:datetime = Field(index=True,nullable=False,default_factory = lambda:datetime.now(timezone.utc))
    session_id:str = Field(index=True)
