from typing import List
from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from ..internal.models import List as ListModel, ListBase
from ..internal.dependencies import get_db_session

router = APIRouter(prefix="/api/lists", tags=["lists"])

@router.post("/", response_model=ListModel, status_code=201)
def create_list(list_data: ListBase, session: Session = Depends(get_db_session)) -> ListModel:
    db_list = ListModel.from_orm(list_data)
    session.add(db_list)
    session.commit()
    session.refresh(db_list)
    return db_list

@router.get("/", response_model=List[ListModel])
def list_lists(skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session)) -> List[ListModel]:
    lists = session.exec(select(ListModel).offset(skip).limit(limit)).all()
    return lists

@router.get("/{list_code}", response_model=ListModel)
def get_list(list_code: str, session: Session = Depends(get_db_session)) -> ListModel:
    list_item = session.get(ListModel, list_code)
    if not list_item:
        raise HTTPException(status_code=404, detail="List not found")
    return list_item

@router.put("/{list_code}", response_model=ListModel)
def update_list(list_code: str, list_update: ListBase, session: Session = Depends(get_db_session)) -> ListModel:
    list_item = session.get(ListModel, list_code)
    if not list_item:
        raise HTTPException(status_code=404, detail="List not found")

    update_data = list_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(list_item, key, value)

    session.add(list_item)
    session.commit()
    session.refresh(list_item)
    return list_item

@router.delete("/{list_code}", status_code=204)
def delete_list(list_code: str, session: Session = Depends(get_db_session)) -> None:
    list_item = session.get(ListModel, list_code)
    if not list_item:
        raise HTTPException(status_code=404, detail="List not found")

    session.delete(list_item)
    session.commit()