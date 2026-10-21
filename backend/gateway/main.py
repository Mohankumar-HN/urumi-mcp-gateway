from uuid import uuid4
from datetime import datetime, timezone
from backend.gateway.auth_models import APIKey
from fastapi.middleware.cors import CORSMiddleware
from backend.gateway.audit_models import AuditLog
import logging
import os
import asyncio
from backend.gateway.auth_service import create_api_key
from backend.gateway.upstream import UpstreamServer, discover_tools
from backend.chat.agent import chat as run_chat_agent

from fastapi import (
    FastAPI,
    HTTPException,
    Response,
    status,
    Depends,
    Header,
)
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.gateway.database import SessionLocal
from backend.gateway.models import Upstream
from backend.gateway.auth import hash_api_key
from backend.gateway.auth_models import User, APIKey


app = FastAPI(
    title="Urumi MCP Gateway",
    description="A gateway for managing and routing MCP tool calls",
    version="0.4.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        ).split(",")
        if origin.strip()
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key"],
)


class UpstreamCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    url: HttpUrl
    credential: str | None = Field(default=None, max_length=1000)

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


def get_current_user(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> User:
    """Authenticate a request using its API key."""
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="API key required.",
        )

    key_hash = hash_api_key(x_api_key)

    with SessionLocal() as db:
        api_key = db.scalar(
            select(APIKey).where(
                APIKey.key_hash == key_hash,
                APIKey.is_revoked.is_(False),
            )
        )

        if api_key is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid or revoked API key.",
            )

        user = db.get(User, api_key.user_id)

        if user is None or not user.is_active:
            raise HTTPException(
                status_code=401,
                detail="User is inactive or does not exist.",
            )

        # Return a detached copy of the user's identity and role.
        return User(
            id=user.id,
            username=user.username,
            role=user.role,
            is_active=user.is_active,
        )


def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Allow administrative operations only for admins."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required.",
        )

    return current_user


def get_upstream_or_404(db: Session, upstream_id: str) -> Upstream:
    upstream = db.get(Upstream, upstream_id)
    if upstream is None:
        raise HTTPException(status_code=404, detail="Upstream not found.")
    return upstream


def serialize_upstream(upstream: Upstream) -> dict:
    return {
        "id": upstream.id,
        "name": upstream.name,
        "url": upstream.url,
        "enabled": upstream.enabled,
        "status": "disabled" if not upstream.enabled else upstream.status,
    }


@app.get("/")
def root():
    return {"message": "Welcome to the Urumi MCP Gateway"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    """Return the identity associated with the API key."""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "role": current_user.role,
    }


@app.get("/upstreams")
def list_upstreams(
    current_user: User = Depends(get_current_user),
):
    with SessionLocal() as db:
        records = db.scalars(
            select(Upstream).order_by(Upstream.name)
        ).all()
        return [serialize_upstream(record) for record in records]


@app.post("/upstreams", status_code=status.HTTP_201_CREATED)
def create_upstream(
    upstream: UpstreamCreate,
    admin: User = Depends(require_admin),
):
    name = upstream.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Name cannot be blank.")

    with SessionLocal() as db:
        duplicate = db.scalar(
            select(Upstream).where(Upstream.name.ilike(name))
        )
        if duplicate:
            raise HTTPException(
                status_code=409,
                detail="An upstream with this name already exists.",
            )

        record = Upstream(
            id=str(uuid4()),
            name=name,
            url=str(upstream.url).rstrip("/"),
            credential=upstream.credential.strip() if upstream.credential else None,
            enabled=True,
        )
        db.add(record)

        try:
            db.commit()
            db.refresh(record)
            return serialize_upstream(record)
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=409,
                detail="An upstream with this name already exists.",
            )


@app.put("/upstreams/{upstream_id}")
def update_upstream(
    upstream_id: str,
    upstream: UpstreamCreate,
    admin: User = Depends(require_admin),
):
    name = upstream.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Name cannot be blank.")

    with SessionLocal() as db:
        record = get_upstream_or_404(db, upstream_id)

        duplicate = db.scalar(
            select(Upstream).where(
                Upstream.name.ilike(name),
                Upstream.id != upstream_id,
            )
        )
        if duplicate:
            raise HTTPException(
                status_code=409,
                detail="An upstream with this name already exists.",
            )

        record.name = name
        record.url = str(upstream.url).rstrip("/")
        record.credential = (
            upstream.credential.strip() if upstream.credential else None
        )

        try:
            db.commit()
            db.refresh(record)
            return serialize_upstream(record)
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=409,
                detail="An upstream with this name already exists.",
            )


