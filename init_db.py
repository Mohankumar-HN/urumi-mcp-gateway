
from backend.gateway.database import Base, engine
from backend.gateway.models import Upstream

Base.metadata.create_all(bind=engine)

print("Database tables created successfully.")
