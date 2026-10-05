"""Access to the company HR data.

The rest of the app only talks to `HRRepository`. To plug in the real company
database later, write another class with the same methods and return it from
`get_hr_repo()`.
"""
import sqlite3
from abc import ABC, abstractmethod
from functools import lru_cache
from app.core.config import get_settings


class HRRepository(ABC):
    @abstractmethod
    def get_employee(self, employee_id: str) -> dict | None: ...

    @abstractmethod
    def get_leave_balance(self, employee_id: str) -> list[dict]: ...

    @abstractmethod
    def get_salary(self, employee_id: str) -> dict | None: ...

    @abstractmethod
    def list_employee_names(self) -> list[dict]:
        """id, name, email of every employee. Used by the guardrails only."""


class SqliteHRRepository(HRRepository):
    def __init__(self, path: str):
        self.path = path

    def _connect(self) -> sqlite3.Connection:
        # Read-only: the app can never modify HR data.
        con = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        return con

    def _query(self, sql: str, params: tuple = ()) -> list[dict]:
        con = self._connect()
        try:
            return [dict(r) for r in con.execute(sql, params).fetchall()]
        finally:
            con.close()

    def get_employee(self, employee_id: str) -> dict | None:
        rows = self._query(
            "SELECT id, name, email, department, job_title, manager, hire_date, status "
            "FROM employees WHERE id = ?",
            (employee_id,),
        )
        return rows[0] if rows else None

    def get_leave_balance(self, employee_id: str) -> list[dict]:
        return self._query(
            "SELECT leave_type, total_days, used_days, (total_days - used_days) AS remaining_days "
            "FROM leave_balances WHERE employee_id = ? ORDER BY leave_type",
            (employee_id,),
        )

    def get_salary(self, employee_id: str) -> dict | None:
        rows = self._query(
            "SELECT annual_salary, currency FROM salaries WHERE employee_id = ?",
            (employee_id,),
        )
        return rows[0] if rows else None

    def list_employee_names(self) -> list[dict]:
        return self._query("SELECT id, name, email FROM employees ORDER BY id")


@lru_cache
def get_hr_repo() -> HRRepository:
    return SqliteHRRepository(get_settings().hr_db_path)
