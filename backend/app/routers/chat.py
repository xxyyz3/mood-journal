from fastapi import APIRouter, Depends, HTTPException
from openai import APITimeoutError, APIError
from sqlmodel import Session, select

from .. import deps
from ..llm import ask_deepseek
from ..models import ChatMessage
from ..schemas import ChatRequest, ChatResponse, ChatMessageRead

router = APIRouter(prefix="/chat",tags=["chat"])

@router.post("", response_model=ChatResponse)
def chat_with_deepseek(req: ChatRequest, session: Session = Depends(deps.get_session)):
    user_msg = ChatMessage(role = "user",content = req.message)
    session.add(user_msg)

    try:
        reply = ask_deepseek(req.message)
    except APITimeoutError:
        session.rollback()
        raise HTTPException(status_code=504,detail="响应超时，请稍后尝试")
    except APIError as err:
        session.rollback()
        raise HTTPException(status_code=502,detail=f"API调用失败: {err}")
    ai_msg = ChatMessage(role = "assistant",content = reply)
    session.add(ai_msg)
    session.commit()
    return ChatResponse(reply=reply)

@router.get("/history",response_model=list[ChatMessageRead])
def chat_history(session: Session = Depends(deps.get_session)):
    return session.exec(
        select(ChatMessage).order_by(ChatMessage.created_at)
    ).all()