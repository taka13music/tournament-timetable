#!/usr/bin/env bash
set -euo pipefail

ZIP="${1:-viewer.zip}"
TMP="$(mktemp -d)"

cleanup() { rm -rf "$TMP"; }
trap cleanup EXIT

if [[ ! -f "$ZIP" ]]; then
  echo "Usage: $0 [path/to/viewer.zip]"
  echo "File not found: $ZIP"
  exit 1
fi

echo "=== Checking $ZIP ==="
unzip -q "$ZIP" -d "$TMP"

if [[ ! -f "$TMP/index.html" ]]; then
  if [[ -f "$TMP/dist-viewer/index.html" ]]; then
    echo "NG  Zip ????1???????dist-viewer/index.html??"
    echo "    cd dist-viewer && zip -r ../viewer.zip . ???????????"
    exit 1
  fi
  echo "NG  Zip ????? index.html ??????"
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
bash "$ROOT/scripts/diagnose-viewer-html.sh" "$TMP/index.html"

python3 - "$TMP/published/timetable.json" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
if not path.is_file():
    print("NG  published/timetable.json ? Zip ?????????")
    sys.exit(1)

raw = json.loads(path.read_text(encoding="utf-8"))
size = path.stat().st_size
print(f"OK  published/timetable.json ({size} bytes)")

if raw.get("v") in (4, 5):
    days = raw.get("s") or []
    print(f"OK  ???????: compact v{raw['v']}, ??: {len(days)}")
    if len(days) < 2:
        print("NG  ???1??????????????????????????")
elif raw.get("tournamentsByDay"):
    keys = list(raw["tournamentsByDay"].keys())
    print(f"OK  ???????: expanded, ??: {len(keys)}")
    if len(keys) < 2:
        print("NG  ???1?????????")
else:
    print("NG  ?????????????")
PY

echo
echo "Zip check finished."
