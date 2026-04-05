"""
Integration tests: hit the API then query the DB directly to confirm persistence.

These tests go one level deeper than the route tests — instead of just checking
the HTTP response, they open the DB and verify the row was actually written,
updated, or deleted correctly.
"""

import io
import pytest
from app.models.url import Url
from app.models.user import User
from app.models.event import Event


# ---------------------------------------------------------------------------
# POST /urls  →  check DB
# ---------------------------------------------------------------------------

class TestShortenIntegration:
    def test_post_shorten_persists_to_db(self, client, sample_user):
        resp = client.post("/urls", json={
            "original_url": "https://example.com",
            "user_id": sample_user["id"],
        })
        assert resp.status_code == 201
        short_code = resp.get_json()["short_code"]

        row = Url.get(Url.short_code == short_code)
        assert row.original_url == "https://example.com"
        assert row.is_active is True

    def test_custom_short_code_stored_in_db(self, client, sample_user):
        client.post("/urls", json={
            "original_url": "https://custom.com",
            "short_code": "mycode",
            "user_id": sample_user["id"],
        })

        row = Url.get(Url.short_code == "mycode")
        assert row.original_url == "https://custom.com"

    def test_is_active_false_stored_in_db(self, client, sample_user):
        resp = client.post("/urls", json={
            "original_url": "https://inactive.com",
            "is_active": False,
            "user_id": sample_user["id"],
        })
        short_code = resp.get_json()["short_code"]

        row = Url.get(Url.short_code == short_code)
        assert row.is_active is False

    def test_title_stored_in_db(self, client, sample_user):
        resp = client.post("/urls", json={
            "original_url": "https://titled.com",
            "title": "My Title",
            "user_id": sample_user["id"],
        })
        short_code = resp.get_json()["short_code"]

        row = Url.get(Url.short_code == short_code)
        assert row.title == "My Title"

    def test_user_id_linked_in_db(self, client, sample_user):
        resp = client.post("/urls", json={
            "original_url": "https://linked.com",
            "user_id": sample_user["id"],
        })
        short_code = resp.get_json()["short_code"]

        row = Url.get(Url.short_code == short_code)
        assert row.user_id_id == sample_user["id"]


# ---------------------------------------------------------------------------
# PUT /urls/<id>  →  check DB
# ---------------------------------------------------------------------------

class TestUpdateUrlIntegration:
    def test_update_persists_to_db(self, client, sample_url):
        client.put(f"/urls/{sample_url['id']}", json={"original_url": "https://updated.com"})

        row = Url.get_by_id(sample_url["id"])
        assert row.original_url == "https://updated.com"

    def test_deactivate_persists_to_db(self, client, sample_url):
        client.put(f"/urls/{sample_url['id']}", json={"is_active": False})

        row = Url.get_by_id(sample_url["id"])
        assert row.is_active is False


# ---------------------------------------------------------------------------
# DELETE /urls/<id>  →  check DB
# ---------------------------------------------------------------------------

class TestDeleteUrlIntegration:
    def test_delete_removes_row_from_db(self, client, sample_url):
        url_id = sample_url["id"]
        client.delete(f"/urls/{url_id}")

        assert Url.select().where(Url.id == url_id).count() == 0


# ---------------------------------------------------------------------------
# POST /users  →  check DB
# ---------------------------------------------------------------------------

class TestCreateUserIntegration:
    def test_post_user_persists_to_db(self, client):
        resp = client.post("/users", json={"username": "integration", "email": "int@test.com"})
        assert resp.status_code == 201
        user_id = resp.get_json()["id"]

        row = User.get_by_id(user_id)
        assert row.username == "integration"
        assert row.email == "int@test.com"

    def test_delete_user_removes_from_db(self, client, sample_user):
        client.delete(f"/users/{sample_user['id']}")

        assert User.select().where(User.id == sample_user["id"]).count() == 0


# ---------------------------------------------------------------------------
# POST /events  →  check DB
# ---------------------------------------------------------------------------

class TestCreateEventIntegration:
    def test_post_event_persists_to_db(self, client, sample_user, sample_url):
        resp = client.post("/events", json={
            "url_id": sample_url["id"],
            "user_id": sample_user["id"],
            "event_type": "click",
            "details": {"browser": "chrome"},
        })
        assert resp.status_code == 201
        event_id = resp.get_json()["id"]

        row = Event.get_by_id(event_id)
        assert row.event_type == "click"
        assert row.url_id_id == sample_url["id"]
        assert row.user_id_id == sample_user["id"]

    def test_event_details_stored_as_json_string(self, client, sample_user, sample_url):
        resp = client.post("/events", json={
            "url_id": sample_url["id"],
            "user_id": sample_user["id"],
            "event_type": "view",
            "details": {"os": "mac"},
        })
        event_id = resp.get_json()["id"]

        row = Event.get_by_id(event_id)
        # Details are stored as a JSON string in the DB
        import json
        assert json.loads(row.details) == {"os": "mac"}


