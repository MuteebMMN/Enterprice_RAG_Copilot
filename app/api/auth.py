from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from app.core.config import get_settings
from app.core.deps import CurrentUser, get_current_user
from app.core.security import COOKIE_NAME, DUMMY_HASH, create_access_token, verify_password
from app.db.hr import get_hr_repo
from app.db.users import (
    get_user_by_email,
    is_locked,
    register_failed_login,
    register_successful_login,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()

INVALID_LOGIN = "Invalid email or password"


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)


@router.post("/login")
def login(payload: LoginRequest, response: Response):
    user = get_user_by_email(payload.email)

    if user is None:
        verify_password(payload.password, DUMMY_HASH)  # same cost as a real check
        raise HTTPException(status_code=401, detail=INVALID_LOGIN)

    if is_locked(user):
        raise HTTPException(status_code=429, detail="Too many failed attempts. Try again later.")

    if not verify_password(payload.password, user.password_hash):
        register_failed_login(user.id)
        raise HTTPException(status_code=401, detail=INVALID_LOGIN)

    if not user.active:
        raise HTTPException(status_code=401, detail=INVALID_LOGIN)

    register_successful_login(user.id)
    response.set_cookie(
        COOKIE_NAME,
        create_access_token(user.id, user.role),
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        max_age=settings.jwt_expire_minutes * 60,
        path="/",
    )
    return {"message": "Logged in"}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"message": "Logged out"}


@router.get("/me")
def me(user: CurrentUser = Depends(get_current_user)):
    employee = get_hr_repo().get_employee(user.employee_id) or {}
    return {
        "email": user.email,
        "role": user.role,
        "employee_id": user.employee_id,
        "name": employee.get("name", user.email),
        "department": employee.get("department"),
    }
