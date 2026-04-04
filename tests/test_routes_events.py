"""
Tests for the /events routes.
"""

import io
import pytest


# ---------------------------------------------------------------------------
# GET /events
# ---------------------------------------------------------------------------

class TestListEvents:
    def test_returns_empty_list_when_no_events(self, client):
        resp = client.get("/events")
        assert resp.status_code == 200
        assert resp.get_json() == []

    def test_returns_created_event(self, client, sample_event):
        data = client.get("/events").get_json()
        assert len(data) == 1
        assert data[0]["event_type"] == sample_event["event_type"]

    def test_pagination_per_page(self, client, sample_user, sample_url):
        for i in range(5):
            client.post(
                "/events",
                json={
                    "url_id": sample_url["id"],
                    "user_id": sample_user["id"],
                    "event_type": f"type{i}",
                },
            )
        resp = client.get("/events?per_page=3")
        assert len(resp.get_json()) == 3

    def test_response_is_list(self, client):
        assert isinstance(client.get("/events").get_json(), list)

    def test_filters_by_url_id(self, client, sample_user, sample_url):
        other_url = client.post(
            "/urls", json={"original_url": "https://other.com", "user_id": sample_user["id"]}
        ).get_json()
        client.post("/events", json={"url_id": sample_url["id"], "user_id": sample_user["id"], "event_type": "click"})
        client.post("/events", json={"url_id": other_url["id"], "user_id": sample_user["id"], "event_type": "view"})
        resp = client.get(f"/events?url_id={sample_url['id']}")
        assert resp.status_code == 200
        results = resp.get_json()
        assert len(results) == 1
        assert all(e["url_id"] == sample_url["id"] for e in results)

    def test_filters_by_user_id(self, client, sample_user, sample_url):
        other_user = client.post(
            "/users", json={"username": "bob", "email": "bob@x.com"}
        ).get_json()
        client.post("/events", json={"url_id": sample_url["id"], "user_id": sample_user["id"], "event_type": "click"})
        client.post("/events", json={"url_id": sample_url["id"], "user_id": other_user["id"], "event_type": "view"})
        resp = client.get(f"/events?user_id={sample_user['id']}")
        assert resp.status_code == 200
        results = resp.get_json()
        assert len(results) == 1
        assert all(e["user_id"] == sample_user["id"] for e in results)

    def test_filters_by_event_type(self, client, sample_user, sample_url):
        client.post("/events", json={"url_id": sample_url["id"], "user_id": sample_user["id"], "event_type": "click"})
        client.post("/events", json={"url_id": sample_url["id"], "user_id": sample_user["id"], "event_type": "view"})
        resp = client.get("/events?event_type=click")
        assert resp.status_code == 200
        results = resp.get_json()
        assert len(results) == 1
        assert results[0]["event_type"] == "click"

    def test_returns_400_for_non_integer_url_id_filter(self, client):
        resp = client.get("/events?url_id=abc")
        assert resp.status_code == 400

    def test_returns_400_for_non_integer_user_id_filter(self, client):
        resp = client.get("/events?user_id=abc")
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# GET /events/<id>
# ---------------------------------------------------------------------------

class TestGetEvent:
    def test_returns_event_by_id(self, client, sample_event):
        resp = client.get(f"/events/{sample_event['id']}")
        assert resp.status_code == 200
        assert resp.get_json()["event_type"] == sample_event["event_type"]

    def test_returns_404_for_missing_event(self, client):
        resp = client.get("/events/999999")
        assert resp.status_code == 404
        assert "error" in resp.get_json()

    def test_response_contains_expected_fields(self, client, sample_event):
        data = client.get(f"/events/{sample_event['id']}").get_json()
        for field in ("id", "event_type", "timestamp"):
            assert field in data

    def test_timestamp_is_present(self, client, sample_event):
        data = client.get(f"/events/{sample_event['id']}").get_json()
        assert data.get("timestamp") is not None

    def test_details_are_deserialized_to_dict(self, client, sample_event):
        data = client.get(f"/events/{sample_event['id']}").get_json()
        # sample_event was created with details={"browser": "firefox"}
        assert isinstance(data["details"], dict)
        assert data["details"]["browser"] == "firefox"


# ---------------------------------------------------------------------------
# POST /events
# ---------------------------------------------------------------------------