# ---------------------------------------------------------------------------
# GET /<short_code>  →  redirect creates event in DB
# ---------------------------------------------------------------------------

class TestRedirectIntegration:
    def test_redirect_creates_event_in_db(self, client, sample_url):
        client.get(f"/{sample_url['short_code']}")

        events = Event.select().where(
            (Event.url_id == sample_url["id"]) & (Event.event_type == "click")
        )
        assert events.count() == 1

    def test_deactivated_url_returns_404_and_no_event(self, client, sample_url):
        client.put(f"/urls/{sample_url['id']}", json={"is_active": False})
        resp = client.get(f"/{sample_url['short_code']}")

        assert resp.status_code == 404
        assert Event.select().where(Event.url_id == sample_url["id"]).count() == 0

    def test_deleted_url_returns_404(self, client, sample_url):
        short_code = sample_url["short_code"]
        client.delete(f"/urls/{sample_url['id']}")
        resp = client.get(f"/{short_code}")

        assert resp.status_code == 404
        assert Url.select().where(Url.short_code == short_code).count() == 0


# ---------------------------------------------------------------------------
# User update  →  check DB
# ---------------------------------------------------------------------------

class TestUpdateUserIntegration:
    def test_update_user_persists_to_db(self, client, sample_user):
        client.put(f"/users/{sample_user['id']}", json={"username": "newname"})

        row = User.get_by_id(sample_user["id"])
        assert row.username == "newname"

    def test_get_user_by_id_after_create(self, client):
        resp = client.post("/users", json={"username": "gettest", "email": "gettest@x.com"})
        user_id = resp.get_json()["id"]

        row = User.get_by_id(user_id)
        assert row.email == "gettest@x.com"

    def test_update_email_persists_to_db(self, client, sample_user):
        client.put(f"/users/{sample_user['id']}", json={"email": "new@example.com"})

        row = User.get_by_id(sample_user["id"])
        assert row.email == "new@example.com"

    def test_get_user_api_matches_db(self, client, sample_user):
        resp = client.get(f"/users/{sample_user['id']}")
        api_data = resp.get_json()
        row = User.get_by_id(sample_user["id"])
        assert api_data["username"] == row.username
        assert api_data["email"] == row.email


# ---------------------------------------------------------------------------
# Events  →  additional DB checks
# ---------------------------------------------------------------------------

class TestEventIntegration:
    def test_redirect_event_count_increments_in_db(self, client, sample_url):
        client.get(f"/{sample_url['short_code']}")
        client.get(f"/{sample_url['short_code']}")

        count = Event.select().where(
            (Event.url_id == sample_url["id"]) & (Event.event_type == "click")
        ).count()
        assert count == 2

    def test_get_event_by_id_after_create(self, client, sample_user, sample_url):
        resp = client.post("/events", json={
            "url_id": sample_url["id"],
            "user_id": sample_user["id"],
            "event_type": "share",
        })
        event_id = resp.get_json()["id"]

        row = Event.get_by_id(event_id)
        assert row.event_type == "share"
        assert row.url_id_id == sample_url["id"]

    def test_event_user_id_stored_in_db(self, client, sample_user, sample_url):
        resp = client.post("/events", json={
            "url_id": sample_url["id"],
            "user_id": sample_user["id"],
            "event_type": "click",
        })
        event_id = resp.get_json()["id"]

        row = Event.get_by_id(event_id)
        assert row.user_id_id == sample_user["id"]

    def test_event_without_user_stored_in_db(self, client, sample_url):
        resp = client.post("/events", json={
            "url_id": sample_url["id"],
            "event_type": "view",
        })
        event_id = resp.get_json()["id"]

        row = Event.get_by_id(event_id)
        assert row.user_id_id is None


# ---------------------------------------------------------------------------
# URL stats  →  DB-backed counts
# ---------------------------------------------------------------------------

