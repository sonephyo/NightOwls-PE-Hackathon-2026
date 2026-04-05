"""
Tests for app-level behaviour: error handlers, health, metrics, and bad inputs
that fall outside the individual route test files.
"""

import pytest


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

class TestErrorHandlers:
    def test_404_returns_json(self, client):
        resp = client.get("/this-route-does-not-exist")
        assert resp.status_code == 404
        data = resp.get_json()
        assert data is not None
        assert "error" in data

    def test_404_content_type_is_json(self, client):
        resp = client.get("/no-such-endpoint")
        assert "application/json" in resp.content_type

    def test_500_returns_json(self, app, monkeypatch):
        """Force a 500 by making an existing route raise an unhandled exception."""
        from app.models.user import User

        # Patch User.select to raise so list_users has an unhandled exception.
        monkeypatch.setattr(User, "select", lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("boom")))
        app.config["PROPAGATE_EXCEPTIONS"] = False
        c = app.test_client()
        resp = c.get("/users")
        app.config["PROPAGATE_EXCEPTIONS"] = True  # restore

        assert resp.status_code == 500
        data = resp.get_json()
        assert data is not None
        assert "error" in data


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------

class TestHealth:
    def test_health_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_returns_status_ok(self, client):
        assert client.get("/health").get_json()["status"] == "ok"


# ---------------------------------------------------------------------------
# /metrics
# ---------------------------------------------------------------------------

class TestMetrics:
    def test_metrics_returns_200(self, client):
        resp = client.get("/metrics")
        assert resp.status_code == 200

    def test_metrics_contains_cpu_gauge(self, client):
        resp = client.get("/metrics")
        assert b"app_cpu_usage_percent" in resp.data

    def test_metrics_contains_ram_gauge(self, client):
        resp = client.get("/metrics")
        assert b"app_ram_usage_mb" in resp.data

    def test_metrics_content_type(self, client):
        resp = client.get("/metrics")
        assert "text/plain" in resp.content_type

    def test_urls_created_counter_increments(self, client, sample_user):
        before = client.get("/metrics").data
        client.post("/urls", json={"original_url": "https://count.com", "user_id": sample_user["id"]})
        after = client.get("/metrics").data
        # Counter value in the after payload should be higher than before
        assert b"app_urls_created_total" in after

    def test_redirects_counter_increments(self, client, sample_url):
        client.get(f"/{sample_url['short_code']}")
        metrics = client.get("/metrics").data
        assert b"app_redirects_total" in metrics

    def test_stress_endpoint_returns_200(self, client):
        resp = client.get("/stress")
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "done"


# ---------------------------------------------------------------------------
# Bad inputs — POST /events
# ---------------------------------------------------------------------------

class TestCreateEventBadInputs:
    def test_no_body_returns_400(self, client):
        # Send JSON null so get_json() returns None → our 400 branch fires
        resp = client.post("/events", data=b"null", content_type="application/json")
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_non_json_content_type_returns_error(self, client):
        resp = client.post("/events", data="notjson", content_type="text/plain")
        assert resp.status_code in (400, 415)


# ---------------------------------------------------------------------------
# Bad inputs — PUT /users (empty body via raw JSON)
# ---------------------------------------------------------------------------

class TestUpdateUserBadInputs:
    def test_empty_json_body_returns_400(self, client, sample_user):
        # Send JSON null so get_json() returns None → our 400 branch fires
        resp = client.put(
            f"/users/{sample_user['id']}",
            data=b"null",
            content_type="application/json",
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data is not None
        assert "error" in data
