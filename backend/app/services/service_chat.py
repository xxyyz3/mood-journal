from openai import APITimeoutError, APIError
from sqlmodel import Session
from sqlmodel import select

from app.models import ChatMessage
from app.prompts import CHAT_SYSTEM_PROMPT
from ..llm import ask_deepseek_messages, ask_deepseek_messages_stream


def messages_histories(session:Session, session_id:str, user_id:str|None=None):
    statement = select(ChatMessage).where(ChatMessage.session_id == session_id)
    # 传入 user_id 时只取当前用户的消息，防止不同用户复用 session_id 时串会话
    if user_id is not None:
        statement = statement.where(ChatMessage.user_id == user_id)

    recent = session.exec(
        statement.
        order_by(ChatMessage.created_at.desc()).limit(10)
    ).all()
    history = list(reversed(recent))
    return history


def build_messages(history:list[ChatMessage],user_message:str):
    messages = [{"role": "system", "content": CHAT_SYSTEM_PROMPT}]
    messages += [{"role": m.role, "content": m.content} for m in history]
    messages.append({"role": "user", "content": user_message})
    return messages


def handle_message(session:Session, user_message:str,session_id:str, user_id:str|None=None):
    history = messages_histories(session, session_id, user_id)
    messages = build_messages(history, user_message)
    user_msg = ChatMessage(role="user", content=user_message, session_id=session_id, user_id=user_id)
    session.add(user_msg)
    try:
        reply = ask_deepseek_messages(messages)
    except APITimeoutError:
        session.rollback()
        raise
    except APIError:
        session.rollback()
        raise
    ai_msg = ChatMessage(role="assistant", content=reply, session_id=session_id, user_id=user_id)
    session.add(ai_msg)
    session.commit()
    return reply


def handle_message_stream(session:Session, user_message:str,session_id:str, user_id:str|None=None):
    history = messages_histories(session, session_id, user_id)
    messages = build_messages(history, user_message)
    user_msg = ChatMessage(role="user", content=user_message, session_id=session_id, user_id=user_id)
    session.add(user_msg)

    full_reply = ""
    try:
        for piece in ask_deepseek_messages_stream(messages):
            if not piece:
                continue
            full_reply += piece
            yield piece
    except APITimeoutError:
        session.rollback()
        yield "[API响应超时]"
        return
    except APIError:
        session.rollback()
        yield "[API错误]"
        return
    ai_msg = ChatMessage(role="assistant", content=full_reply, session_id=session_id, user_id=user_id)
    session.add(ai_msg)
    session.commit()


def get_history(session:Session, session_id:str, user_id:str):
    """查询某个用户自己的会话历史，避免知道 session_id 就能读取别人的消息。"""
    return session.exec(
        select(ChatMessage).
        where(
            ChatMessage.session_id == session_id,
            ChatMessage.user_id == user_id,
        ).
        order_by(ChatMessage.created_at)
    ).all()


