# Incident Response — Bronze Submission

## Structured Logging

**Evidence URL:** N/A — terminal output, no URL

**Image:** [Structured JSON Logs — All Three Severity Levels](https://imgur.com/a/VMnbIRR)

**Notes:**
The image shows that the app uses structured logging. Every log line is a JSON object with a severity level, event name, and timestamp, making logs filterable and readable by both humans and tools. All three severity levels are present — INFO for normal traffic, WARNING for bad requests, and ERROR for server failures. The logs are parsed by Loki and displayed in Grafana, allowing the team to access and query logs without SSH.

---

## Metrics Endpoint

**Evidence URL:** `<host_url>:8000/metrics`

**Image:** [Prometheus /metrics output + Grafana CPU/RAM Dashboard](https://imgur.com/a/Fc7D775)

**Notes:**
The first image shows the raw `/metrics` endpoint in Prometheus format, exposing CPU and RAM usage sampled every 2 seconds. The second image shows Grafana visualizing this data — turning the raw numbers into live gauges and historical graphs. The `/metrics` endpoint is the single source of truth that feeds the entire dashboard.

---

## Log Access Without SSH

**Evidence URL:** `<host_url>:3000/d/all-container-logs`

**Image:** [Grafana All Container Logs Dashboard](https://imgur.com/a/BpANq38)

**Notes:**
Logs are accessible without SSH via a Promtail → Loki → Grafana pipeline. Promtail reads container logs via the Docker socket, parses the `level` and `event` fields from the structured JSON, and ships them to Loki. The Grafana dashboard at `/dashboards` shows live log streams from every service in the stack — app, database, Prometheus, Alertmanager, and more — all in one place. Engineers can filter by severity or event name using LogQL queries without ever touching a terminal.