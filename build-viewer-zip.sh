#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

DIST="dist-viewer"
PUBLISHED_JSON="${1:-published/timetable.json}"
OUT="${2:-viewer.zip}"
OUT="$(basename "$OUT")"
if [[ "$OUT" != *.zip ]]; then
  OUT="${OUT}.zip"
fi

echo "=== Build ${OUT} for Netlify ==="

bash scripts/prepare-viewer-dist.sh "$DIST"

if [[ -n "${PUBLISHED_JSON}" && -f "${PUBLISHED_JSON}" ]]; then
  mkdir -p "$DIST/published"
  cp "${PUBLISHED_JSON}" "$DIST/published/timetable.json"
  echo "Included published data: ${PUBLISHED_JSON}"
else
  echo "WARNING: No published/timetable.json included."
  echo "  Copy your real timetable.json into published/ and re-run:"
  echo "  ./build-viewer-zip.sh published/timetable.json [output.zip]"
  echo "  Or pass a path from your previous viewer.zip."
fi

rm -f "$OUT"
(
  cd "$DIST"
  zip -r "../${OUT}" . -x "*.DS_Store"
)

bash scripts/diagnose-viewer-html.sh "$DIST/index.html"
if [[ -f "$DIST/published/timetable.json" ]]; then
  python3 - "$DIST/published/timetable.json" <<'PY'
import json, sys
from pathlib import Path
raw = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
days = len(raw.get("s") or []) if raw.get("v") in (4, 5) else len(raw.get("tournamentsByDay") or {})
print(f"Published days: {days}")
if days < 2:
    print("WARNING: timetable.json has fewer than 2 days.")
PY
fi

echo
echo "Created ${OUT}"
echo "Upload this zip to Netlify (Deploy manually)."
echo "If the timetable data is missing, include your real published/timetable.json first."
