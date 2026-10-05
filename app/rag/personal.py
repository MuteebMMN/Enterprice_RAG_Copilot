"""Read-only access to the *asking user's own* HR record.

SECURITY: nothing in this module accepts an employee id from the question or from the
LLM. Every lookup uses `user.employee_id`, which comes from the verified login. The LLM
only chooses which categories of its own data to fetch, never whose.
"""
from app.core.deps import CurrentUser
from app.db.hr import get_hr_repo

CATEGORIES = ("profile", "leave", "salary")


def get_my_profile(user: CurrentUser) -> dict | None:
    return get_hr_repo().get_employee(user.employee_id)


def get_my_leave_balance(user: CurrentUser) -> list[dict]:
    return get_hr_repo().get_leave_balance(user.employee_id)


def get_my_salary(user: CurrentUser) -> dict | None:
    return get_hr_repo().get_salary(user.employee_id)


_FETCHERS = {
    "profile": get_my_profile,
    "leave": get_my_leave_balance,
    "salary": get_my_salary,
}


def fetch_my_data(user: CurrentUser, categories: list[str]) -> dict:
    """Fetch the requested categories of the user's own data. Unknown categories are ignored."""
    return {c: _FETCHERS[c](user) for c in categories if c in _FETCHERS}
