from typing import List
from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from ..internal.models import ListItem, ListItemBase
from ..internal.dependencies import get_db_session

router = APIRouter(prefix="/api/list_items", tags=["list_items"])

@router.post("/", response_model=ListItem, status_code=201)
def create_list_item(item_data: ListItemBase, session: Session = Depends(get_db_session)) -> ListItem:
    db_item = ListItem.from_orm(item_data)
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item

@router.get("/", response_model=List[ListItem])
def list_list_items(skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session)) -> List[ListItem]:
    items = session.exec(select(ListItem).offset(skip).limit(limit)).all()
    return items

@router.get("/{list_code}/{value}", response_model=ListItem)
def get_list_item(list_code: str, value: str, session: Session = Depends(get_db_session)) -> ListItem:
    item = session.exec(select(ListItem).where(ListItem.list == list_code, ListItem.value == value)).first()
    if not item:
        raise HTTPException(status_code=404, detail="List item not found")
    return item

@router.put("/{list_code}/{value}", response_model=ListItem)
def update_list_item(list_code: str, value: str, item_update: ListItemBase, session: Session = Depends(get_db_session)) -> ListItem:
    item = session.exec(select(ListItem).where(ListItem.list == list_code, ListItem.value == value)).first()
    if not item:
        raise HTTPException(status_code=404, detail="List item not found")

    update_data = item_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(item, key, value)

    session.add(item)
    session.commit()
    session.refresh(item)
    return item

@router.delete("/{list_code}/{value}", status_code=204)
def delete_list_item(list_code: str, value: str, session: Session = Depends(get_db_session)) -> None:
    item = session.exec(select(ListItem).where(ListItem.list == list_code, ListItem.value == value)).first()
    if not item:
        raise HTTPException(status_code=404, detail="List item not found")

    session.delete(item)
    session.commit()