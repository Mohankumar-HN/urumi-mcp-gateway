import os

from sqlalchemy import select, text

from backend.gateway import audit_models, auth_models
from backend.gateway.database import Base, SessionLocal, engine
from backend.gateway.models import Upstream


def bootstrap() -> None:
    """Create tables and register configured internal MCP upstreams."""
    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        connection.execute(text(
            "ALTER TABLE upstreams ADD COLUMN IF NOT EXISTS credential VARCHAR(1000)"
        ))
        connection.execute(text(
            "ALTER TABLE upstreams ADD COLUMN IF NOT EXISTS status VARCHAR(20) "
            "NOT NULL DEFAULT 'unknown'"
        ))
        connection.execute(text(
            "ALTER TABLE upstreams ADD COLUMN IF NOT EXISTS status_message VARCHAR(500)"
        ))

    configured = os.getenv("BOOTSTRAP_UPSTREAMS", "")
    upstreams = []
    for item in configured.split(","):
        name, separator, url = item.partition("=")
        if separator and name.strip() and url.strip():
            upstreams.append((name.strip(), url.strip().rstrip("/")))

    with SessionLocal() as db:
        for name, url in upstreams:
            existing = db.scalar(
                select(Upstream).where(Upstream.name.ilike(name))
            )
            if existing is None:
                db.add(
                    Upstream(
                        id=f"bootstrap-{name}",
                        name=name,
                        url=url,
                        enabled=True,
                    )
                )
        db.commit()


if __name__ == "__main__":
    bootstrap()
