from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_tenants():
    response = client.get("/api/tenants")
    assert response.status_code == 200
    ids = {t["id"] for t in response.json()}
    assert {"demo-electric", "northstar-demo-shop"} <= ids


def test_chat_returns_citations():
    response = client.post(
        "/api/chat",
        json={"tenant_id": "demo-electric", "session_id": "api-test", "message": "How do I reset the thermostat?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["abstained"] is False
    assert data["citations"]
    assert "reset" in data["answer"].lower()


def test_chat_rejects_unknown_tenant():
    response = client.post(
        "/api/chat",
        json={"tenant_id": "does-not-exist", "session_id": "api-test", "message": "hello"},
    )
    assert response.status_code == 404


def test_audit_endpoints():
    response = client.post(
        "/api/chat",
        json={"tenant_id": "demo-electric", "session_id": "api-test", "message": "Please open a ticket about a broken thermostat"},
    )
    assert response.status_code == 200
    assert any(c["name"] == "create_ticket" for c in response.json()["tool_calls"])

    tickets = client.get("/api/tickets", params={"tenant_id": "demo-electric"})
    assert tickets.status_code == 200
    assert tickets.json()

    audit = client.get("/api/audit", params={"tenant_id": "demo-electric"})
    assert audit.status_code == 200
    assert any(a["action"] == "create_ticket" for a in audit.json())


def test_history_is_session_scoped():
    client.post(
        "/api/chat",
        json={"tenant_id": "demo-electric", "session_id": "history-a", "message": "How do I reset the thermostat?"},
    )
    mine = client.get("/api/history", params={"tenant_id": "demo-electric", "session_id": "history-a"})
    assert mine.status_code == 200
    roles = [m["role"] for m in mine.json()]
    assert roles == ["user", "assistant"]

    other = client.get("/api/history", params={"tenant_id": "demo-electric", "session_id": "history-b"})
    assert other.json() == []

    cross = client.get("/api/history", params={"tenant_id": "northstar-demo-shop", "session_id": "history-a"})
    assert cross.json() == []


def test_admin_ingest_disabled_without_token():
    response = client.post(
        "/api/admin/ingest",
        json={"tenant_id": "demo-electric", "title": "Test", "content": "Some content for the test."},
    )
    assert response.status_code == 403
