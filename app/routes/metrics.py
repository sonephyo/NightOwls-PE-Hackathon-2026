import threading
import time

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

# System-level gauges — updated by background sampler thread
cpu_gauge = Gauge("app_cpu_usage_percent", "System CPU usage percent across all cores")
ram_gauge = Gauge("app_ram_usage_mb", "Flask process RSS memory usage in MB")

# Application counters — import and increment these in your route files.
# Example:
#   from app.routes.metrics import urls_created_total
#   urls_created_total.inc()
urls_created_total = Counter("app_urls_created_total", "Total URLs shortened")
redirects_total = Counter("app_redirects_total", "Total redirects served")

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests handled",
    ["method", "endpoint", "http_status"],
)


def _sample_metrics():
    while True:
        cpu = psutil.cpu_percent(interval=1)  # system-wide, blocks 1s
        ram = psutil.Process().memory_info().rss / 1024 / 1024
        cpu_gauge.set(cpu)
        ram_gauge.set(ram)
        time.sleep(1)  # total cycle ~2s


threading.Thread(target=_sample_metrics, daemon=True).start()


@metrics_bp.route("/metrics")
def metrics():
    log.info("metrics.scraped")
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

# Endpoint to bring cpu usage up 
@metrics_bp.route("/stress")
def stress():
    end = time.time() + 3
    while time.time() < end:
        _ = sum(i * i for i in range(10000))
    return {"status": "done"}
