from typing import Annotated
from fastapi import Depends, APIRouter, HTTPException
from openai import APITimeoutError, APIError
from sqlmodel import Session, select

from .. import deps
from ..deps import verify_token
from ..models import MoodEntry
from ..schemas import MoodEntryRead, MoodEntryCreate, SummaryResponse
from ..services.service_entries import handle_messages, handle_messages_summary

router = APIRouter(prefix="/entries",tags=["entries"] )


@router.get("/summary",response_model=SummaryResponse)
def entries_summary(
        token: Annotated[str, Depends(verify_token)],
        session: Session = Depends(deps.get_session)
):
    try:
        reply = handle_messages(session)
    except APITimeoutError:
        raise HTTPException(status_code=504,detail="响应超时，请稍后尝试")
    except APIError as err:
        raise HTTPException(status_code=502,detail=f"API调用失败: {err}")
    return SummaryResponse(summary=reply)


@router.get("/stats",summary="Get mood statistics")
async def read_stats(
        token: Annotated[str, Depends(verify_token)],
        mood:str|None = None,
        session: Session = Depends(deps.get_session)
):
    return handle_messages_summary(session,mood)


@router.post("",response_model=MoodEntryRead)
async def create_entry(
        token: Annotated[str, Depends(verify_token)],
        entry_in:MoodEntryCreate,
        session: Session = Depends(deps.get_session)
):
    db_entry = MoodEntry(**entry_in.model_dump())
    session.add(db_entry)
    session.commit()
    session.refresh(db_entry)
    return db_entry

@router.get("")
async def read_entries(
        token: Annotated[str, Depends(verify_token)],
        mood:str|None = None,
        session:Session = Depends(deps.get_session)
):
  # 要查找的表
  statement = select(MoodEntry)

  # 判断查找对象是否存在
  if mood is not None:
      statement = statement.where(MoodEntry.mood == mood)

  #返回查找对象的全部值
  return session.exec(statement).all()

@router.get("/{entry_id}",response_model=MoodEntryRead)
async def read_entry(
        token: Annotated[str, Depends(verify_token)],
        entry_id:int,
        session: Session = Depends(deps.get_session)
):
    db_entry = session.get(MoodEntry, entry_id)
    if not db_entry:
        raise HTTPException(status_code=404, detail="Not Found")
    return db_entry


@router.delete("/{entry_id}",status_code=204)
async def delete_entry(
        token: Annotated[str, Depends(verify_token)],
        entry_id:int,
        session: Session = Depends(deps.get_session)
):
    db_entry = session.get(MoodEntry, entry_id)
    if not db_entry:
        raise HTTPException(status_code=404, detail="Not Found")
    session.delete(db_entry)
    session.commit()

