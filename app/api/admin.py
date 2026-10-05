import sqlite3
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from app.core.deps import CurrentUser, require_role
from app.core.security import hash_password
from app.db.hr import get_hr_repo
from app.services.audit import list_audit
from app.db.users import ROLES, create_user, get_user_by_id, list_users, set_active, set_password_hash

router = APIRouter(prefix="/api/admin", tags=["admin"])

admin_only = require_role("admin")


class NewUser(BaseModel):
    employee_id: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=1, max_length=256)
    role: str = "employee"


class ActiveFlag(BaseModel):
    active: bool


class NewPassword(BaseModel):
    password: str = Field(min_length=1, max_length=256)


def _public(user) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "employee_id": user.employee_id,
        "active": user.active,
    }


def _hash_or_400(password: str) -> str:
    try:
        return hash_password(password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/audit")
def audit(limit: int = 100, blocked_only: bool = False, _: CurrentUser = Depends(require_role("hr", "admin"))):
    return list_audit(limit=max(1, min(limit, 500)), blocked_only=blocked_only)


@router.get("/users")
def users(_: CurrentUser = Depends(admin_only)):
    return [_public(u) for u in list_users()]


@router.post("/users", status_code=201)
def add_user(payload: NewUser, _: CurrentUser = Depends(admin_only)):
    if payload.role not in ROLES:
        raise HTTPException(status_code=400, detail=f"Role must be one of: {', '.join(ROLES)}")
    # The email always comes from the HR record, so an account can't be tied to the wrong employee.
    employee = get_hr_repo().get_employee(payload.employee_id)
    if employee is None:
        raise HTTPException(status_code=404, detail="No such employee in the HR database")
    try:
        user = create_user(employee["email"], _hash_or_400(payload.password), payload.role, payload.employee_id)
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="This employee already has an account") from exc
    return _public(user)


@router.patch("/users/{user_id}/active")
def set_user_active(user_id: int, payload: ActiveFlag, admin: CurrentUser = Depends(admin_only)):
    if get_user_by_id(user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user_id == admin.id and not payload.active:
        raise HTTPException(status_code=400, detail="You cannot disable your own account")
    set_active(user_id, payload.active)
    return _public(get_user_by_id(user_id))


@router.post("/users/{user_id}/password")
def reset_password(user_id: int, payload: NewPassword, _: CurrentUser = Depends(admin_only)):
    if get_user_by_id(user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")
    set_password_hash(user_id, _hash_or_400(payload.password))
    return {"message": "Password updated"}
