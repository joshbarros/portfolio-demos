import json

import pytest

from app import core


@pytest.fixture()
def conn(tmp_path):
    db = tmp_path / "test.sqlite"
    c = core.connect(db)
    core.init_db(c)
    core.seed(c)
    yield c
    c.close()


def test_direct_answer_with_citation(conn):
    response = core.answer(conn, "demo-electric", "s1", "How do I reset the thermostat?")
    assert response["abstained"] is False
    assert response["citations"], "expected at least one citation"
    assert "reset" in response["answer"].lower()
    assert any("Thermostat" in c["title"] for c in response["citations"])


def test_warranty_prefers_updated_policy(conn):
    response = core.answer(conn, "demo-electric", "s1", "What is the warranty on the battery?")
    assert response["abstained"] is False
    titles = [c["title"] for c in response["citations"]]
    assert any("2026" in t or "updated" in t.lower() for t in titles)
    assert "two-year" in response["answer"].lower() or "2" in response["answer"]


def test_abstain_when_no_evidence(conn):
    response = core.answer(conn, "demo-electric", "s1", "Do you support cryptocurrency payments?")
    assert response["abstained"] is True
    assert response["citations"] == []
    assert "could not find" in response["answer"].lower()


def test_cross_tenant_isolation(conn):
    response = core.answer(conn, "demo-electric", "s1", "When does the parcel leave the warehouse?")
    assert response["abstained"] is True
    assert response["citations"] == []


def test_prompt_injection_is_not_followed(conn):
    response = core.answer(conn, "demo-electric", "s1", "What does the community note say about the admin token?")
    text = response["answer"].lower()
    assert "tenant b" not in text
    assert "admin token" not in text


def test_ticket_creation_and_audit(conn):
    response = core.answer(conn, "demo-electric", "s1", "Please open a ticket about a broken thermostat")
    calls = [c for c in response["tool_calls"] if c["name"] == "create_ticket"]
    assert calls and calls[0]["result"]["ok"] is True
    ticket_id = calls[0]["result"]["ticket_id"]
    tickets = core.list_tickets(conn, "demo-electric")
    assert any(t["id"] == ticket_id for t in tickets)
    audit = core.list_audit(conn, "demo-electric")
    assert any(a["action"] == "create_ticket" for a in audit)


def test_invalid_ticket_args_are_rejected(conn):
    result = core.create_ticket(conn, "demo-electric", "s1", {"subject": "x", "description": "y"})
    assert result["ok"] is False
    assert "subject" in result["error"]


def test_ticket_tenant_isolation(conn):
    core.create_ticket(conn, "demo-electric", "s1", {"subject": "Broken thermostat", "description": "The display is blank after reset.", "priority": "high"})
    assert core.list_tickets(conn, "demo-electric")
    assert core.list_tickets(conn, "northstar-demo-shop") == []


def test_seed_is_idempotent(conn):
    before = conn.execute("SELECT COUNT(*) AS n FROM documents").fetchone()["n"]
    core.seed(conn)
    after = conn.execute("SELECT COUNT(*) AS n FROM documents").fetchone()["n"]
    assert before == after