class TestUrlStatsIntegration:
    def test_stats_click_count_matches_db(self, client, sample_url):
        client.get(f"/{sample_url['short_code']}")
        client.get(f"/{sample_url['short_code']}")

        stats = client.get(f"/urls/{sample_url['id']}/stats").get_json()
        db_count = Event.select().where(
            (Event.url_id == sample_url["id"]) & (Event.event_type == "click")
        ).count()
        assert stats["click_count"] == db_count == 2

    def test_stats_last_clicked_at_matches_db(self, client, sample_url):
        client.get(f"/{sample_url['short_code']}")

        stats = client.get(f"/urls/{sample_url['id']}/stats").get_json()
        last_event = Event.select().where(
            Event.url_id == sample_url["id"]
        ).order_by(Event.timestamp.desc()).first()
        assert stats["last_clicked_at"] == last_event.timestamp.isoformat()

    def test_stats_unique_users_matches_db(self, client, sample_url, sample_user):
        # same user clicks twice — unique count should be 1
        client.get(f"/{sample_url['short_code']}?user_id={sample_user['id']}")
        client.get(f"/{sample_url['short_code']}?user_id={sample_user['id']}")

        stats = client.get(f"/urls/{sample_url['id']}/stats").get_json()
        assert stats["unique_users"] == 1


# ---------------------------------------------------------------------------
# Bulk upload  →  verify rows land in DB
# ---------------------------------------------------------------------------

class TestBulkIntegration:
    def test_bulk_users_persist_to_db(self, client):
        csv = "id,username,email,created_at\n201,bulkuser1,bulk1@x.com,2024-01-01 00:00:00\n202,bulkuser2,bulk2@x.com,2024-01-02 00:00:00\n"
        data = {"file": (io.BytesIO(csv.encode()), "users.csv")}
        client.post("/users/bulk", data=data, content_type="multipart/form-data")

        assert User.select().where(User.email == "bulk1@x.com").count() == 1
        assert User.select().where(User.email == "bulk2@x.com").count() == 1

    def test_bulk_urls_persist_to_db(self, client, sample_user):
        csv = (
            "id,user_id,short_code,original_url,title,is_active,created_at,updated_at\n"
            f"301,{sample_user['id']},blk01,https://bulk1.com,Bulk,TRUE,2024-01-01 00:00:00,2024-01-01 00:00:00\n"
            f"302,{sample_user['id']},blk02,https://bulk2.com,Bulk2,FALSE,2024-01-02 00:00:00,2024-01-02 00:00:00\n"
        )
        data = {"file": (io.BytesIO(csv.encode()), "urls.csv")}
        client.post("/urls/bulk", data=data, content_type="multipart/form-data")

        assert Url.select().where(Url.short_code == "blk01").count() == 1
        row = Url.get(Url.short_code == "blk02")
        assert row.is_active is False


# ---------------------------------------------------------------------------
# Top URLs  →  ordering backed by DB click counts
# ---------------------------------------------------------------------------

class TestTopUrlsIntegration:
    def test_top_urls_order_matches_db_click_counts(self, client, sample_user):
        url_a = client.post("/urls", json={"original_url": "https://a.com", "user_id": sample_user["id"]}).get_json()
        url_b = client.post("/urls", json={"original_url": "https://b.com", "user_id": sample_user["id"]}).get_json()

        client.get(f"/{url_b['short_code']}")
        client.get(f"/{url_b['short_code']}")
        client.get(f"/{url_a['short_code']}")

        results = client.get("/urls/top").get_json()
        ids = [u["id"] for u in results]
        assert ids.index(url_b["id"]) < ids.index(url_a["id"])

        db_b = Event.select().where(Event.url_id == url_b["id"]).count()
        db_a = Event.select().where(Event.url_id == url_a["id"]).count()
        assert db_b == 2
        assert db_a == 1


# ---------------------------------------------------------------------------
# Events summary  →  counts match DB
# ---------------------------------------------------------------------------

class TestEventsSummaryIntegration:
    def test_summary_counts_match_db(self, client, sample_user, sample_url):
        client.post("/events", json={"url_id": sample_url["id"], "user_id": sample_user["id"], "event_type": "click"})
        client.post("/events", json={"url_id": sample_url["id"], "user_id": sample_user["id"], "event_type": "click"})
        client.post("/events", json={"url_id": sample_url["id"], "user_id": sample_user["id"], "event_type": "view"})

        summary = client.get("/events/summary").get_json()
        db_total = Event.select().count()
        assert summary["total"] == db_total
        assert summary["by_type"]["click"] == 2
        assert summary["by_type"]["view"] == 1
