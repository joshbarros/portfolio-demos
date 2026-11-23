"""Postgres + pgvector path. Skipped unless NORTHSTAR_TEST_DATABASE_URL is set."""
import json
import os
import uuid

import pytest

from app import core

PG_URL = os.getenv("NORTHSTAR_TEST_DATABASE_URL", "")


@pytest.fixture()
def pg_conn(monkeypatch):
    if not PG_URL:
        pytest.skip("set NORTHSTAR_TEST_DATABASE_URL to run the Postgres suite")
    monkeypatch.setattr(core, "DATABASE_URL", PG_URL)
    conn = core.connect()
    core.init_db(conn)
    tenant = f"pg-test-{uuid.uuid4().hex[:8]}"
    conn.execute("INSERT INTO tenants (id, name) VALUES (?, ?)", (tenant, "PG Test Co."))
    conn.execute(
        "INSERT INTO documents (id, tenant_id, title, source, updated_at, content) VALUES (?, ?, ?, ?, ?, ?)",
        (
            f"{tenant}-doc",
            tenant,
            "Thermostat reset guide",
            "support/thermostat-reset.md",
            "2026-10-02",
            "To reset the thermostat, hold the mode button for 8 seconds until the display shows RESET.",
        ),
    )
    core.add_chunk(
        conn,
        f"{tenant}-doc-0",
        tenant,
        f"{tenant}-doc",
        "Thermostat reset guide",
        "To reset the thermostat, hold the mode button for 8 seconds until the display shows RESET.",
    )
    conn.commit()
    yield conn, tenant
    conn.execute("DELETE FROM chunks WHERE tenant_id = ?", (tenant,))
    conn.execute("DELETE FROM documents WHERE tenant_id = ?", (tenant,))
    conn.execute("DELETE FROM tickets WHERE tenant_id = ?", (tenant,))
    conn.execute("DELETE FROM audit WHERE tenant_id = ?", (tenant,))
    conn.execute("DELETE FROM messages WHERE tenant_id = ?", (tenant,))
    conn.execute("DELETE FROM tenants WHERE id = ?", (tenant,))
    conn.commit()
    conn.close()


def test_postgres_retrieval_with_pgvector_order(pg_conn):
    conn, tenant = pg_conn
    hits = core.retrieve(conn, tenant, "How do I reset the thermostat?")
    assert hits, "pgvector query returned no rows"
    assert hits[0].title.startswith("Thermostat")
    assert 0.0 < hits[0].score <= 1.0


def test_postgres_ticket_and_audit_round_trip(pg_conn):
    conn, tenant = pg_conn
    result = core.create_ticket(
        conn, tenant, "pg-session", {"subject": "Broken thermostat", "description": "Display is blank.", "priority": "high"}
    )
    assert result["ok"] is True
    assert core.list_tickets(conn, tenant)[0]["id"] == result["ticket_id"]
    assert json.loads(core.list_audit(conn, tenant)[0]["args"])["subject"] == "Broken thermostat"


def test_postgres_tenant_isolation(pg_conn):
    conn, tenant = pg_conn
    assert core.retrieve(conn, "demo-electric", "How do I reset the thermostat?") == [] or all(
        hit.document_id.startswith("de-") for hit in core.retrieve(conn, "demo-electric", "thermostat reset")
    )
    assert all(hit.document_id != f"{tenant}-doc" for hit in core.retrieve(conn, "demo-electric", "thermostat reset"))
