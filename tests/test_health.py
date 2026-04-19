"""Tests de la route /health."""


def test_health_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["database"] == "up"
    assert body["calendar_backend"] == "db"
    # La clé LLM factice est posée dans conftest; on vérifie que le flag remonte.
    assert body["llm_configured"] is True
