from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from openai import APITimeoutError, APIError
from sqlmodel import Session, select
from fastapi.responses import StreamingResponse

from .. import deps
from ..deps import verify_token
from ..models import ChatMessage
from ..schemas import ChatRequest, ChatResponse, ChatMessageRead
from ..services.chat import handle_message, handle_message_stream

router = APIRouter(prefix="/chat",tags=["chat"])

@router.post("", response_model=ChatResponse)
def chat_with_deepseek(
        token: Annotated[str, Depends(verify_token)],
        req: ChatRequest,
        session: Session = Depends(deps.get_session),
):
    try:
        reply = handle_message(session, req.message, req.session_id)
    except APITimeoutError:
        session.rollback()
        raise HTTPException(status_code=504, detail="响应超时，请稍后尝试")
    except APIError as err:
        session.rollback()
        raise HTTPException(status_code=502, detail=f"API调用失败: {err}")

    return ChatResponse(reply=reply)


@router.get("/history",response_model=list[ChatMessageRead])
def chat_history(
        token: Annotated[str, Depends(verify_token)],
        session_id:str,
        session: Session = Depends(deps.get_session)
):
    return session.exec(
        select(ChatMessage).
        where(ChatMessage.session_id == session_id).
        order_by(ChatMessage.created_at)
    ).all()


@router.post("/stream")
def chat_stream(
        token: Annotated[str, Depends(verify_token)],
        req: ChatRequest,
        session: Session = Depends(deps.get_session)
):
    def event_generator():
        yield from handle_message_stream(session, req.message, req.session_id)
    return StreamingResponse(event_generator(),media_type="text/event-stream")







