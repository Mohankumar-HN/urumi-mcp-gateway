
from getpass import getpass

from backend.gateway.database import SessionLocal
from backend.gateway.auth_service import create_user
from backend.gateway.auth_models import User
from sqlalchemy import select

username = input("Enter member username: ").strip()

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

    user, api_key = create_user(
        db,
        username=username,
        role="member",
    )

    print("\nMember created successfully.")
    print("Username:", user.username)
    print("Role:", user.role)
    print("\nStore this API key securely. It will not be shown again:")
    print(api_key)