@app.patch("/upstreams/{upstream_id}/disable")
def disable_upstream(
    upstream_id: str,
    admin: User = Depends(require_admin),
):
    with SessionLocal() as db:
        record = get_upstream_or_404(db, upstream_id)
        record.enabled = False
        db.commit()
        db.refresh(record)
        return serialize_upstream(record)


@app.patch("/upstreams/{upstream_id}/enable")
def enable_upstream(
    upstream_id: str,
    admin: User = Depends(require_admin),
):
    with SessionLocal() as db:
        record = get_upstream_or_404(db, upstream_id)
        record.enabled = True
        db.commit()
        db.refresh(record)
        return serialize_upstream(record)


@app.delete(
    "/upstreams/{upstream_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_upstream(
    upstream_id: str,
    admin: User = Depends(require_admin),
):
    with SessionLocal() as db:
        record = get_upstream_or_404(db, upstream_id)
        db.delete(record)
        db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.patch("/api-keys/{key_id}/revoke")
def revoke_api_key(
    key_id: str,
    admin: User = Depends(require_admin),
):
    """Revoke an API key. Admin access required."""
    with SessionLocal() as db:
        api_key = db.get(APIKey, key_id)

        if api_key is None:
            raise HTTPException(
                status_code=404,
                detail="API key not found.",
            )

        if api_key.is_revoked:
            return {
                "message": "API key was already revoked.",
                "key_id": api_key.id,
            }

        api_key.is_revoked = True
        api_key.revoked_at = datetime.now(timezone.utc)

        db.commit()

        return {
            "message": "API key revoked successfully.",
            "key_id": api_key.id,
        }


@app.get("/api-keys")
def list_api_keys(
    admin: User = Depends(require_admin),
):
    """List API key metadata without exposing key secrets."""
    with SessionLocal() as db:
        keys = db.scalars(
            select(APIKey).order_by(APIKey.created_at.desc())
        ).all()

        return [
            {
                "id": key.id,
                "user_id": key.user_id,
                "is_revoked": key.is_revoked,
                "created_at": key.created_at,
                "revoked_at": key.revoked_at,
            }
            for key in keys
        ]


@app.post("/api-keys")
def create_my_api_key(current_user: User = Depends(get_current_user)):
    """Create a key for the authenticated user and return it once."""
    with SessionLocal() as db:
        return {
            "api_key": create_api_key(db, current_user.id),
            "message": "Store this key securely; it will not be shown again.",
        }


@app.get("/audit-logs")
def list_audit_logs(
    limit: int = 100,
    admin: User = Depends(require_admin),
):
    """List recent tool-call audit records. Admin access required."""

    if not 1 <= limit <= 500:
        raise HTTPException(
            status_code=422,
            detail="Limit must be between 1 and 500.",
        )

    with SessionLocal() as db:
        records = db.scalars(
            select(AuditLog)
            .order_by(AuditLog.timestamp.desc(), AuditLog.id.desc())
            .limit(limit)
        ).all()

        return [
            {
                "id": record.id,
                "user_id": record.user_id,
                "upstream_name": record.upstream_name,
                "tool_name": record.tool_name,
                "timestamp": record.timestamp,
                "duration_seconds": record.duration_seconds,
                "outcome": record.outcome,
                "error_message": record.error_message,
            }
            for record in records
        ]

@app.post("/chat")
async def chat_endpoint(
    request: ChatRequest,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    current_user: User = Depends(get_current_user),
):
    """Send a message to the authenticated user's chat agent."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API key required.")

    try:
        answer = await run_chat_agent(request.message, x_api_key)
        return {"answer": answer}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        logging.exception("Chat request failed.")
        raise HTTPException(
            status_code=502,
            detail="The chat agent could not complete the request. Check the gateway logs.",
        )