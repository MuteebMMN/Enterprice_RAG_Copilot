from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel
from app.core.security import COOKIE_NAME, decode_access_token
from app.db.users import get_user_by_id


class CurrentUser(BaseModel):
    """The verified identity behind a request. Never built from anything the client types."""
    id: int
    email: str
    role: str
    employee_id: str


def get_current_user(request: Request) -> CurrentUser:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.lower().startswith("bearer "):
            token = auth[7:].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Session expired or invalid")

    # Load the user fresh on every request so disabled accounts and role changes apply immediately.
    user = get_user_by_id(int(payload["sub"]))
    if user is None or not user.active:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return CurrentUser(id=user.id, email=user.email, role=user.role, employee_id=user.employee_id)


def require_role(*roles: str):
    def checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="You do not have permission to do this")
        return user

    return checker
