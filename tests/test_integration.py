"""
Integration tests: hit the API then query the DB directly to confirm persistence.

These tests go one level deeper than the route tests — instead of just checking
the HTTP response, they open the DB and verify the row was actually written,
updated, or deleted correctly.
"""

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
