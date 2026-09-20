import os
from sqlmodel import SQLModel, create_engine, Session
from typing import Generator
from dotenv import load_dotenv

load_dotenv()
sqlite_url = os.getenv("DATABASE_URL", "sqlite:///./mood_journal.db")
echo = os.getenv("DB_ECHO", "false").lower() == "true"
engine = create_engine(sqlite_url, echo=echo)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session() -> Generator[Session,None,None]:
    with Session(engine) as session:
        yield session