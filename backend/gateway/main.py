
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Response, status
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.gateway.database import SessionLocal
from backend.gateway.models import Upstream


app = FastAPI(
    title="Urumi MCP Gateway",
    description="A gateway for managing and routing MCP tool calls",
    version="0.3.0",
)


class UpstreamCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    url: HttpUrl


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
    }


@app.get("/")
def root():
    return {"message": "Welcome to the Urumi MCP Gateway"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/upstreams")
def list_upstreams():
    with SessionLocal() as db:
        records = db.scalars(
            select(Upstream).order_by(Upstream.name)
        ).all()
        return [serialize_upstream(record) for record in records]


@app.post("/upstreams", status_code=status.HTTP_201_CREATED)
def create_upstream(upstream: UpstreamCreate):
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
def update_upstream(upstream_id: str, upstream: UpstreamCreate):
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
def disable_upstream(upstream_id: str):
    with SessionLocal() as db:
        record = get_upstream_or_404(db, upstream_id)
        record.enabled = False
        db.commit()
        db.refresh(record)
        return serialize_upstream(record)


@app.patch("/upstreams/{upstream_id}/enable")
def enable_upstream(upstream_id: str):
    with SessionLocal() as db:
        record = get_upstream_or_404(db, upstream_id)
        record.enabled = True
        db.commit()
        db.refresh(record)
        return serialize_upstream(record)


@app.delete("/upstreams/{upstream_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_upstream(upstream_id: str):
    with SessionLocal() as db:
        record = get_upstream_or_404(db, upstream_id)
        db.delete(record)
        db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
