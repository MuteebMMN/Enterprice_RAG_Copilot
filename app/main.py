from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.api.routes import router
from app.api.auth import router as auth_router
from app.api.admin import router as admin_router
from app.core.config import get_settings, BASE_DIR
from app.core.deps import CurrentUser, get_current_user
from app.core.logging import configure_logging
from app.db.hr import get_hr_repo
from app.db.users import get_user_by_email, init_users_db
from app.services.audit import init_db


configure_logging()
settings = get_settings()
init_db()
init_users_db()


app = FastAPI(title=settings.app_name, version="1.0.0")

app.include_router(router)
app.include_router(auth_router)
app.include_router(admin_router)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def current_user_or_none(request: Request) -> CurrentUser | None:
    try:
        return get_current_user(request)
    except HTTPException:
        return None


def profile(user: CurrentUser) -> dict:
    employee = get_hr_repo().get_employee(user.employee_id) or {}
    return {
        "name": employee.get("name", user.email),
        "email": user.email,
        "role": user.role,
        "department": employee.get("department", ""),
    }


def demo_profile() -> dict | None:
    """Details for the 'Continue as demo user' button, or None when demo login is off."""
    if not settings.demo_email:
        return None
    user = get_user_by_email(settings.demo_email)
    if user is None or not user.active or user.role != "employee":
        return None
    return profile(CurrentUser(id=user.id, email=user.email, role=user.role, employee_id=user.employee_id))


def page(request: Request, template: str, **context):
    # no-store: after logout, the browser's back button must not show a cached private page
    response = templates.TemplateResponse(
        template, {"request": request, "app_name": settings.app_name, **context}
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    user = current_user_or_none(request)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    return page(request, "index.html", user=profile(user))


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if current_user_or_none(request) is not None:
        return RedirectResponse("/", status_code=303)
    return page(request, "login.html", demo=demo_profile())


@app.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request):
    user = current_user_or_none(request)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    if user.role not in ("hr", "admin"):
        return RedirectResponse("/", status_code=303)
    return page(request, "admin.html", user=profile(user))
