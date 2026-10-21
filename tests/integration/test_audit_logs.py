
from backend.gateway.database import SessionLocal
from backend.gateway.audit_models import AuditLog

def main():
    with SessionLocal() as db:
        logs = (
            db.query(AuditLog)
            .order_by(AuditLog.timestamp.desc())
            .limit(10)
            .all()
        )

        print(f"Recent audit records: {len(logs)}")

        for log in logs:
            print("-" * 40)
            print("User ID:", log.user_id)
            print("Upstream:", log.upstream_name)
            print("Tool:", log.tool_name)
            print("Outcome:", log.outcome)
            print("Duration (seconds):", log.duration_seconds)
            print("Timestamp:", log.timestamp)

if __name__ == "__main__":
    main()
