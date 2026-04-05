import os

import psutil
import structlog
from flask import Blueprint, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    generate_latest,
)

log = structlog.get_logger(__name__)

metrics_bp = Blueprint("metrics", __name__)

_process = psutil.Process(os.getpid())

# Process-level gauges — refreshed on every Prometheus scrape
cpu_gauge = Gauge("app_cpu_usage_percent", "Flask process CPU usage percent (one core = 100%)")
ram_gauge = Gauge("app_ram_usage_mb", "Flask process RSS memory usage in MB")

# Application counters — import and increment these in your route files.
# Example:
#   from app.routes.metrics import urls_created_total
#   urls_created_total.inc()
urls_created_total = Counter("app_urls_created_total", "Total URLs shortened")
redirects_total = Counter("app_redirects_total", "Total redirects served")
cache_hits_total = Counter("app_cache_hits_total", "Total Redis cache hits on redirect")


@metrics_bp.route("/metrics")
def metrics():
    cpu = _process.cpu_percent(interval=0.1)
    ram = _process.memory_info().rss / 1024 / 1024
    cpu_gauge.set(cpu)
    ram_gauge.set(ram)
    log.info("metrics.scraped", cpu=cpu, ram_mb=ram)
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)
