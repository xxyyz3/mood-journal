from fastapi import Depends, APIRouter, HTTPException
from sqlmodel import Session, select

from .. import deps
from ..models import MoodEntry
from ..schemas import MoodEntryRead, MoodEntryCreate


router = APIRouter(prefix="/entries",tags=["entries"] )


@router.get("/stats",summary="Get mood statistics")
async def read_stats(mood:str|None = None,session: Session = Depends(deps.get_session)):
    statement = select(MoodEntry)
    if mood is not None:
        statement = statement.where(MoodEntry.mood == mood)
    entries = session.exec(statement).all()
    total = len(entries)
    by_mood = {}
    for entry in entries:
        by_mood[entry.mood] = by_mood.get(entry.mood, 0) + 1

    by_mood = {k: v for k, v in by_mood.items() if v > 0}
    by_mood = dict(sorted(by_mood.items(), key=lambda item: item[1], reverse=True))

    return {"total":total,"by_mood":by_mood}



@router.post("",response_model=MoodEntryRead)
async def create_entry(entry_in:MoodEntryCreate,session: Session = Depends(deps.get_session)):
    db_entry = MoodEntry(**entry_in.model_dump())
    session.add(db_entry)
    session.commit()
    session.refresh(db_entry)
    return db_entry

@router.get("")
async def read_entries(mood:str|None = None,session:Session = Depends(deps.get_session)):
  # 要查找的表
  statement = select(MoodEntry)

  # 判断查找对象是否存在
  if mood is not None:
      statement = statement.where(MoodEntry.mood == mood)

  #返回查找对象的全部值
  return session.exec(statement).all()

@router.get("/{entry_id}",response_model=MoodEntryRead)
async def read_entry(entry_id:int,session: Session = Depends(deps.get_session)):
    db_entry = session.get(MoodEntry, entry_id)
    if not db_entry:
        raise HTTPException(status_code=404, detail="Not Found")
    return db_entry


@router.delete("/{entry_id}",status_code=204)
async def delete_entry(entry_id:int,session: Session = Depends(deps.get_session)):
    db_entry = session.get(MoodEntry, entry_id)
    if not db_entry:
        raise HTTPException(status_code=404, detail="Not Found")
    session.delete(db_entry)
    session.commit()


