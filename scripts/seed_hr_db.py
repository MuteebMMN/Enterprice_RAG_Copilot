"""Create the mock HR database with fake employees.

Usage:  python scripts/seed_hr_db.py
Re-running deletes and recreates data/hr.db.
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.config import get_settings  # noqa: E402

DOMAIN = "novacore.com"

# id, name, department, job_title, manager_id, hire_date, annual_salary
EMPLOYEES = [
    ("E001", "Sara Malik",     "Human Resources", "HR Manager",           None,   "2019-03-04", 98000),
    ("E002", "Omar Khan",      "IT",              "IT Administrator",     None,   "2018-07-16", 105000),
    ("E003", "Alice Johnson",  "Engineering",     "Software Engineer",    "E010", "2021-01-11", 92000),
    ("E004", "Bob Smith",      "Engineering",     "Software Engineer",    "E010", "2020-09-21", 88000),
    ("E005", "Carol Davis",    "Finance",         "Financial Analyst",    "E011", "2022-02-14", 76000),
    ("E006", "David Wilson",   "Sales",           "Account Executive",    "E012", "2019-11-05", 81000),
    ("E007", "Emma Brown",     "Marketing",       "Marketing Specialist", "E012", "2023-04-03", 64000),
    ("E008", "Farhan Ali",     "Engineering",     "DevOps Engineer",      "E010", "2021-08-23", 97000),
    ("E009", "Grace Lee",      "Support",         "Support Agent",        "E013", "2023-06-12", 52000),
    ("E010", "Henry Taylor",   "Engineering",     "Engineering Manager",  None,   "2017-05-29", 135000),
    ("E011", "Isla Moore",     "Finance",         "Finance Manager",      None,   "2016-10-10", 118000),
    ("E012", "Jack Anderson",  "Sales",           "Sales Manager",        None,   "2018-01-22", 112000),
    ("E013", "Kiran Patel",    "Support",         "Support Lead",         None,   "2020-03-30", 72000),
    ("E014", "Laura White",    "Engineering",     "QA Engineer",          "E010", "2022-09-19", 78000),
    ("E015", "Mark Thompson",  "Sales",           "Sales Associate",      "E012", "2024-01-08", 55000),
    ("E016", "Muteeb Nasir",   "Engineering",     "AI Engineer",          "E010", "2024-06-03", 85000),
]

# Employees whose email is not firstname.lastname@DOMAIN
EMAIL_OVERRIDES = {"E016": "muteebnasir9@gmail.com"}

# leave_type -> (total days per year, used-days list aligned with EMPLOYEES)
LEAVE_TOTALS = {"annual": 24, "sick": 10, "casual": 6}
USED = {
    "annual": [3, 8, 12, 5, 0, 15, 2, 9, 1, 20, 7, 11, 4, 6, 0, 2],
    "sick":   [0, 2, 1, 0, 3, 0, 1, 4, 0, 2, 0, 1, 0, 5, 0, 0],
    "casual": [1, 0, 2, 3, 0, 1, 0, 2, 1, 0, 4, 0, 1, 2, 0, 1],
}


def email_for(name: str) -> str:
    return f"{name.lower().replace(' ', '.')}@{DOMAIN}"


def main() -> None:
    path = Path(get_settings().hr_db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.unlink(missing_ok=True)

    names = {e[0]: e[1] for e in EMPLOYEES}
    con = sqlite3.connect(path)
    con.executescript(
        """
        CREATE TABLE employees (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
            department TEXT NOT NULL, job_title TEXT NOT NULL, manager TEXT,
            hire_date TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'active'
        );
        CREATE TABLE leave_balances (
            employee_id TEXT NOT NULL REFERENCES employees(id),
            leave_type TEXT NOT NULL, total_days INTEGER NOT NULL, used_days INTEGER NOT NULL,
            PRIMARY KEY (employee_id, leave_type)
        );
        CREATE TABLE salaries (
            employee_id TEXT PRIMARY KEY REFERENCES employees(id),
            annual_salary INTEGER NOT NULL, currency TEXT NOT NULL DEFAULT 'USD'
        );
        """
    )
    for i, (eid, name, dept, title, mgr, hired, salary) in enumerate(EMPLOYEES):
        con.execute(
            "INSERT INTO employees VALUES (?,?,?,?,?,?,?,'active')",
            (eid, name, EMAIL_OVERRIDES.get(eid, email_for(name)), dept, title, names.get(mgr), hired),
        )
        for leave_type, total in LEAVE_TOTALS.items():
            con.execute(
                "INSERT INTO leave_balances VALUES (?,?,?,?)",
                (eid, leave_type, total, USED[leave_type][i]),
            )
        con.execute("INSERT INTO salaries VALUES (?,?, 'USD')", (eid, salary))
    con.commit()
    con.close()
    print(f"Created {path} with {len(EMPLOYEES)} employees")


if __name__ == "__main__":
    main()
