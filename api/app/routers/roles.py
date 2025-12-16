from typing import List

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select

from ..internal.models import Role, RoleCreate, RoleUpdate
from ..internal.dependencies import get_db_session

router = APIRouter(prefix="/api/roles", tags=["roles"])


@router.post("/", response_model=Role, status_code=201)
def create_role(
    role: RoleCreate, session: Session = Depends(get_db_session)
) -> Role:
    db_role = Role.from_orm(role)
    session.add(db_role)
    session.commit()
    session.refresh(db_role)
    return db_role


@router.get("/", response_model=List[Role])
def list_roles(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_db_session),
) -> List[Role]:
    roles = session.exec(select(Role).offset(skip).limit(limit)).all()
    return roles


@router.get("/{role_code}", response_model=Role)
def get_role(role_code: str, session: Session = Depends(get_db_session)) -> Role:
    role = session.get(Role, role_code)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return role


@router.put("/{role_code}", response_model=Role)
def update_role(
    role_code: str, role_update: RoleUpdate, session: Session = Depends(get_db_session)
) -> Role:
    role = session.get(Role, role_code)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    update_data = role_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(role, key, value)

    session.add(role)
    session.commit()
    session.refresh(role)
    return role


@router.delete("/{role_code}", status_code=204)
def delete_role(role_code: str, session: Session = Depends(get_db_session)) -> None:
    role = session.get(Role, role_code)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    session.delete(role)
    session.commit()
