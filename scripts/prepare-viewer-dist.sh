#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST="${1:-$ROOT/dist-viewer}"

python3 - "$ROOT/index.html" "$DIST/index.html" <<'PY'
import re
import sys
from pathlib import Path

src = Path(sys.argv[1]).read_text(encoding="utf-8")
dst = Path(sys.argv[2])
dst.parent.mkdir(parents=True, exist_ok=True)

html = src
html = html.replace(
    "'  <script>window.APP_MODE = \"view\";</script>\\n'",
    "'  <scr' + 'ipt>window.APP_MODE = \"view\";</scr' + 'ipt>\\n'",
)
html = html.replace(
    "\n  <script>window.APP_MODE = \"view\";</script>\n",
    "\n  <scr' + 'ipt>window.APP_MODE = \"view\";</scr' + 'ipt>\n",
)
main_open = re.search(r"<script>\s*\n\s*const APP_MODE", html)
if main_open:
    body_close = html.lower().rfind("</body>")
    if body_close >= 0:
        region = html[main_open.start() : body_close]
        if "</script>" not in region:
            html = html[:body_close] + "\n  </script>\n" + html[body_close:]

parts = re.split(r"</head>", html, maxsplit=1, flags=re.I)
if len(parts) == 2:
    after_head = parts[1]
    script_match = re.search(r"<script\b", after_head, re.I)
    before_script = after_head[: script_match.start()] if script_match else after_head
    from_script = after_head[script_match.start() :] if script_match else ""
    body_match = re.search(r"<body\b[^>]*>", before_script, re.I)
    if body_match:
        body_tag = body_match.group(0)
        if "viewer-mode" not in body_tag:
            if re.fullmatch(r"<body\s*>", body_tag, re.I):
                new_body_tag = '<body class="viewer-mode">'
            elif re.search(r"class=", body_tag, re.I):
                new_body_tag = re.sub(
                    r'class=(["\'])([^"\']*)\1',
                    r'class=\1\2 viewer-mode\1',
                    body_tag,
                    count=1,
                )
            else:
                new_body_tag = re.sub(
                    r"<body(\s[^>]*)>",
                    r'<body\1 class="viewer-mode">',
                    body_tag,
                    count=1,
                )
            before_script = before_script.replace(body_tag, new_body_tag, 1)
            html = parts[0] + "</head>" + before_script + from_script

head_html = html.split("</head>", 1)[0]
if "<!--viewer-deploy-boot-->" not in head_html:
    from datetime import datetime, timezone
    build_stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    boot = (
        f'  <!--viewer-build:{build_stamp}-->\n'
        '  <!--viewer-deploy-boot-->\n'
        '  <script>window.APP_MODE = "view";</script>\n'
    )
    html = re.sub(r"(</head>)", boot + r"\1", html, count=1)

html = re.sub(
    r"<title>[^<]*</title>",
    "<title>\u30c8\u30fc\u30ca\u30e1\u30f3\u30c8 \u30bf\u30a4\u30e0\u30c6\u30fc\u30d6\u30eb\uff08\u95b2\u89a7\uff09</title>",
    html,
    count=1,
)

dst.write_text(html, encoding="utf-8")
PY

cp "$ROOT/view.html" "$ROOT/netlify.toml" "$ROOT/_redirects" "$ROOT/viewer-deploy.js" "$DIST/"

if [[ "${COPY_PUBLISHED:-}" == "1" ]] && compgen -G "$ROOT/published/*.json" > /dev/null; then
  mkdir -p "$DIST/published"
  cp "$ROOT/published/"*.json "$DIST/published/"
fi
