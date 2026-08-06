#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

SITE_NAME="${NETLIFY_SITE_NAME:-tournament-timetable}"
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

echo "=== Tournament Timetable Deploy (Netlify / Viewer) ==="
echo "Viewer URL: https://${SITE_NAME}.netlify.app/view.html"
echo

prepare_viewer_dist

if [[ -f published/timetable.json ]]; then
  mkdir -p "$VIEWER_DIST/published"
  cp published/timetable.json "$VIEWER_DIST/published/"
  echo "Including published/timetable.json"
else
  echo "WARNING: published/timetable.json not found in this folder."
  echo "Copy your real timetable.json into published/ before deploying,"
  echo "or run: ./build-viewer-zip.sh <path-to-timetable.json>"
fi

if [[ ! -f .netlify/state.json ]]; then
  echo "First-time setup: login and link this folder to your Netlify site."
  echo
  run_netlify login
  echo
  echo "Link to an existing site, or create one:"
  echo "  netlify sites:create --name ${SITE_NAME}"
  echo "  netlify link"
  echo
  run_netlify link
fi

run_netlify deploy --prod --dir="$VIEWER_DIST"
echo
echo "Viewer deployed. Check the URL shown above or your Netlify dashboard."
