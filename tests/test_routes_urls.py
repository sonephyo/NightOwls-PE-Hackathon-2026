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
        assert len(results) == 1
        # list endpoint uses recurse=False so user_id is returned as a plain integer
        assert all(u["user_id"] == sample_user["id"] for u in results)

    def test_filters_by_is_active_true(self, client, sample_user):
        client.post("/urls", json={"original_url": "https://active.com", "is_active": True, "user_id": sample_user["id"]})
        client.post("/urls", json={"original_url": "https://inactive.com", "is_active": False, "user_id": sample_user["id"]})
        resp = client.get("/urls?is_active=true")
        assert resp.status_code == 200
        results = resp.get_json()
        assert all(u["is_active"] is True for u in results)

    def test_filters_by_is_active_false(self, client, sample_user):
        client.post("/urls", json={"original_url": "https://active.com", "is_active": True, "user_id": sample_user["id"]})
        client.post("/urls", json={"original_url": "https://inactive.com", "is_active": False, "user_id": sample_user["id"]})
        resp = client.get("/urls?is_active=false")
        assert resp.status_code == 200
        results = resp.get_json()
        assert len(results) == 1
        assert all(u["is_active"] is False for u in results)

    def test_pagination_per_page(self, client, sample_user):
        for i in range(5):
            client.post("/urls", json={"original_url": f"https://x{i}.com", "user_id": sample_user["id"]})
        resp = client.get("/urls?per_page=3")
        assert len(resp.get_json()) == 3

    def test_click_count_field_present(self, client, sample_url):
        data = client.get("/urls").get_json()
        assert "click_count" in data[0]

    def test_click_count_increments_on_redirect(self, client, sample_url):
        client.get(f"/{sample_url['short_code']}")
        client.get(f"/{sample_url['short_code']}")
        data = client.get("/urls").get_json()
        assert data[0]["click_count"] == 2

    def test_filters_by_short_code(self, client, sample_user):
        client.post("/urls", json={"original_url": "https://a.com", "short_code": "aaaa11", "user_id": sample_user["id"]})
        client.post("/urls", json={"original_url": "https://b.com", "short_code": "bbbb22", "user_id": sample_user["id"]})
        resp = client.get("/urls?short_code=aaaa11")
        assert resp.status_code == 200
        results = resp.get_json()
        assert len(results) == 1
        assert results[0]["short_code"] == "aaaa11"

    def test_sort_by_created_at_desc(self, client, sample_user):
        for i in range(3):
            client.post("/urls", json={"original_url": f"https://s{i}.com", "user_id": sample_user["id"]})
        results = client.get("/urls?sort_by=created_at&order=desc").get_json()
        dates = [r["created_at"] for r in results]
        assert dates == sorted(dates, reverse=True)

    def test_sort_by_id_asc_default(self, client, sample_user):
        for i in range(3):
            client.post("/urls", json={"original_url": f"https://t{i}.com", "user_id": sample_user["id"]})
        results = client.get("/urls").get_json()
        ids = [r["id"] for r in results]
        assert ids == sorted(ids)


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

    def test_user_id_is_integer(self, client, sample_url, sample_user):
        data = client.get(f"/urls/{sample_url['id']}").get_json()
        assert data["user_id"] == sample_user["id"]

    def test_click_count_present(self, client, sample_url):
        data = client.get(f"/urls/{sample_url['id']}").get_json()
        assert "click_count" in data
        assert data["click_count"] == 0

    def test_click_count_reflects_redirects(self, client, sample_url):
        client.get(f"/{sample_url['short_code']}")
        data = client.get(f"/urls/{sample_url['id']}").get_json()
        assert data["click_count"] == 1


# ---------------------------------------------------------------------------
# GET /urls/<short_code>  (lookup by short code, no redirect)
# ---------------------------------------------------------------------------

