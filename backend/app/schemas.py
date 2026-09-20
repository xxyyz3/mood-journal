from sqlmodel import SQLModel
from datetime import datetime
from pydantic import Field

class MoodEntryCreate(SQLModel):
    mood:str = Field(max_length=20)
    content:str = Field(max_length=200)

class MoodEntryRead(MoodEntryCreate):
    id:int
    created_at: datetime

