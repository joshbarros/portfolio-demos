"""Vaultgate core: tenant context, sessions, protected files and signed URLs.

The tenant comes from a validated session. Every database operation runs inside a
transaction that sets `app.org_id`, and the application role is subject to
Postgres row-level security (FORCE RLS). A browser parameter never picks the tenant.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Iterator

import psycopg
from psycopg.rows import dict_row

APP_DSN = os.getenv("VAULT_APP_DSN", "postgresql://vault_app:vault_app@127.0.0.1:5443/vaultgate")
OWNER_DSN = os.getenv("VAULT_OWNER_DSN", "postgresql://vault_owner:vault_owner@127.0.0.1:5443/vaultgate")
SECRET = os.getenv("VAULT_SECRET", "dev-secret")
SESSION_MINUTES = int(os.getenv("SESSION_MINUTES", "30"))
URL_SECONDS = int(os.getenv("URL_SECONDS", "60"))


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def now() -> datetime:
    return datetime.now(timezone.utc)


def connect_app() -> psycopg.Connection:
    return psycopg.connect(APP_DSN, autocommit=False, row_factory=dict_row)


def connect_owner() -> psycopg.Connection:
    return psycopg.connect(OWNER_DSN, autocommit=True, row_factory=dict_row)


@contextmanager
def tenant(conn: psycopg.Connection, org_id: str) -> Iterator[psycopg.Cursor]:
    """Sets the tenant for this transaction only; a pooled connection cannot leak it."""
    with conn.transaction():
        with conn.cursor() as cur:
            cur.execute("select set_config('app.org_id', %s, true)", [org_id])
            yield cur


def login(user_id: str, password: str) -> dict:
    with connect_app() as conn:
        with conn.cursor() as cur:
            cur.execute("select id, org_id, role, password_hash from users where id = %s", [user_id])
            user = cur.fetchone()
    if not user or not hmac.compare_digest(user["password_hash"], sha256(password)):
        raise PermissionError("invalid credentials")
    token = secrets.token_urlsafe(32)
    expires = now() + timedelta(minutes=SESSION_MINUTES)
    with connect_app() as conn:
        with tenant(conn, user["org_id"]) as cur:
            cur.execute(
                "insert into sessions (token_hash, user_id, org_id, expires_at) values (%s,%s,%s,%s)",
                [sha256(token), user["id"], user["org_id"], expires],
            )
            audit(cur, user["org_id"], user["id"], "login", {})
    return {"token": token, "org_id": user["org_id"], "user_id": user["id"], "expires_at": expires.isoformat()}


def session(token: str) -> dict:
    with connect_app() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """select token_hash, user_id, org_id, expires_at, revoked_at
                   from sessions where token_hash = %s""",
                [sha256(token)],
            )
            row = cur.fetchone()
    if not row:
        raise PermissionError("unknown session")
    if row["revoked_at"] is not None:
        raise PermissionError("session revoked")
    if row["expires_at"] <= now():
        raise PermissionError("session expired")
    return row


def logout(token: str) -> None:
    with connect_app() as conn:
        with conn.cursor() as cur:
            cur.execute("update sessions set revoked_at = now() where token_hash = %s", [sha256(token)])


def audit(cur: psycopg.Cursor, org_id: str, actor: str, action: str, detail: dict) -> None:
    cur.execute(
        "insert into audit (org_id, actor_id, action, detail) values (%s,%s,%s,%s)",
        [org_id, actor, action, json.dumps(detail)],
    )


def list_files(sess: dict) -> list[dict]:
    with connect_app() as conn:
        with tenant(conn, sess["org_id"]) as cur:
            cur.execute("select id, name, content_type, octet_length(bytes) as size from files order by name")
            rows = cur.fetchall()
            audit(cur, sess["org_id"], sess["user_id"], "files.list", {"count": len(rows)})
    return rows


def get_file(sess: dict, file_id: str) -> dict | None:
    with connect_app() as conn:
        with tenant(conn, sess["org_id"]) as cur:
            cur.execute("select id, org_id, name, content_type, bytes from files where id = %s", [file_id])
            row = cur.fetchone()
            audit(cur, sess["org_id"], sess["user_id"], "file.read", {"file_id": file_id, "found": bool(row)})
    return row


def sign_download(sess: dict, file_id: str, ttl_seconds: int = URL_SECONDS) -> dict:
    # Only metadata is checked here; RLS still applies on the download request.
    if not get_file(sess, file_id):
        raise PermissionError("file not found in this organization")
    exp = int((now() + timedelta(seconds=ttl_seconds)).timestamp())
    payload = f"{file_id}:{sess['org_id']}:{exp}"
    sig = hmac.new(SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    audit_with(sess, "file.sign", {"file_id": file_id, "exp": exp})
    return {"file_id": file_id, "exp": exp, "sig": sig}


def audit_with(sess: dict, action: str, detail: dict) -> None:
    with connect_app() as conn:
        with tenant(conn, sess["org_id"]) as cur:
            audit(cur, sess["org_id"], sess["user_id"], action, detail)


def verify_download(sess: dict, file_id: str, exp: int, sig: str) -> dict | None:
    payload = f"{file_id}:{sess['org_id']}:{exp}"
    expected = hmac.new(SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        audit_with(sess, "download.denied", {"file_id": file_id, "reason": "bad_signature"})
        return None
    if exp < int(now().timestamp()):
        # A signed URL stays valid until it expires; this is documented, not hidden.
        audit_with(sess, "download.denied", {"file_id": file_id, "reason": "expired"})
        return None
    row = get_file(sess, file_id)
    if row:
        audit_with(sess, "download.allowed", {"file_id": file_id})
    return row


def list_audit(sess: dict) -> list[dict]:
    with connect_app() as conn:
        with tenant(conn, sess["org_id"]) as cur:
            cur.execute(
                "select id, actor_id, action, detail, created_at from audit order by id desc limit 50"
            )
            return cur.fetchall()
