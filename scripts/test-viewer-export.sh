#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== Test viewer export pipeline ==="
bash scripts/prepare-viewer-dist.sh dist-viewer
if [[ -f published/timetable.json ]]; then
  mkdir -p dist-viewer/published
  cp published/timetable.json dist-viewer/published/
fi
bash scripts/diagnose-viewer-html.sh dist-viewer/index.html
./build-viewer-zip.sh published/timetable.json viewer-export-test.zip
bash scripts/check-viewer-zip.sh viewer-export-test.zip
rm -f viewer-export-test.zip
echo
echo "OK: viewer export pipeline passed"
