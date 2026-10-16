
from starlette.responses import JSONResponse
from sqlalchemy import select

from backend.gateway.auth import hash_api_key
from backend.gateway.auth_models import APIKey, User
from backend.gateway.database import SessionLocal
from backend.gateway.request_identity import current_user_id


class MCPAuthMiddleware:
    """Require a valid API key for MCP HTTP requests."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        # Only authenticate HTTP requests.
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        raw_key = headers.get(b"x-api-key", b"").decode("utf-8").strip()

        if not raw_key:
            response = JSONResponse(
                {"detail": "API key required."},
                status_code=401,
            )
            await response(scope, receive, send)
            return

        key_hash = hash_api_key(raw_key)

        # Database access is synchronous; keep it brief.
        with SessionLocal() as db:
            api_key = db.scalar(
                select(APIKey).where(
                    APIKey.key_hash == key_hash,
                    APIKey.is_revoked.is_(False),
                )
            )

            user = db.get(User, api_key.user_id) if api_key else None

            if user is None or not user.is_active:
                response = JSONResponse(
                    {"detail": "Invalid, revoked, or inactive API key."},
                    status_code=401,
                )
                await response(scope, receive, send)
                return

            authenticated_user_id = user.id

        # Make the user ID available to audit logging during this request.
        token = current_user_id.set(authenticated_user_id)
        try:
            await self.app(scope, receive, send)
        finally:
            current_user_id.reset(token)
