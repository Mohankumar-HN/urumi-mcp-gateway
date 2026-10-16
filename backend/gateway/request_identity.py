
from contextvars import ContextVar

# The authenticated user ID for the current request.
current_user_id: ContextVar[str] = ContextVar(
    "current_user_id",
    default="system",
)
