#!/usr/bin/env bash
set -euo pipefail

LOG_TAG="subboy-healthcheck"
STATE_DIR="/var/lib/subboy-healthcheck"
STAMP_FILE="$STATE_DIR/last-check"
mkdir -p "$STATE_DIR"

if [[ -f "$STAMP_FILE" ]]; then
  SINCE="@$(stat -c %Y "$STAMP_FILE")"
else
  SINCE="5 minutes ago"
fi
RUN_STARTED_EPOCH="$(date +%s)"

finish() {
  touch -d "@${RUN_STARTED_EPOCH}" "$STAMP_FILE"
}
trap finish EXIT

if ! systemctl is-active --quiet warp-svc; then
  logger -t "$LOG_TAG" "warp-svc is inactive, restarting warp-svc and subboy"
  systemctl restart warp-svc
  sleep 10
  systemctl restart subboy
  exit 0
fi

if ! systemctl is-active --quiet subboy; then
  logger -t "$LOG_TAG" "subboy is inactive, restarting subboy"
  systemctl restart subboy
  exit 0
fi

if journalctl -u subboy --since "$SINCE" --no-pager | grep -Eq 'ProxyError|Host unreachable|Network is unreachable|Connection refused|Request timeout|TelegramNetworkError|Failed to fetch updates'; then
  logger -t "$LOG_TAG" "recent proxy/network error in subboy logs since $SINCE, restarting warp-svc and subboy"
  systemctl restart warp-svc
  sleep 10
  systemctl restart subboy
fi
