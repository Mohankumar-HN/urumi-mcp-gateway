from backend.gateway.database import SessionLocal
from backend.gateway.auth_service import (
    create_user,
    authenticate_api_key,
)

with SessionLocal() as db:
    username = "test_member"

    # Reuse an existing test user rather than creating duplicates.
    from backend.gateway.auth_models import User

    existing_user = (
        db.query(User)
        .filter(User.username == username)
        .first()
    )

    if existing_user:
        print("Test user already exists. Delete it manually before rerunning.")
    else:
        user, raw_key = create_user(db, username, "member")
        print("User created:", user.username)
        print("Role:", user.role)
        print("Generated API key:", raw_key)

        authenticated_user = authenticate_api_key(db, raw_key)
        print(
            "Authentication successful:",
            authenticated_user is not None,
        )

        invalid_user = authenticate_api_key(db, "invalid_key")
        print("Invalid key rejected:", invalid_user is None)
