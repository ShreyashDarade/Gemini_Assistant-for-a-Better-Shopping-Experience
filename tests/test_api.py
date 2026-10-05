from unittest.mock import AsyncMock, patch


def test_liveness_and_headers(client):
    r = client.get("/live")
    assert r.status_code == 200 and r.json() == {"alive": True}
    assert r.headers["X-Request-ID"]
    assert r.headers["X-Content-Type-Options"] == "nosniff"


def test_request_id_is_propagated(client):
    r = client.get("/live", headers={"X-Request-ID": "abc123"})
    assert r.headers["X-Request-ID"] == "abc123"


def test_readiness_checks_database(client):
    r = client.get("/ready")
    assert r.status_code == 200 and r.json() == {"ready": True}


def test_metrics_exposed(client):
    client.get("/live")
    body = client.get("/metrics").text
    assert "http_requests_total" in body


def test_chat_validation_error_shape(client):
    r = client.post("/api/v1/chat", json={"message": ""})
    assert r.status_code == 422
    assert r.json()["error_code"] == "VALIDATION_ERROR"


def test_chat_success_path(client):
    fake = {
        "success": True,
        "session_id": "s1",
        "response": {"message": "hi", "intent": "greeting", "intent_confidence": 0.9},
    }
    with patch("app.routers.chat.get_ai_engine") as get_engine:
        get_engine.return_value.process_query = AsyncMock(return_value=fake)
        r = client.post("/api/v1/chat", json={"message": "hello"})
    assert r.status_code == 200
    assert r.json()["message"] == "hi"


def test_chat_does_not_leak_internal_errors(client):
    with patch("app.routers.chat.get_ai_engine") as get_engine:
        get_engine.return_value.process_query = AsyncMock(side_effect=RuntimeError("secret"))
        r = client.post("/api/v1/chat", json={"message": "hello"})
    assert r.status_code == 500
    assert "secret" not in r.text


def test_products_search_empty_db(client):
    r = client.get("/api/v1/products")
    assert r.status_code == 200, r.text
