"""
Tests for the /urls routes and the short-code redirect route.
"""

import io
import pytest


# ---------------------------------------------------------------------------
# GET /urls
# ---------------------------------------------------------------------------

class TestListUrls:
    def test_returns_empty_list_when_no_urls(self, client):
        resp = client.get("/urls")
        assert resp.status_code == 200
        assert resp.get_json() == []

    def test_returns_created_url(self, client, sample_url):
        data = client.get("/urls").get_json()
        assert len(data) == 1
        assert data[0]["original_url"] == sample_url["original_url"]

    def test_filters_by_user_id(self, client, sample_user):
        # Create a second user with their own URL.
        other = client.post(
            "/users", json={"username": "bob", "email": "bob@x.com"}
        ).get_json()
        client.post("/urls", json={"original_url": "https://a.com", "user_id": sample_user["id"]})
        client.post("/urls", json={"original_url": "https://b.com", "user_id": other["id"]})

        resp = client.get(f"/urls?user_id={sample_user['id']}")
        assert resp.status_code == 200
        results = resp.get_json()
        # model_to_dict expands ForeignKeyField into a nested dict
        assert all(u["user_id"]["id"] == sample_user["id"] for u in results)

    def test_pagination_per_page(self, client, sample_user):
        for i in range(5):
            client.post("/urls", json={"original_url": f"https://x{i}.com", "user_id": sample_user["id"]})
        resp = client.get("/urls?per_page=3")
        assert len(resp.get_json()) == 3


# ---------------------------------------------------------------------------
# GET /urls/<id>
# ---------------------------------------------------------------------------

class TestGetUrl:
    def test_returns_url_by_id(self, client, sample_url):
        resp = client.get(f"/urls/{sample_url['id']}")
        assert resp.status_code == 200
        assert resp.get_json()["short_code"] == sample_url["short_code"]

    def test_returns_404_for_missing_url(self, client):
        resp = client.get("/urls/999999")
        assert resp.status_code == 404
        assert "error" in resp.get_json()

    def test_response_contains_expected_fields(self, client, sample_url):
        data = client.get(f"/urls/{sample_url['id']}").get_json()
        for field in ("id", "short_code", "original_url", "is_active"):
            assert field in data


# ---------------------------------------------------------------------------
# POST /urls
# ---------------------------------------------------------------------------

