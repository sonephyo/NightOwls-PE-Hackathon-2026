"""
Tests for the /users routes.

Each test class maps to one endpoint.  The ``client`` and ``sample_user``
fixtures come from conftest.py and provide a clean database state per test.
"""

import io
import pytest


# ---------------------------------------------------------------------------
# GET /users
# ---------------------------------------------------------------------------

class TestListUsers:
    def test_returns_empty_list_when_no_users(self, client):
        resp = client.get("/users")
        assert resp.status_code == 200
        assert resp.get_json() == []

    def test_returns_all_users(self, client, sample_user):
        resp = client.get("/users")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 1
        assert data[0]["email"] == sample_user["email"]

    def test_pagination_per_page(self, client):
        for i in range(5):
            client.post("/users", json={"username": f"u{i}", "email": f"u{i}@x.com"})
        resp = client.get("/users?per_page=2")
        assert len(resp.get_json()) == 2

    def test_pagination_page_two(self, client):
        for i in range(4):
            client.post("/users", json={"username": f"u{i}", "email": f"u{i}@x.com"})
        page1 = {u["id"] for u in client.get("/users?page=1&per_page=2").get_json()}
        page2 = {u["id"] for u in client.get("/users?page=2&per_page=2").get_json()}
        assert page1.isdisjoint(page2)

    def test_response_is_list(self, client):
        assert isinstance(client.get("/users").get_json(), list)


# ---------------------------------------------------------------------------
# GET /users/<id>
# ---------------------------------------------------------------------------

class TestGetUser:
    def test_returns_user_by_id(self, client, sample_user):
        resp = client.get(f"/users/{sample_user['id']}")
        assert resp.status_code == 200
        assert resp.get_json()["email"] == sample_user["email"]

    def test_returns_404_for_missing_user(self, client):
        resp = client.get("/users/999999")
        assert resp.status_code == 404
        assert "error" in resp.get_json()

    def test_response_contains_expected_fields(self, client, sample_user):
        data = client.get(f"/users/{sample_user['id']}").get_json()
        for field in ("id", "username", "email", "created_at"):
            assert field in data


# ---------------------------------------------------------------------------
# POST /users
# ---------------------------------------------------------------------------

class TestCreateUser:
    def test_creates_user_successfully(self, client):
        resp = client.post("/users", json={"username": "bob", "email": "bob@x.com"})
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["username"] == "bob"
        assert data["email"] == "bob@x.com"

    def test_returns_400_when_body_is_empty(self, client):
        resp = client.post("/users", json={})
        assert resp.status_code == 400

    def test_returns_400_when_body_is_string(self, client):
        resp = client.post("/users", json="not-an-object")
        assert resp.status_code == 400

    def test_returns_400_when_unknown_field_present(self, client):
        resp = client.post(
            "/users",
            json={"username": "bob", "email": "bob@x.com", "role": "admin"},
        )
        assert resp.status_code == 400

    def test_returns_400_when_username_missing(self, client):
        resp = client.post("/users", json={"email": "x@x.com"})
        assert resp.status_code == 400

    def test_returns_400_when_email_missing(self, client):
        resp = client.post("/users", json={"username": "bob"})
        assert resp.status_code == 400

    def test_returns_400_when_username_not_string(self, client):
        resp = client.post("/users", json={"username": 123, "email": "x@x.com"})
        assert resp.status_code == 400

    def test_returns_400_when_email_not_string(self, client):
        resp = client.post("/users", json={"username": "bob", "email": 999})
        assert resp.status_code == 400

    def test_created_user_is_retrievable(self, client):
        resp = client.post("/users", json={"username": "carol", "email": "carol@x.com"})
        user_id = resp.get_json()["id"]
        fetched = client.get(f"/users/{user_id}")
        assert fetched.status_code == 200
        assert fetched.get_json()["email"] == "carol@x.com"

    def test_wrong_content_type_returns_error(self, client):
        # Flask 3 returns 415 Unsupported Media Type for wrong content-type
        resp = client.post("/users", data="notjson", content_type="text/plain")
        assert resp.status_code in (400, 415)

    def test_returns_400_when_email_has_no_at_sign(self, client):
        resp = client.post("/users", json={"username": "bob", "email": "notanemail"})
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_returns_400_when_username_is_whitespace(self, client):
        resp = client.post("/users", json={"username": "   ", "email": "bob@example.com"})
        assert resp.status_code == 400

    def test_returns_400_when_email_is_whitespace(self, client):
        resp = client.post("/users", json={"username": "bob", "email": "   "})
        assert resp.status_code == 400

    def test_returns_400_when_email_already_exists(self, client):
        client.post("/users", json={"username": "bob", "email": "dup@example.com"})
        resp = client.post("/users", json={"username": "alice", "email": "dup@example.com"})
        assert resp.status_code == 400

    def test_accepts_valid_email(self, client):
        resp = client.post("/users", json={"username": "bob", "email": "bob@example.com"})
        assert resp.status_code == 201


