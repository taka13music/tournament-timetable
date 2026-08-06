#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

VIEWER_DIST="dist-viewer"

run_netlify() {
  if command -v netlify &>/dev/null; then
    netlify "$@"
  else
    npx --yes netlify-cli "$@"
  fi
}

prepare_viewer_dist() {
  rm -rf "$VIEWER_DIST"
  bash scripts/prepare-viewer-dist.sh "$VIEWER_DIST"
}

if [[ -z "${NETLIFY_AUTH_TOKEN:-}" ]]; then
  echo "NETLIFY_AUTH_TOKEN is not set."
  echo "Run: ./setup-and-deploy-viewer.sh"
  exit 1
fi

if [[ -z "${NETLIFY_SITE_ID:-}" ]]; then
  echo "NETLIFY_SITE_ID is not set."
  echo "Run: ./setup-and-deploy-viewer.sh"
  exit 1
fi

prepare_viewer_dist

if [[ -f published/timetable.json ]]; then
  mkdir -p "$VIEWER_DIST/published"
  cp published/timetable.json "$VIEWER_DIST/published/"
  echo "Including published/timetable.json"
else
  echo "WARNING: published/timetable.json not found."
  echo "Netlify deploy may remove existing public data unless it remains on the site."
  echo "Place your timetable.json in published/ or run: ./build-viewer-zip.sh <path-to-timetable.json>"
fi

run_netlify deploy --prod --dir="$VIEWER_DIST"
echo "Viewer deployed via Netlify CLI."
