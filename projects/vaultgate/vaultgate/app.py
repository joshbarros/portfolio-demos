"""Vaultgate HTTP API and static portal."""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import core

app = FastAPI(title="Vaultgate", version="0.1.0")


class Login(BaseModel):
    user_id: str
    password: str


def bearer(authorization: str | None) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing session")
    try:
        return core.session(authorization.removeprefix("Bearer ").strip())
    except PermissionError as error:
        raise HTTPException(status_code=401, detail=str(error)) from error


@app.get("/api/health")
def health():
    return {"ok": True, "service": "vaultgate"}


@app.post("/api/login")
def login(payload: Login):
    try:
        return core.login(payload.user_id, payload.password)
    except PermissionError as error:
        raise HTTPException(status_code=401, detail=str(error)) from error


@app.post("/api/logout")
def logout(authorization: str | None = Header(default=None)):
    sess = bearer(authorization)
    core.logout(authorization.removeprefix("Bearer ").strip())
    return {"ok": True, "user": sess["user_id"]}


@app.get("/api/me")
def me(authorization: str | None = Header(default=None)):
    sess = bearer(authorization)
    return {"user_id": sess["user_id"], "org_id": sess["org_id"]}


@app.get("/api/files")
def files(authorization: str | None = Header(default=None)):
    sess = bearer(authorization)
    return {"files": core.list_files(sess)}


@app.get("/api/files/{file_id}")
def file_detail(file_id: str, authorization: str | None = Header(default=None)):
    sess = bearer(authorization)
    row = core.get_file(sess, file_id)
    if not row:
        raise HTTPException(status_code=404, detail="file not found")
    return {"id": row["id"], "name": row["name"], "content_type": row["content_type"], "size": len(row["bytes"])}


@app.post("/api/files/{file_id}/sign")
def sign(file_id: str, authorization: str | None = Header(default=None)):
    sess = bearer(authorization)
    try:
        return core.sign_download(sess, file_id)
    except PermissionError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.get("/api/download")
def download(
    file_id: str = Query(...),
    exp: int = Query(...),
    sig: str = Query(...),
    authorization: str | None = Header(default=None),
):
    sess = bearer(authorization)
    row = core.verify_download(sess, file_id, exp, sig)
    if not row:
        raise HTTPException(status_code=403, detail="invalid or expired link")
    return Response(content=row["bytes"], media_type=row["content_type"])


@app.get("/api/audit")
def audit(authorization: str | None = Header(default=None)):
    sess = bearer(authorization)
    return {"audit": core.list_audit(sess)}


DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"
if DIST.exists():
    app.mount("/", StaticFiles(directory=DIST, html=True), name="portal")