class TestCreateEvent:
    def test_creates_event_with_required_fields(self, client, sample_user, sample_url):
        resp = client.post(
            "/events",
            json={
                "url_id": sample_url["id"],
                "user_id": sample_user["id"],
                "event_type": "view",
            },
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["event_type"] == "view"

    def test_creates_event_with_details(self, client, sample_user, sample_url):
        resp = client.post(
            "/events",
            json={
                "url_id": sample_url["id"],
                "user_id": sample_user["id"],
                "event_type": "click",
                "details": {"referrer": "google"},
            },
        )
        assert resp.status_code == 201
        # details should round-trip as a dict
        assert resp.get_json()["details"] == {"referrer": "google"}

    def test_creates_event_without_details(self, client, sample_user, sample_url):
        resp = client.post(
            "/events",
            json={
                "url_id": sample_url["id"],
                "user_id": sample_user["id"],
                "event_type": "view",
            },
        )
        assert resp.status_code == 201
        assert resp.get_json()["details"] is None

    def test_returns_error_when_body_is_empty(self, client):
        resp = client.post("/events", json=None)
        assert resp.status_code in (400, 415)

    def test_returns_400_when_body_is_string(self, client):
        resp = client.post("/events", json="not-an-object")
        assert resp.status_code == 400

    def test_returns_400_when_body_is_list(self, client):
        resp = client.post("/events", json=["not", "an", "object"])
        assert resp.status_code == 400

    def test_returns_400_when_url_id_missing(self, client, sample_user):
        resp = client.post("/events", json={"user_id": sample_user["id"], "event_type": "click"})
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_returns_400_when_event_type_missing(self, client, sample_user, sample_url):
        resp = client.post("/events", json={"url_id": sample_url["id"], "user_id": sample_user["id"]})
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_returns_400_when_unknown_field_present(self, client, sample_user, sample_url):
        resp = client.post(
            "/events",
            json={
                "url_id": sample_url["id"],
                "user_id": sample_user["id"],
                "event_type": "click",
                "malicious": "junk",
            },
        )
        assert resp.status_code == 400

    def test_returns_404_when_url_id_does_not_exist(self, client, sample_user):
        resp = client.post(
            "/events",
            json={"url_id": 999999, "user_id": sample_user["id"], "event_type": "click"},
        )
        assert resp.status_code == 404

    def test_returns_404_when_user_id_does_not_exist(self, client, sample_url):
        resp = client.post(
            "/events",
            json={"url_id": sample_url["id"], "user_id": 999999, "event_type": "click"},
        )
        assert resp.status_code == 404

    def test_returns_400_when_event_type_is_whitespace(self, client, sample_user, sample_url):
        resp = client.post(
            "/events",
            json={"url_id": sample_url["id"], "user_id": sample_user["id"], "event_type": "   "},
        )
        assert resp.status_code == 400

    def test_timestamp_is_present_in_response(self, client, sample_user, sample_url):
        resp = client.post("/events", json={"url_id": sample_url["id"], "user_id": sample_user["id"], "event_type": "click"})
        assert resp.status_code == 201
        assert resp.get_json().get("timestamp") is not None

    def test_timestamp_is_set_automatically(self, client, sample_user, sample_url):
        resp = client.post(
            "/events",
            json={
                "url_id": sample_url["id"],
                "user_id": sample_user["id"],
                "event_type": "download",
            },
        )
        assert resp.status_code == 201
        assert resp.get_json().get("timestamp") is not None

    def test_returns_400_when_user_id_is_string(self, client, sample_url):
        resp = client.post(
            "/events",
            json={
                "url_id": sample_url["id"],
                "user_id": "notanint",
                "event_type": "click",
            },
        )
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_returns_400_when_user_id_is_boolean(self, client, sample_url):
        resp = client.post(
            "/events",
            json={
                "url_id": sample_url["id"],
                "user_id": True,
                "event_type": "click",
            },
        )
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_returns_400_when_details_is_string(self, client, sample_user, sample_url):
        resp = client.post(
            "/events",
            json={
                "url_id": sample_url["id"],
                "user_id": sample_user["id"],
                "event_type": "click",
                "details": "not a dict",
            },
        )
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_returns_400_when_details_is_integer(self, client, sample_user, sample_url):
        resp = client.post(
            "/events",
            json={
                "url_id": sample_url["id"],
                "user_id": sample_user["id"],
                "event_type": "click",
                "details": 42,
            },
        )
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_returns_400_when_details_is_list(self, client, sample_user, sample_url):
        resp = client.post(
            "/events",
            json={
                "url_id": sample_url["id"],
                "user_id": sample_user["id"],
                "event_type": "click",
                "details": ["not", "an", "object"],
            },
        )
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_accepts_details_as_dict(self, client, sample_user, sample_url):
        resp = client.post(
            "/events",
            json={
                "url_id": sample_url["id"],
                "user_id": sample_user["id"],
                "event_type": "click",
                "details": {"key": "value"},
            },
        )
        assert resp.status_code == 201
        assert resp.get_json()["details"] == {"key": "value"}

    def test_created_event_is_retrievable(self, client, sample_user, sample_url):
        resp = client.post(
            "/events",
            json={
                "url_id": sample_url["id"],
                "user_id": sample_user["id"],
                "event_type": "share",
            },
        )
        event_id = resp.get_json()["id"]
        fetched = client.get(f"/events/{event_id}")
        assert fetched.status_code == 200
        assert fetched.get_json()["event_type"] == "share"


# ---------------------------------------------------------------------------
# POST /events/bulk
# ---------------------------------------------------------------------------

class TestBulkUploadEvents:
    def _csv(self, url_id, user_id):
        return (
            "id,url_id,user_id,event_type,timestamp,details\n"
            f"301,{url_id},{user_id},click,2024-06-01 12:00:00,\n"
            f"302,{url_id},{user_id},view,2024-06-02 08:00:00,\n"
        )

    def test_inserts_rows_from_csv(self, client, sample_user, sample_url):
        csv = self._csv(sample_url["id"], sample_user["id"])
        data = {"file": (io.BytesIO(csv.encode()), "events.csv")}
        resp = client.post("/events/bulk", data=data, content_type="multipart/form-data")
        assert resp.status_code == 201
        assert resp.get_json()["count"] == 2

    def test_events_are_queryable_after_bulk_insert(self, client, sample_user, sample_url):
        csv = self._csv(sample_url["id"], sample_user["id"])
        data = {"file": (io.BytesIO(csv.encode()), "events.csv")}
        client.post("/events/bulk", data=data, content_type="multipart/form-data")
        events = client.get("/events").get_json()
        event_types = {e["event_type"] for e in events}
        assert "click" in event_types
        assert "view" in event_types

    def test_returns_400_when_no_file_provided(self, client):
        resp = client.post("/events/bulk", data={}, content_type="multipart/form-data")
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# GET /events/summary
# ---------------------------------------------------------------------------

class TestEventsSummary:
    def test_returns_200(self, client):
        resp = client.get("/events/summary")
        assert resp.status_code == 200

    def test_empty_when_no_events(self, client):
        data = client.get("/events/summary").get_json()
        assert data["total"] == 0
        assert data["by_type"] == {}

    def test_counts_by_type(self, client, sample_user, sample_url):
        client.post("/events", json={"url_id": sample_url["id"], "user_id": sample_user["id"], "event_type": "click"})
        client.post("/events", json={"url_id": sample_url["id"], "user_id": sample_user["id"], "event_type": "click"})
        client.post("/events", json={"url_id": sample_url["id"], "user_id": sample_user["id"], "event_type": "view"})
        data = client.get("/events/summary").get_json()
        assert data["total"] == 3
        assert data["by_type"]["click"] == 2
        assert data["by_type"]["view"] == 1

    def test_filters_by_url_id(self, client, sample_user, sample_url):
        other_url = client.post("/urls", json={"original_url": "https://other.com", "user_id": sample_user["id"]}).get_json()
        client.post("/events", json={"url_id": sample_url["id"], "user_id": sample_user["id"], "event_type": "click"})
        client.post("/events", json={"url_id": other_url["id"], "user_id": sample_user["id"], "event_type": "view"})
        data = client.get(f"/events/summary?url_id={sample_url['id']}").get_json()
        assert data["total"] == 1
        assert data["by_type"] == {"click": 1}

    def test_summary_returns_400_for_non_integer_url_id_filter(self, client):
        resp = client.get("/events/summary?url_id=abc")
        assert resp.status_code == 400

    def test_summary_returns_400_for_non_integer_user_id_filter(self, client):
        resp = client.get("/events/summary?user_id=abc")
        assert resp.status_code == 400

    def test_contains_total_and_by_type_fields(self, client):
        data = client.get("/events/summary").get_json()
        assert "total" in data
        assert "by_type" in data


# ---------------------------------------------------------------------------
# GET /health  (sanity check)
# ---------------------------------------------------------------------------

class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.get_json() == {"status": "ok"}