# ---------------------------------------------------------------------------
# PUT /users/<id>
# ---------------------------------------------------------------------------

class TestUpdateUser:
    def test_updates_username(self, client, sample_user):
        resp = client.put(
            f"/users/{sample_user['id']}", json={"username": "alice2"}
        )
        assert resp.status_code == 200
        assert resp.get_json()["username"] == "alice2"

    def test_updates_email(self, client, sample_user):
        resp = client.put(
            f"/users/{sample_user['id']}", json={"email": "new@x.com"}
        )
        assert resp.status_code == 200
        assert resp.get_json()["email"] == "new@x.com"

    def test_partial_update_leaves_other_fields_unchanged(self, client, sample_user):
        client.put(f"/users/{sample_user['id']}", json={"username": "newname"})
        data = client.get(f"/users/{sample_user['id']}").get_json()
        assert data["email"] == sample_user["email"]

    def test_returns_404_for_missing_user(self, client):
        resp = client.put("/users/999999", json={"username": "x"})
        assert resp.status_code == 404

    def test_returns_error_when_body_is_empty(self, client, sample_user):
        # json=None sends no body; Flask 3 may return 415 instead of 400
        resp = client.put(f"/users/{sample_user['id']}", json=None)
        assert resp.status_code in (400, 415)

    def test_returns_400_for_empty_object_payload(self, client, sample_user):
        resp = client.put(f"/users/{sample_user['id']}", json={})
        assert resp.status_code == 400

    def test_returns_400_for_unknown_update_field(self, client, sample_user):
        resp = client.put(f"/users/{sample_user['id']}", json={"role": "admin"})
        assert resp.status_code == 400

    def test_returns_400_when_updating_username_to_non_string(self, client, sample_user):
        resp = client.put(f"/users/{sample_user['id']}", json={"username": 123})
        assert resp.status_code == 400

    def test_returns_400_when_updating_email_to_invalid_format(self, client, sample_user):
        resp = client.put(f"/users/{sample_user['id']}", json={"email": "invalid"})
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# DELETE /users/<id>
# ---------------------------------------------------------------------------

class TestDeleteUser:
    def test_deletes_existing_user(self, client, sample_user):
        resp = client.delete(f"/users/{sample_user['id']}")
        assert resp.status_code == 200
        assert client.get(f"/users/{sample_user['id']}").status_code == 404

    def test_returns_404_for_missing_user(self, client):
        resp = client.delete("/users/999999")
        assert resp.status_code == 404

    def test_response_contains_message(self, client, sample_user):
        data = client.delete(f"/users/{sample_user['id']}").get_json()
        assert "message" in data


# ---------------------------------------------------------------------------
# POST /users/bulk
# ---------------------------------------------------------------------------

class TestBulkUploadUsers:
    CSV = (
        "id,username,email,created_at\n"
        "101,dave,dave@x.com,2024-01-01 00:00:00\n"
        "102,eve,eve@x.com,2024-01-02 00:00:00\n"
    )

    def test_inserts_rows_from_csv(self, client):
        data = {"file": (io.BytesIO(self.CSV.encode()), "users.csv")}
        resp = client.post("/users/bulk", data=data, content_type="multipart/form-data")
        assert resp.status_code == 201
        assert resp.get_json()["count"] == 2

    def test_users_are_queryable_after_bulk_insert(self, client):
        data = {"file": (io.BytesIO(self.CSV.encode()), "users.csv")}
        client.post("/users/bulk", data=data, content_type="multipart/form-data")
        users = client.get("/users").get_json()
        emails = {u["email"] for u in users}
        assert "dave@x.com" in emails
        assert "eve@x.com" in emails

    def test_returns_400_when_no_file_provided(self, client):
        resp = client.post("/users/bulk", data={}, content_type="multipart/form-data")
        assert resp.status_code == 400
