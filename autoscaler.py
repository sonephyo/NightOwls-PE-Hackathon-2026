"""
Simple autoscaler for Docker Compose.
Scales based on p95 response time and request rate from Prometheus.

- Scales UP when p95 latency > 300ms OR request rate > 200 req/s
- Scales DOWN when p95 latency < 100ms AND request rate < 50 req/s

Usage:
    uv run autoscaler.py
"""

import subprocess
import time

import requests

# --- config ---
MIN_REPLICAS       = 2    # never go below this
MAX_REPLICAS       = 6    # never go above this
SCALE_UP_LATENCY   = 50   # CPU% — scale up if avg CPU exceeds this
SCALE_DOWN_LATENCY = 10   # CPU% — scale down if avg CPU drops below this
SCALE_UP_RPS       = 30   # req/s — scale up if redirect rate exceeds this
SCALE_DOWN_RPS     = 10   # req/s — scale down if redirect rate drops below this
POLL_INTERVAL      = 10   # seconds between checks
PROMETHEUS_URL     = "http://localhost:9090"

current_replicas = MIN_REPLICAS
low_load_streak  = 0       # consecutive low-load readings before scaling down
SCALE_DOWN_AFTER = 3       # require N consecutive low readings to scale down


def query(promql: str) -> float:
    """Run a PromQL query and return the scalar result."""
    try:
        resp = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": promql},
            timeout=5,
        )
        data = resp.json()
        results = data.get("data", {}).get("result", [])
        if results:
            return float(results[0]["value"][1])
    except Exception as e:
        print(f"[autoscaler] Prometheus query failed: {e}")
    return 0.0


def get_p95_latency_ms() -> float:
    """Use CPU as a proxy for latency — it's what the app exposes."""
    return query("avg(app_cpu_usage_percent)")


def get_request_rate() -> float:
    """Redirects per second over the last 30s."""
    return query("sum(rate(app_redirects_total[30s]))")


def scale(n: int):
    """Scale app service to n replicas."""
    print(f"[autoscaler] Scaling app to {n} replicas...")
    subprocess.run(
        ["docker", "compose", "up", "--scale", f"app={n}", "-d", "--no-recreate"],
        check=True,
    )


def main():
    global current_replicas
    print(f"[autoscaler] Starting. Min={MIN_REPLICAS} Max={MAX_REPLICAS}")
    print(f"[autoscaler] ScaleUp: cpu>{SCALE_UP_LATENCY}% OR rps>{SCALE_UP_RPS}")
    print(f"[autoscaler] ScaleDown: cpu<{SCALE_DOWN_LATENCY}% AND rps<{SCALE_DOWN_RPS}")

    while True:
        global low_load_streak
        p95 = get_p95_latency_ms()
        rps = get_request_rate()
        print(f"[autoscaler] cpu={p95:.1f}% | rps={rps:.1f} | replicas={current_replicas}")

        if (p95 > SCALE_UP_LATENCY or rps > SCALE_UP_RPS) and current_replicas < MAX_REPLICAS:
            low_load_streak = 0
            current_replicas += 1
            print(f"[autoscaler] HIGH load — scaling UP to {current_replicas}")
            scale(current_replicas)

        elif p95 < SCALE_DOWN_LATENCY and rps < SCALE_DOWN_RPS and current_replicas > MIN_REPLICAS:
            low_load_streak += 1
            print(f"[autoscaler] LOW load streak={low_load_streak}/{SCALE_DOWN_AFTER}")
            if low_load_streak >= SCALE_DOWN_AFTER:
                low_load_streak = 0
                current_replicas -= 1
                print(f"[autoscaler] Scaling DOWN to {current_replicas}")
                scale(current_replicas)
        else:
            low_load_streak = 0

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
