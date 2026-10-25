from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from openai import APIError, APITimeoutError
from sqlmodel import Session
from fastapi.responses import StreamingResponse

from .. import deps
from ..deps import verify_token
from ..schemas import AskRequest, AskResponse
from ..services.service_rag import ask, ask_stream

router = APIRouter(prefix="/ask",tags=["ask"])

@router.post("")
def about_her(
    # token: Annotated[str, Depends(verify_token)],
    req:AskRequest,
    session:Session = Depends(deps.get_session),
):
    try:
        answer = ask(req.question, session, req.session_id)
    except APITimeoutError:
        raise HTTPException(status_code=504, detail="响应超时")
    except APIError as err:
        raise HTTPException(status_code=502, detail=f"API调用失败: {err}")
    return AskResponse(answer = answer["answer"],sources = answer["sources"])

@router.post("/stream")
def about_her_stream(
    token: Annotated[str, Depends(verify_token)],
    req:AskRequest,
    session:Session = Depends(deps.get_session),
):
    return StreamingResponse(
        ask_stream(req.question, session, req.session_id),
        media_type="test/event-stream"
    )
