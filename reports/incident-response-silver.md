# Incident Response — Silver Submission

## Alert Rules Configuration

**Evidence URL:** `<host_url>:9090/alerts`

**Image:** [link](https://imgur.com/a/NoL0EwN)

**Notes:**
Two alerts are configured in `monitoring/prometheus/alert_rules.yml`. `FlaskAppDown` fires when Prometheus cannot scrape `/metrics` for 1 consecutive minute — meaning the app is down or unreachable. `HighErrorRate` fires when HTTP 5xx responses exceed 10% of total traffic for 1 consecutive minute. Both are severity critical and only alert when a human needs to act, avoiding alert fatigue.

---

## Alert Channel Delivery

**Evidence URL:** N/A — configuration file

**Image:** [link](https://imgur.com/a/vmbswq2) 

**Notes:**
Alerts are routed through Alertmanager to Discord via webhook and PagerDuty for on-call escalation. When an incident fires, the team gets notified on Discord instantly and PagerDuty handles on-call escalation — email, SMS, and phone call to whoever is on shift. Both channels also receive a resolved notification when the incident clears, so the on-call engineer doesn't have to manually verify recovery.

---

## Alert Trigger Under 5 Minutes

**Evidence URL:** [Youtube Link](https://youtu.be/08FjRbQfeoM) 

**Image:** [link](https://imgur.com/a/q9JqYM2)

**Notes:**
In this recording, we intentionally stop the app container. This puts the FlaskAppDown alert into PENDING state, where Prometheus checks for 60 seconds to confirm the app is truly unreachable before firing. Once the 60 seconds elapse without recovery, the alert transitions to FIRING and Alertmanager sends a notification to Discord and PagerDuty. After restarting the app, the alert clears and both channels receive a resolved notification automatically.