class TestGetUrlByShortCode:
    def test_returns_url_info(self, client, sample_url):
        resp = client.get(f"/urls/{sample_url['short_code']}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["short_code"] == sample_url["short_code"]
        assert data["original_url"] == sample_url["original_url"]

    def test_returns_404_for_unknown_short_code(self, client):
        resp = client.get("/urls/doesnotexist")
        assert resp.status_code == 404

    def test_does_not_redirect(self, client, sample_url):
        resp = client.get(f"/urls/{sample_url['short_code']}")
        assert resp.status_code == 200
        assert "Location" not in resp.headers

    def test_includes_click_count(self, client, sample_url):
        client.get(f"/{sample_url['short_code']}")
        resp = client.get(f"/urls/{sample_url['short_code']}")
        assert resp.get_json()["click_count"] == 1

    def test_includes_is_active(self, client, sample_url):
        data = client.get(f"/urls/{sample_url['short_code']}").get_json()
        assert "is_active" in data


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

    def test_returns_409_when_explicit_short_code_already_exists(self, client, sample_user):
        """When the given short_code already exists, return 409 Conflict."""
        uid = sample_user["id"]
        client.post("/urls", json={"original_url": "https://a.com", "short_code": "dup123", "user_id": uid})
        resp = client.post("/urls", json={"original_url": "https://b.com", "short_code": "dup123", "user_id": uid})
        assert resp.status_code == 409
        assert "error" in resp.get_json()

    def test_auto_generates_unique_short_code_when_no_code_given(self, client, sample_user):
        """Without explicit short_code, auto-generation always produces a unique code."""
        uid = sample_user["id"]
        resp1 = client.post("/urls", json={"original_url": "https://a.com", "user_id": uid})
        resp2 = client.post("/urls", json={"original_url": "https://b.com", "user_id": uid})
        assert resp1.status_code == 201
        assert resp2.status_code == 201
        assert resp1.get_json()["short_code"] != resp2.get_json()["short_code"]

    def test_returns_400_when_url_is_not_http(self, client, sample_user):
        resp = client.post("/urls", json={"original_url": "ftp://bad.com", "user_id": sample_user["id"]})
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_returns_400_when_url_has_no_scheme(self, client, sample_user):
        resp = client.post("/urls", json={"original_url": "example.com", "user_id": sample_user["id"]})
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_create_response_includes_click_count(self, client, sample_user):
        resp = client.post("/urls", json={"original_url": "https://x.com", "user_id": sample_user["id"]})
        assert resp.status_code == 201
        assert resp.get_json()["click_count"] == 0

    def test_create_response_user_id_is_integer(self, client, sample_user):
        resp = client.post("/urls", json={"original_url": "https://x.com", "user_id": sample_user["id"]})
        assert resp.get_json()["user_id"] == sample_user["id"]

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

    def test_returns_400_when_body_is_not_object(self, client):
        resp = client.post("/urls", json="not-an-object")
        assert resp.status_code == 400

    def test_returns_400_when_user_id_missing(self, client):
        resp = client.post("/urls", json={"original_url": "https://x.com"})
        assert resp.status_code == 400

    def test_returns_400_when_user_id_not_integer(self, client):
        resp = client.post("/urls", json={"original_url": "https://x.com", "user_id": "1"})
        assert resp.status_code == 400

    def test_returns_400_when_user_does_not_exist(self, client):
        resp = client.post("/urls", json={"original_url": "https://x.com", "user_id": 999999})
        assert resp.status_code == 400

    def test_accepts_explicit_short_code_with_symbols(self, client, sample_user):
        resp = client.post(
            "/urls",
            json={"original_url": "https://x.com", "short_code": "bad-code!", "user_id": sample_user["id"]},
        )
        assert resp.status_code == 201

    def test_returns_400_for_explicit_short_code_too_long(self, client, sample_user):
        resp = client.post(
            "/urls",
            json={"original_url": "https://x.com", "short_code": "abcdefghijk", "user_id": sample_user["id"]},
        )
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

    def test_returns_400_when_update_body_is_not_object(self, client, sample_url):
        resp = client.put(f"/urls/{sample_url['id']}", json="nope")
        assert resp.status_code == 400

    def test_ignores_unknown_fields_and_returns_200(self, client, sample_url):
        resp = client.put(f"/urls/{sample_url['id']}", json={"foo": "bar"})
        assert resp.status_code == 200

    def test_update_response_includes_click_count(self, client, sample_url):
        resp = client.put(f"/urls/{sample_url['id']}", json={"title": "new"})
        assert "click_count" in resp.get_json()


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

    def test_redirect_creates_click_event(self, client, sample_url):
        client.get(f"/{sample_url['short_code']}")
        events = client.get("/events").get_json()
        click_events = [e for e in events if e["event_type"] == "click"]
        assert len(click_events) == 1
        assert click_events[0]["url_id"] == sample_url["id"]

    def test_no_click_event_for_inactive_url(self, client, sample_url):
        client.put(f"/urls/{sample_url['id']}", json={"is_active": False})
        client.get(f"/{sample_url['short_code']}")
        events = client.get("/events").get_json()
        assert len(events) == 0


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


# ---------------------------------------------------------------------------
# GET /urls/<id>/stats
# ---------------------------------------------------------------------------

class TestUrlStats:
    def test_returns_200_for_existing_url(self, client, sample_url):
        resp = client.get(f"/urls/{sample_url['id']}/stats")
        assert resp.status_code == 200

    def test_returns_404_for_missing_url(self, client):
        resp = client.get("/urls/999999/stats")
        assert resp.status_code == 404

    def test_contains_expected_fields(self, client, sample_url):
        data = client.get(f"/urls/{sample_url['id']}/stats").get_json()
        for field in ("url_id", "short_code", "click_count", "unique_users", "last_clicked_at"):
            assert field in data

    def test_click_count_zero_initially(self, client, sample_url):
        data = client.get(f"/urls/{sample_url['id']}/stats").get_json()
        assert data["click_count"] == 0
        assert data["last_clicked_at"] is None

    def test_click_count_increments_on_redirect(self, client, sample_url):
        client.get(f"/{sample_url['short_code']}")
        client.get(f"/{sample_url['short_code']}")
        data = client.get(f"/urls/{sample_url['id']}/stats").get_json()
        assert data["click_count"] == 2

    def test_last_clicked_at_set_after_redirect(self, client, sample_url):
        client.get(f"/{sample_url['short_code']}")
        data = client.get(f"/urls/{sample_url['id']}/stats").get_json()
        assert data["last_clicked_at"] is not None

    def test_url_id_and_short_code_match(self, client, sample_url):
        data = client.get(f"/urls/{sample_url['id']}/stats").get_json()
        assert data["url_id"] == sample_url["id"]
        assert data["short_code"] == sample_url["short_code"]


# ---------------------------------------------------------------------------
# GET /urls/top
# ---------------------------------------------------------------------------

class TestTopUrls:
    def test_returns_list(self, client):
        resp = client.get("/urls/top")
        assert resp.status_code == 200
        assert isinstance(resp.get_json(), list)

    def test_ordered_by_click_count_desc(self, client, sample_user):
        url_a = client.post("/urls", json={"original_url": "https://a.com", "user_id": sample_user["id"]}).get_json()
        url_b = client.post("/urls", json={"original_url": "https://b.com", "user_id": sample_user["id"]}).get_json()
        # click b twice, a once
        client.get(f"/{url_b['short_code']}")
        client.get(f"/{url_b['short_code']}")
        client.get(f"/{url_a['short_code']}")
        results = client.get("/urls/top").get_json()
        ids = [u["id"] for u in results]
        assert ids.index(url_b["id"]) < ids.index(url_a["id"])

    def test_n_param_limits_results(self, client, sample_user):
        for i in range(5):
            client.post("/urls", json={"original_url": f"https://x{i}.com", "user_id": sample_user["id"]})
        results = client.get("/urls/top?n=3").get_json()
        assert len(results) == 3

    def test_each_result_has_click_count(self, client, sample_url):
        results = client.get("/urls/top").get_json()
        assert all("click_count" in u for u in results)
