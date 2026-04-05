# Incident Response — Gold Submission

## The Dashboard

**Evidence URL:** `<host_url>:3000/d/app-overview`

**Image:** [link](https://imgur.com/a/XdbBUNb)

**Notes:**
The Grafana dashboard tracks all four Golden Signals in one view — Latency (p50/p95/p99 percentiles), Traffic (requests/sec by endpoint), Errors (5xx error rate %), and Saturation (CPU % and RAM usage). The top row shows live stat panels for instant status at a glance — including a 2.32% error rate from the simulated load test. Below that, historical time-series graphs show the traffic spike and latency trends over time. All data is pulled from the /metrics endpoint via Prometheus, updated every 2 seconds.

---

## The Runbook

**Evidence URL:** [Runbook](link_to_runbook_here)

**Image:** [image_link_here]

**Notes:**
The runbook covers both critical alerts — `FlaskAppDown` and `HighErrorRate`. Each section walks through how to confirm the alert, diagnose the root cause, apply a fix, and verify recovery. It is written to be followed at 3 AM without context — every step has a command, every command has an expected output, and every dead end has a next step. Quick links to Grafana, Prometheus, and Alertmanager are at the top so the on-call engineer never has to remember a URL.

---

## Sherlock Mode

**Evidence URL:** [Youtube Link](https://youtu.be/OG62fIYyiCc) 

**Image:** [link](https://imgur.com/a/sherlock-mode-EztzJc8)

**Notes:**
To simulate an incident, we hammered `/stress` (CPU spikes) and `/test-error` (500 errors) simultaneously. Starting from the dashboard top row — App Status green, Error Rate red, Latency p95 elevated — we ruled out a crash and focused on errors. The Traffic panel showed requests still flowing, and the Saturation panel showed repeated CPU spikes correlating exactly with the error spike. Switching to the Logs dashboard confirmed the root cause: a flood of requests to `/stress` and `/test-error` starting at the same timestamp. The CPU saturation caused worker queuing, which produced the latency spike and 500 errors. Root cause identified using only the dashboard and logs.
