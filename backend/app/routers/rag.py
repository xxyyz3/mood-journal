from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from openai import APIError, APITimeoutError

from ..deps import verify_token
from ..schemas import AskRequest, AskResponse
from ..services.service_rag  import ask

router = APIRouter(prefix="/ask",tags=["ask"])

@router.post("")
def about_her(
    token: Annotated[str, Depends(verify_token)],
    req:AskRequest,
):
    try:
        answer = ask(req.question)
    except APITimeoutError:
        raise HTTPException(status_code=504, detail="响应超时")
    except APIError as err:
        raise HTTPException(status_code=502, detail=f"API调用失败: {err}")
    return AskResponse(answer = answer)

