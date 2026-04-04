"""
Shared pytest fixtures for the MLH PE Hackathon test suite.

Strategy
--------
The production app connects to PostgreSQL via Peewee's DatabaseProxy.
For tests we patch ``app.database.PostgresqlDatabase`` so that
``init_db()`` initialises the proxy with a file-backed SQLite database
instead.  A file-backed database (rather than ``:memory:``) is used
because Flask closes the connection after every request; reopening a
``:memory:`` connection would create a brand-new, empty database.

All fixtures that touch the database use ``reuse_if_open=True`` so
they can be called whether or not a connection is already open.
"""

import io
import pytest
from peewee import SqliteDatabase
from unittest.mock import patch


# ---------------------------------------------------------------------------
# App / database setup
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def app(tmp_path_factory):
    """Create a Flask application wired to a temporary SQLite database."""
    db_path = str(tmp_path_factory.mktemp("db") / "test.db")
    test_db = SqliteDatabase(db_path, pragmas={"foreign_keys": 0})

    # Patch PostgresqlDatabase in app.database so init_db uses SQLite.
    with patch("app.database.PostgresqlDatabase", return_value=test_db):
        from app import create_app
        flask_app = create_app()

    flask_app.config["TESTING"] = True

    # Create all tables once for the entire test session.
    from app.models.user import User
    from app.models.url import Url
    from app.models.event import Event

    test_db.connect(reuse_if_open=True)
    test_db.create_tables([User, Url, Event], safe=True)
    test_db.close()

    return flask_app


@pytest.fixture(autouse=True)
def clean_tables():
    """Delete all rows from every table before each test."""
    from app.database import db
    from app.models.event import Event
    from app.models.url import Url
    from app.models.user import User

    db.connect(reuse_if_open=True)
    Event.delete().execute()
    Url.delete().execute()
    User.delete().execute()
    db.close()
    yield


# ---------------------------------------------------------------------------
# HTTP client
# ---------------------------------------------------------------------------

@pytest.fixture
def client(app):
    """Return a Flask test client."""
    return app.test_client()


# ---------------------------------------------------------------------------
# Convenience data fixtures (created via the API so they go through the
# full request lifecycle, including DB connection management).
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_user(client):
    """A persisted User created through the API."""
    resp = client.post(
        "/users",
        json={"username": "alice", "email": "alice@example.com"},
    )
    assert resp.status_code == 201
    return resp.get_json()


@pytest.fixture
def sample_url(client, sample_user):
    """A persisted, active Url created through the API."""
    resp = client.post(
        "/urls",
        json={
            "original_url": "https://example.com",
            "short_code": "testcd",
            "title": "Example",
            "user_id": sample_user["id"],
        },
    )
    assert resp.status_code == 201
    return resp.get_json()


@pytest.fixture
def sample_event(client, sample_user, sample_url):
    """A persisted Event created through the API."""
    resp = client.post(
        "/events",
        json={
            "url_id": sample_url["id"],
            "user_id": sample_user["id"],
            "event_type": "click",
            "details": {"browser": "firefox"},
        },
    )
    assert resp.status_code == 201
    return resp.get_json()


# ---------------------------------------------------------------------------
# CSV helper
# ---------------------------------------------------------------------------

def make_csv_upload(csv_text: str, filename: str = "upload.csv"):
    """Return a (data, content_type) tuple suitable for client.post()."""
    data = {"file": (io.BytesIO(csv_text.encode()), filename)}
    return data, "multipart/form-data"
