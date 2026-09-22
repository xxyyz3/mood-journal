from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

from .routers import entries, chat
from .deps import create_db_and_tables

load_dotenv()
app = FastAPI()

origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(entries.router)
app.include_router(chat.router)
create_db_and_tables()

@app.get("/health")
async def root():
    return {"status": "ok"}


