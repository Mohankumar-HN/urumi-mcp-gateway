
from backend.gateway.database import Base, engine
from backend.gateway.models import Upstream
from backend.gateway.audit_models import AuditLog
from backend.gateway.auth_models import User, APIKey

Base.metadata.create_all(bind=engine)

print("Database tables created successfully.")
