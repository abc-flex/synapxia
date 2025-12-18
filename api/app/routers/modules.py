from typing import List
from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from ..internal.models import Module, ModuleBase
from ..internal.dependencies import get_db_session

router = APIRouter(prefix="/api/modules", tags=["modules"])

@router.post("/", response_model=Module, status_code=201)
def create_module(module: ModuleBase, session: Session = Depends(get_db_session)) -> Module:
    db_module = Module.from_orm(module)
    session.add(db_module)
    session.commit()
    session.refresh(db_module)
    return db_module

@router.get("/", response_model=List[Module])
def list_modules(skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session)) -> List[Module]:
    modules = session.exec(select(Module).offset(skip).limit(limit)).all()
    return modules

@router.get("/{module_code}", response_model=Module)
def get_module(module_code: str, session: Session = Depends(get_db_session)) -> Module:
    module = session.get(Module, module_code)
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    return module

@router.put("/{module_code}", response_model=Module)
def update_module(module_code: str, module_update: ModuleBase, session: Session = Depends(get_db_session)) -> Module:
    module = session.get(Module, module_code)
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    update_data = module_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(module, key, value)

    session.add(module)
    session.commit()
    session.refresh(module)
    return module

@router.delete("/{module_code}", status_code=204)
def delete_module(module_code: str, session: Session = Depends(get_db_session)) -> None:
    module = session.get(Module, module_code)
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    session.delete(module)
    session.commit()