import os
from urllib.parse import urlparse

from peewee import DatabaseProxy, Model
from playhouse.pool import PooledPostgresqlDatabase

db = DatabaseProxy()


class BaseModel(Model):
    class Meta:
        database = db


def init_db(app):
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        parsed = urlparse(database_url)
        db_name = parsed.path.lstrip("/")
        db_host = parsed.hostname
        db_port = parsed.port or 5432
        db_user = parsed.username
        db_password = parsed.password
    else:
        db_name = os.environ.get("DATABASE_NAME", "hackathon_db")
        db_host = os.environ.get("DATABASE_HOST", "localhost")
        db_port = int(os.environ.get("DATABASE_PORT", 5432))
        db_user = os.environ.get("DATABASE_USER", "postgres")
        db_password = os.environ.get("DATABASE_PASSWORD", "postgres")

    # Connection pool: keeps connections alive across requests instead of
    # opening/closing on every request. Each gthread worker thread gets its
    # own connection from the pool.
    database = PooledPostgresqlDatabase(
        db_name,
        host=db_host,
        port=db_port,
        user=db_user,
        password=db_password,
        max_connections=20,      # per Gunicorn worker process
        stale_timeout=300,       # recycle connections idle > 5 min
        timeout=10,              # wait up to 10s for a free connection
    )
    db.initialize(database)

    @app.before_request
    def _db_connect():
        db.connect(reuse_if_open=True)

    @app.teardown_appcontext
    def _db_close(exc):
        if not db.is_closed():
            db.close()  # returns connection to pool, doesn't actually close it
