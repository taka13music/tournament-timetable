#!/usr/bin/env bash
set -euo pipefail

TARGET="${1:-dist-viewer/index.html}"

if [[ ! -f "$TARGET" ]]; then
  echo "Usage: $0 [path/to/index.html]"
  echo "File not found: $TARGET"
  exit 1
fi

python3 - "$TARGET" <<'PY'
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
html = path.read_text(encoding="utf-8")
head = html.split("</head>", 1)[0]
issues = []
ok = []

if "<!--viewer-deploy-boot-->" in head:
    ok.append("head ? viewer ?????????")
else:
    issues.append("head ? <!--viewer-deploy-boot--> ????????????????")

after_head = html.split("</head>", 1)[-1]
body_match = re.search(r"<body\b[^>]*>", after_head)
body_tag = body_match.group(0) if body_match else ""
if body_tag and re.search(r"\bviewer-mode\b", body_tag):
    ok.append("body.viewer-mode ??")
else:
    issues.append(f"body ? viewer-mode ?????? ({body_tag or 'not found'})")

redirects = Path(path.parent / "_redirects")
if redirects.is_file():
    text = redirects.read_text(encoding="utf-8")
    if "/index.html    /view.html" in text:
        issues.append("_redirects ??????index.html ? view.html????")
    elif "/    /index.html" in text:
        ok.append("_redirects ? index.html ??")
    else:
        issues.append("_redirects ????????????")
else:
    issues.append("_redirects ?????????")

m = re.search(r"<script>\s*\n\s*const APP_MODE", html)
if not m:
    issues.append("??? script ???????")
else:
    body = html[m.start() + 8 : html.find("</script>", m.start())]
    if "</script>" in body.lower():
        issues.append("script ?? </script> ??? HTML ???????")
    else:
        ok.append(f"??? script ??? OK ({len(body)} bytes)")

    last = html.rfind("</script>")
    tail = html[last + 9 :].strip()
    if "setupViewerMode" in tail or "${escapeHtml" in tail:
        issues.append("?????? JS ???????????????????")
    else:
        ok.append("JS ????")

stamp = re.search(r"<!--viewer-build:([^>]+)-->", head)
if stamp:
    ok.append(f"????: {stamp.group(1)}")
else:
    issues.append("???? <!--viewer-build:...--> ?????? Zip ?????")

print(f"=== {path} ===")
for line in ok:
    print(f"OK  {line}")
for line in issues:
    print(f"NG  {line}")

if issues:
    print("\nResult: BROKEN")
    sys.exit(1)
print("\nResult: OK")
PY
