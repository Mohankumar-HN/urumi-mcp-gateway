
import logging
from sqlalchemy.orm import Session

from backend.gateway.audit_models import AuditLog
from backend.gateway.database import SessionLocal

logger = logging.getLogger(__name__)


def record_audit(
    upstream_name: str,
    tool_name: str,
    duration_seconds: float,
    outcome: str,
    user_id: str = "system",
    error_message: str | None = None,
) -> None:
    """Persist the result of a tool call without disrupting the gateway."""
    try:
        with SessionLocal() as db:
            entry = AuditLog(
                user_id=user_id,
                upstream_name=upstream_name,
                tool_name=tool_name,
                duration_seconds=round(duration_seconds, 4),
                outcome=outcome,
                error_message=error_message,
            )
            db.add(entry)
            db.commit()
    except Exception:
        # A database logging failure should not crash the MCP gateway.
        logger.exception("Failed to save audit log for %s", tool_name)
