import logging

import structlog
from dotenv import load_dotenv
from flask import Flask, jsonify, request

from app.database import init_db
from app.routes import register_routes


def create_app():
    load_dotenv()

    _configure_logging()

    app = Flask(__name__)

    init_db(app)

    from app import models  # noqa: F401 - registers models with Peewee

    register_routes(app)

    @app.route("/health")
    def health():
        return jsonify(status="ok")

    @app.errorhandler(404)
    def not_found(e):
        log = structlog.get_logger(__name__)
        log.warning("not_found", path=request.path)
        return jsonify(error="not found"), 404

    @app.errorhandler(500)
    def server_error(e):
        log = structlog.get_logger(__name__)
        log.error("unhandled_exception", exc_info=True)
        return jsonify(error="internal server error"), 500

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
