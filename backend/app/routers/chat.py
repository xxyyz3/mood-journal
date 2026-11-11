from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from openai import APITimeoutError, APIError
from sqlmodel import Session
from fastapi.responses import StreamingResponse

from .. import deps
from ..services.service_auth import get_current_user
from ..models import User
from ..schemas import ChatRequest, ChatResponse, ChatMessageRead
from ..services.service_chat import get_history, handle_message, handle_message_stream

router = APIRouter(prefix="/chat",tags=["chat"])

@router.post("", response_model=ChatResponse)
def chat_with_deepseek(
        current_user: Annotated[User, Depends(get_current_user)],
        req: ChatRequest,
        session: Session = Depends(deps.get_session),
):
    try:
        # 用户身份以 JWT 为准，不能由请求体决定
        reply = handle_message(session, req.message, req.session_id, current_user.username)
    except APITimeoutError:
        session.rollback()
        raise HTTPException(status_code=504, detail="响应超时，请稍后尝试")
    except APIError as err:
        session.rollback()
        raise HTTPException(status_code=502, detail=f"API调用失败: {err}")

    return ChatResponse(reply=reply)


@router.get("/history",response_model=list[ChatMessageRead])
def chat_history(
        current_user: Annotated[User, Depends(get_current_user)],
        session_id:str,
        session: Session = Depends(deps.get_session)
):
    # 只返回当前登录用户自己的消息
    return get_history(session, session_id, current_user.username)


@router.post("/stream")
def chat_stream(
        current_user: Annotated[User, Depends(get_current_user)],
        req: ChatRequest,
        session: Session = Depends(deps.get_session)
):
    def event_generator():
        yield from handle_message_stream(
            session, req.message, req.session_id, current_user.username
        )
    return StreamingResponse(event_generator(),media_type="text/event-stream")








