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

echo "=== Tournament Timetable Deploy (Surge / Editor) ==="
echo "Editor URL: https://${DOMAIN}/"
echo

TOKEN="$(read_token)"

if ! token_valid "$TOKEN"; then
  echo "Surge login required. Enter your email and password."
  echo
  if command -v surge &>/dev/null; then
    surge logout 2>/dev/null || true
    surge login
  else
    npx --yes surge logout 2>/dev/null || true
    npx --yes surge login
  fi
  TOKEN="$(read_token)"
fi

if ! token_valid "$TOKEN"; then
  echo "Invalid Surge token. Run:"
  echo "  surge login"
  echo "  ./setup-and-deploy-surge.sh"
  exit 1
fi

if command -v surge &>/dev/null; then
  surge . "$DOMAIN" --token "$TOKEN"
else
  npx --yes surge . "$DOMAIN" --token "$TOKEN"
fi

echo
echo "Editor deployed: https://${DOMAIN}/"
