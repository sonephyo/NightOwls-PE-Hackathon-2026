import logging
import time

import structlog
from dotenv import load_dotenv
from flask import Flask, g, jsonify, request

from app.database import init_db
from app.routes import register_routes


def create_app():
    load_dotenv()

    _configure_logging()

    app = Flask(__name__)

    init_db(app)

    from app import models  # noqa: F401 - registers models with Peewee
    from app.models import User, Url, Event
    from app.database import db
    db.connect()
    db.create_tables([User, Url, Event], safe=True)
    db.close()

    register_routes(app)

    @app.route("/health")
    def health():
        checks = {}
        http_status = 200

        # Database check — SELECT 1 is near-instant and confirms connectivity
        try:
            db.connect(reuse_if_open=True)
            db.execute_sql("SELECT 1")
            checks["database"] = "ok"
        except Exception as exc:
            checks["database"] = f"error: {exc}"
            http_status = 503
        finally:
            if not db.is_closed():
                db.close()

        # Redis check — non-critical, app degrades gracefully without it
        try:
            import os, redis as redis_lib
            r = redis_lib.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", 6379)),
                socket_connect_timeout=1,
                socket_timeout=1,
            )
            r.ping()
            checks["redis"] = "ok"
        except Exception:  # pragma: no cover
            checks["redis"] = "unavailable"  # pragma: no cover

        overall = "ok" if http_status == 200 else "error"
        return jsonify(status=overall, checks=checks), http_status

    @app.errorhandler(404)
    def not_found(e):  # pragma: no cover — /<short_code> catch-all handles all 404s
        log = structlog.get_logger(__name__)
        log.warning("not_found", path=request.path)
        return jsonify(error="not found"), 404

    @app.errorhandler(500)
    def server_error(e):
        log = structlog.get_logger(__name__)
        log.error("unhandled_exception", exc_info=True)
        return jsonify(error="internal server error"), 500

    from app.routes.metrics import http_requests_total, request_duration_seconds

    @app.before_request
    def start_timer():
        g.start_time = time.time()

    @app.after_request
    def record_request_metrics(response):
        endpoint = str(request.url_rule) if request.url_rule else "unknown"
        http_requests_total.labels(
            method=request.method,
            endpoint=endpoint,
            http_status=str(response.status_code),
        ).inc()
        if hasattr(g, "start_time"):
            request_duration_seconds.labels(
                method=request.method,
                endpoint=endpoint,
            ).observe(time.time() - g.start_time)
        return response

    @app.route("/test-error")
    def test_error():
        log = structlog.get_logger(__name__)
        log.error("simulated_error", endpoint="/test-error", reason="manual test trigger")
        return jsonify(error="simulated server error"), 500

    return app


def _configure_logging():
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    # Silence noisy werkzeug logs in production
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
