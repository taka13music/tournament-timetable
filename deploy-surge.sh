#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

DOMAIN="tournament-timetable.surge.sh"

read_token() {
  awk '/machine surge.surge.sh/{found=1} found && $1=="password"{print $2; exit}' "${HOME}/.netrc" 2>/dev/null || true
}

token_valid() {
  local token="$1"
  [[ -n "$token" ]] || return 1
  surge list --token "$token" >/dev/null 2>&1
}

SURGE_TOKEN="${SURGE_TOKEN:-$(read_token)}"

if [[ -z "$SURGE_TOKEN" ]]; then
  echo "SURGE_TOKEN is not set."
  echo "Run: ./setup-and-deploy-surge.sh"
  exit 1
fi

if ! token_valid "$SURGE_TOKEN"; then
  echo "Invalid Surge token."
  echo "Run: ./setup-and-deploy-surge.sh"
  exit 1
fi

if command -v surge &>/dev/null; then
  surge . "$DOMAIN" --token "$SURGE_TOKEN"
else
  npx --yes surge . "$DOMAIN" --token "$SURGE_TOKEN"
fi

echo "Editor deployed: https://${DOMAIN}/"
