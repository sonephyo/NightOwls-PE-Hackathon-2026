#!/bin/sh
# Substitute env vars into alertmanager config before starting.
# AlertManager does not expand environment variables natively.
sed "s|\${PAGERDUTY_ROUTING_KEY}|${PAGERDUTY_ROUTING_KEY}|g" \
  /etc/alertmanager/alertmanager.yml > /tmp/alertmanager.yml
exec /bin/alertmanager --config.file=/tmp/alertmanager.yml --storage.path=/alertmanager
