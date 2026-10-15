import uuid
from sqlalchemy.orm import Session

from backend.gateway.auth import generate_api_key, hash_api_key
from backend.gateway.auth_models import User, APIKey


def create_user(
    db: Session,
    username: str,
    role: str = "member",
) -> tuple[User, str]:
    """Create a user and generate their API key."""
    if role not in {"admin", "member"}:
        raise ValueError("Role must be 'admin' or 'member'.")

    user = User(
        id=str(uuid.uuid4()),
        username=username,
        role=role,
    )
    db.add(user)
    db.flush()

    raw_key = generate_api_key()
    api_key = APIKey(
        id=str(uuid.uuid4()),
        user_id=user.id,
        key_hash=hash_api_key(raw_key),
    )
    db.add(api_key)
    db.commit()
    db.refresh(user)

    return user, raw_key


def authenticate_api_key(db: Session, raw_key: str) -> User | None:
    """Return the active user associated with a valid API key."""
    key_hash = hash_api_key(raw_key)

    api_key = (
        db.query(APIKey)
        .filter(
            APIKey.key_hash == key_hash,
            APIKey.is_revoked.is_(False),
        )
        .first()
    )

    if api_key is None:
        return None

    user = (
        db.query(User)
        .filter(
            User.id == api_key.user_id,
            User.is_active.is_(True),
        )
        .first()
    )

    return user