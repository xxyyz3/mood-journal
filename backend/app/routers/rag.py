from typing import Annotated
from fastapi import BackgroundTasks
from fastapi import APIRouter, Depends, HTTPException
from openai import APIError, APITimeoutError
from sqlmodel import Session
from fastapi.responses import StreamingResponse

from .. import deps
from ..services.service_auth import get_current_user
from ..models import User
from ..schemas import AskRequest, AskResponse
from ..services.service_rag import ask, ask_stream

router = APIRouter(prefix="/ask",tags=["ask"])

@router.post("")
def about_her(
    current_user: Annotated[User, Depends(get_current_user)],
    req:AskRequest,
    session:Session = Depends(deps.get_session),
):
    try:
        # 用户身份以 JWT 为准；req.user_id 即使传了也会被忽略，防止读取/写入他人记忆
        answer = ask(req.question, session, req.session_id, current_user.username)
    except APITimeoutError:
        raise HTTPException(status_code=504, detail="响应超时")
    except APIError as err:
        raise HTTPException(status_code=502, detail=f"API调用失败: {err}")
    return AskResponse(answer = answer["answer"],sources = answer["sources"])


@router.post("/stream")
def about_her_stream(
    current_user: Annotated[User, Depends(get_current_user)],
    background_tasks: BackgroundTasks,
    req:AskRequest,
    session:Session = Depends(deps.get_session),
):
    return StreamingResponse(
        # 同样使用 JWT 中的用户身份，忽略请求体里的 user_id
        ask_stream(
            req.question,
            session,
            req.session_id,
            current_user.username,
            background_tasks,
        ),
        media_type="text/event-stream"
    )
