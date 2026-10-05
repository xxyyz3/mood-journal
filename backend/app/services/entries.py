from fastapi import Depends
from openai import APITimeoutError, APIError
from sqlmodel import Session, select

from app.llm import ask_deepseek_messages
from app import deps
from app.models import MoodEntry
from app.prompts import SUMMARY_SYSTEM_PROMPT
from app.schemas import SummaryResponse


def messages_histories(
        session: Session
):
    # 拿到最近的15条心情记录
    recent = session.exec(select(MoodEntry).order_by(MoodEntry.created_at.desc()).limit(15)).all()
    messages = list(reversed(recent))
    return messages


def to_str(messages:list[MoodEntry]):
    prompt = SUMMARY_SYSTEM_PROMPT
    # 将messages转换为字符串
    all_txt = ""
    for m in messages:
        record_txt = f"{m.created_at.strftime('%Y-%m-%d')}  {m.mood}: {m.content}\n"
        all_txt += f"{record_txt}"

    return [
        {"role": "system", "content": prompt},
        {"role": "user", "content": all_txt}
    ]


def handle_messages(session: Session):
    messages = messages_histories(session)
    if not messages:
        return "还没有心情记录喵~"
    summary = to_str(messages)
    try:
        reply = ask_deepseek_messages(summary)
    except APITimeoutError:
        raise
    except APIError:
        raise
    return reply

def messages_summary(session: Session,mood:str):
    statement = select(MoodEntry)
    if mood is not None:
        statement = statement.where(MoodEntry.mood == mood)
    entries = session.exec(statement.limit(15)).all()
    return entries

def handle_messages_summary(session: Session,mood:str):
    entries = messages_summary(session,mood)
    total = len(entries)
    by_mood = {}
    for entry in entries:
        by_mood[entry.mood] = by_mood.get(entry.mood, 0) + 1
    by_mood = {k: v for k, v in by_mood.items() if v > 0}
    by_mood = dict(sorted(by_mood.items(), key=lambda item: item[1], reverse=True))
    return {"total":total, "by_mood":by_mood}