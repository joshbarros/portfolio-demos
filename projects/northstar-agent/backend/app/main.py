"""Northstar Agent — FastAPI app."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .core import (
    add_chunk,
    answer,
    chunk_text,
    connect,
    init_db,
    list_audit,
    list_messages,
    list_tenants,
    list_tickets,
    seed,
    utcnow,
)

ROOT = Path(os.getenv("NORTHSTAR_ROOT", str(Path(__file__).resolve().parents[2])))
DIST = ROOT / "frontend" / "dist"

conn = connect()
init_db(conn)
seed(conn)

app = FastAPI(title="Northstar Agent", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8093"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    tenant_id: str = Field(min_length=1, max_length=80)
    session_id: str = Field(default="demo-session", max_length=120)
    message: str = Field(min_length=1, max_length=4000)


class IngestRequest(BaseModel):
    tenant_id: str
    title: str
    source: str = "admin/upload.md"
    content: str


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"ok": True, "service": "northstar-agent", "mode": os.getenv("NORTHSTAR_MODE", "demo"), "time": utcnow()}


@app.get("/api/tenants")
def tenants() -> list[dict[str, Any]]:
    return list_tenants(conn)


@app.post("/api/chat")
def chat(payload: ChatRequest) -> dict[str, Any]:
    allowed = {row["id"] for row in list_tenants(conn)}
    if payload.tenant_id not in allowed:
        raise HTTPException(status_code=404, detail="tenant not found")
    return answer(conn, payload.tenant_id, payload.session_id, payload.message)


@app.get("/api/tickets")
def tickets(tenant_id: str = Query(...)) -> list[dict[str, Any]]:
    return list_tickets(conn, tenant_id)


@app.get("/api/audit")
def audit(tenant_id: str = Query(...)) -> list[dict[str, Any]]:
    return list_audit(conn, tenant_id)


@app.get("/api/history")
def history(tenant_id: str = Query(...), session_id: str = Query(...)) -> list[dict[str, Any]]:
    allowed = {row["id"] for row in list_tenants(conn)}
    if tenant_id not in allowed:
        raise HTTPException(status_code=404, detail="tenant not found")
    return list_messages(conn, tenant_id, session_id, limit=40)


@app.post("/api/admin/ingest")
def ingest(payload: IngestRequest, x_admin_token: str | None = Header(default=None)) -> dict[str, Any]:
    expected = os.getenv("ADMIN_TOKEN", "")
    if not expected:
        raise HTTPException(status_code=403, detail="admin ingestion is disabled (ADMIN_TOKEN not set)")
    if x_admin_token != expected:
        raise HTTPException(status_code=401, detail="invalid admin token")
    if payload.tenant_id not in {row["id"] for row in list_tenants(conn)}:
        raise HTTPException(status_code=404, detail="tenant not found")
    doc_id = f"admin-{utcnow()}"
    conn.execute(
        "INSERT INTO documents (id, tenant_id, title, source, updated_at, content) VALUES (?, ?, ?, ?, ?, ?)",
        (doc_id, payload.tenant_id, payload.title, payload.source, utcnow(), payload.content),
    )
    for i, piece in enumerate(chunk_text(payload.content)):
        add_chunk(conn, f"{doc_id}-{i}", payload.tenant_id, doc_id, payload.title, piece)
    conn.commit()
    return {"ok": True, "document_id": doc_id, "chunks": len(chunk_text(payload.content))}


if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(DIST / "index.html")

    @app.get("/{path:path}")
    def spa(path: str) -> FileResponse:
        candidate = DIST / path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(DIST / "index.html")
