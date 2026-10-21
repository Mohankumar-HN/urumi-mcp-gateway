from getpass import getpass

from sqlalchemy import select

from backend.gateway.database import SessionLocal
from backend.gateway.auth_service import create_user
from backend.gateway.auth_models import User

username = input("Enter admin username: ").strip()

if not username:
    raise SystemExit("Username cannot be empty.")

with SessionLocal() as db:
    existing = db.scalar(
        select(User).where(User.username == username)
    )

    if existing:
        raise SystemExit(
            "This username already exists. Choose a different username."
        )

    admin, api_key = create_user(
        db,
        username=username,
        role="admin",
    )

    print("\nAdmin created successfully.")
    print("Username:", admin.username)
    print("Role:", admin.role)
    print("\nCopy this API key and store it securely:")
    print(api_key)
