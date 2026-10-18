
import secrets

from sqlalchemy import select

from backend.gateway.database import SessionLocal
from backend.gateway.auth import hash_api_key
from backend.gateway.auth_models import User, APIKey


def main():
    username = input("Enter existing admin username: ").strip()

    if not username:
        raise SystemExit("Username cannot be empty.")

    with SessionLocal() as db:
        admin = db.scalar(
            select(User).where(
                User.username == username,
                User.role == "admin",
            )
        )

        if not admin:
            raise SystemExit(
                "No existing admin found with that username. "
                "Check the username and try again."
            )

        # Generate a fresh key and store only its hash.
        api_key = "urumi_" + secrets.token_urlsafe(32)

        record = APIKey(
            id=secrets.token_hex(16),
            user_id=admin.id,
            key_hash=hash_api_key(api_key),
            is_revoked=False,
        )

        db.add(record)
        db.commit()

        print("\nNew API key generated successfully.")
        print("Username:", admin.username)
        print("Role:", admin.role)
        print("\nSave this key securely; it will not be shown again:")
        print(api_key)


if __name__ == "__main__":
    main()
