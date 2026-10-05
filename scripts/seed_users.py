"""Create login accounts for every employee in the HR database.

Usage:
  python scripts/seed_users.py                       # create missing accounts, random passwords (printed once)
  python scripts/seed_users.py --password "Xyz12345" # create missing accounts with one shared temporary password
  python scripts/seed_users.py --set-password a@b.com "NewPass123"   # reset one account's password

Existing accounts are never overwritten by the first two forms.
Roles: E001 = hr, E002 = admin, everyone else = employee.
"""
import argparse
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.security import hash_password  # noqa: E402
from app.db.hr import get_hr_repo  # noqa: E402
from app.db.users import create_user, get_user_by_email, init_users_db, set_password_hash  # noqa: E402

ROLE_BY_EMPLOYEE = {"E001": "hr", "E002": "admin"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--password", help="use this temporary password for every new account")
    parser.add_argument("--set-password", nargs=2, metavar=("EMAIL", "PASSWORD"))
    args = parser.parse_args()

    init_users_db()

    if args.set_password:
        email, password = args.set_password
        user = get_user_by_email(email)
        if user is None:
            sys.exit(f"No account for {email}")
        set_password_hash(user.id, hash_password(password))
        print(f"Password updated for {email}")
        return

    created = []
    for emp in get_hr_repo().list_employee_names():
        if get_user_by_email(emp["email"]):
            continue
        password = args.password or secrets.token_urlsafe(9)
        create_user(emp["email"], hash_password(password), ROLE_BY_EMPLOYEE.get(emp["id"], "employee"), emp["id"])
        created.append((emp["email"], ROLE_BY_EMPLOYEE.get(emp["id"], "employee"), password))

    if not created:
        print("All employees already have accounts.")
        return
    if args.password:
        # Never echo a password the caller supplied (it would end up in logs).
        print(f"Created {len(created)} accounts with the password you supplied.")
        return
    print(f"Created {len(created)} accounts. Passwords are shown ONCE:\n")
    for email, role, password in created:
        print(f"{role:9} {email:36} {password}")


if __name__ == "__main__":
    main()