class TestCreateUrl:
    def test_creates_url_with_required_fields(self, client, sample_user):
        # user_id is required by the schema (ForeignKeyField without null=True)
        resp = client.post(
            "/urls",
            json={"original_url": "https://example.com", "user_id": sample_user["id"]},
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["original_url"] == "https://example.com"
        assert len(data["short_code"]) == 6  # auto-generated default length

    def test_accepts_custom_short_code(self, client, sample_user):
        resp = client.post(
            "/urls",
            json={
                "original_url": "https://x.com",
                "short_code": "custom",
                "user_id": sample_user["id"],
            },
        )
        assert resp.status_code == 201
        assert resp.get_json()["short_code"] == "custom"

    def test_auto_generates_unique_short_code_on_collision(self, client, sample_user):
        """When the given short_code already exists, a new one is generated."""
        uid = sample_user["id"]
        client.post("/urls", json={"original_url": "https://a.com", "short_code": "dup123", "user_id": uid})
        resp = client.post("/urls", json={"original_url": "https://b.com", "short_code": "dup123", "user_id": uid})
        assert resp.status_code == 201
        assert resp.get_json()["short_code"] != "dup123"

    def test_default_is_active_true(self, client, sample_user):
        resp = client.post("/urls", json={"original_url": "https://x.com", "user_id": sample_user["id"]})
        assert resp.get_json()["is_active"] is True

    def test_can_set_is_active_false(self, client, sample_user):
        resp = client.post(
            "/urls",
            json={"original_url": "https://x.com", "is_active": False, "user_id": sample_user["id"]},
        )
        assert resp.get_json()["is_active"] is False

    def test_returns_400_when_original_url_missing(self, client):
        resp = client.post("/urls", json={"title": "no url"})
        assert resp.status_code == 400

    def test_returns_400_when_body_is_empty(self, client):
        resp = client.post("/urls", json={})
        assert resp.status_code == 400

    def test_created_url_is_retrievable(self, client, sample_user):
        resp = client.post(
            "/urls",
            json={"original_url": "https://test.com", "user_id": sample_user["id"]},
        )
        url_id = resp.get_json()["id"]
        fetched = client.get(f"/urls/{url_id}")
        assert fetched.status_code == 200
        assert fetched.get_json()["original_url"] == "https://test.com"


# ---------------------------------------------------------------------------
# PUT /urls/<id>
# ---------------------------------------------------------------------------

class TestUpdateUrl:
    def test_updates_original_url(self, client, sample_url):
        resp = client.put(
            f"/urls/{sample_url['id']}", json={"original_url": "https://updated.com"}
        )
        assert resp.status_code == 200
        assert resp.get_json()["original_url"] == "https://updated.com"

    def test_updates_title(self, client, sample_url):
        resp = client.put(f"/urls/{sample_url['id']}", json={"title": "New Title"})
        assert resp.status_code == 200
        assert resp.get_json()["title"] == "New Title"

    def test_updates_is_active(self, client, sample_url):
        resp = client.put(f"/urls/{sample_url['id']}", json={"is_active": False})
        assert resp.status_code == 200
        assert resp.get_json()["is_active"] is False

    def test_partial_update_leaves_other_fields_unchanged(self, client, sample_url):
        original_url = sample_url["original_url"]
        client.put(f"/urls/{sample_url['id']}", json={"title": "changed"})
        data = client.get(f"/urls/{sample_url['id']}").get_json()
        assert data["original_url"] == original_url

    def test_returns_404_for_missing_url(self, client):
        resp = client.put("/urls/999999", json={"title": "x"})
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /urls/<id>
# ---------------------------------------------------------------------------

class TestDeleteUrl:
    def test_deletes_existing_url(self, client, sample_url):
        resp = client.delete(f"/urls/{sample_url['id']}")
        assert resp.status_code == 200
        assert client.get(f"/urls/{sample_url['id']}").status_code == 404

    def test_returns_404_for_missing_url(self, client):
        resp = client.delete("/urls/999999")
        assert resp.status_code == 404

    def test_response_contains_message(self, client, sample_url):
        data = client.delete(f"/urls/{sample_url['id']}").get_json()
        assert "message" in data


# ---------------------------------------------------------------------------
# GET /<short_code>  (redirect)
# ---------------------------------------------------------------------------

class TestRedirectUrl:
    def test_redirects_active_url(self, client, sample_url):
        resp = client.get(f"/{sample_url['short_code']}")
        assert resp.status_code == 302
        assert sample_url["original_url"] in resp.headers["Location"]

    def test_returns_410_for_inactive_url(self, client, sample_url):
        client.put(f"/urls/{sample_url['id']}", json={"is_active": False})
        resp = client.get(f"/{sample_url['short_code']}")
        assert resp.status_code == 410

    def test_returns_404_for_unknown_short_code(self, client):
        resp = client.get("/doesnotexist")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /urls/bulk
# ---------------------------------------------------------------------------

class TestBulkUploadUrls:
    def _csv(self, user_id):
        return (
            "id,user_id,short_code,original_url,title,is_active,created_at,updated_at\n"
            f"201,{user_id},bulk01,https://bulk1.com,Bulk One,TRUE,2024-01-01 00:00:00,2024-01-01 00:00:00\n"
            f"202,{user_id},bulk02,https://bulk2.com,Bulk Two,FALSE,2024-01-02 00:00:00,2024-01-02 00:00:00\n"
        )

    def test_inserts_rows_from_csv(self, client, sample_user):
        csv = self._csv(sample_user["id"])
        data = {"file": (io.BytesIO(csv.encode()), "urls.csv")}
        resp = client.post("/urls/bulk", data=data, content_type="multipart/form-data")
        assert resp.status_code == 201
        assert resp.get_json()["count"] == 2

    def test_urls_are_queryable_after_bulk_insert(self, client, sample_user):
        csv = self._csv(sample_user["id"])
        data = {"file": (io.BytesIO(csv.encode()), "urls.csv")}
        client.post("/urls/bulk", data=data, content_type="multipart/form-data")
        urls = client.get("/urls").get_json()
        short_codes = {u["short_code"] for u in urls}
        assert "bulk01" in short_codes
        assert "bulk02" in short_codes

    def test_is_active_parsed_correctly(self, client, sample_user):
        csv = self._csv(sample_user["id"])
        data = {"file": (io.BytesIO(csv.encode()), "urls.csv")}
        client.post("/urls/bulk", data=data, content_type="multipart/form-data")
        urls = {u["short_code"]: u for u in client.get("/urls").get_json()}
        assert urls["bulk01"]["is_active"] is True
        assert urls["bulk02"]["is_active"] is False

    def test_returns_400_when_no_file_provided(self, client):
        resp = client.post("/urls/bulk", data={}, content_type="multipart/form-data")
        assert resp.status_code == 400
