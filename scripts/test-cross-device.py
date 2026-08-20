#!/usr/bin/env python3
"""Serve a clean-origin copy of the app with shared JSON fixtures and check HTTP."""
from __future__ import annotations

import json
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVENT_ID = "evt-sample-cup"
SLUG = "sample-cup"
FIXTURE_EVENTS = {
    "version": 1,
    "selectedId": EVENT_ID,
    "events": [
        {
            "id": EVENT_ID,
            "name": "Sample Cup",
            "slug": SLUG,
            "sheetUrl": "https://docs.google.com/spreadsheets/d/1mT9Y1FVd0l9bbyxNmYAkJYLaEK3JDCeaIb9BSJuuOv8/edit",
            "sheetStart": "Main Day 1A",
            "sheetEnd": "Finale",
        }
    ],
}
FIXTURE_PUBLISHED = {
    "version": 5,
    "mode": "snapshot-live",
    "eventId": SLUG,
    "eventName": "Sample Cup",
    "publishedAt": "2026-08-20T02:00:00.000Z",
    "sheetUrl": "https://docs.google.com/spreadsheets/d/1mT9Y1FVd0l9bbyxNmYAkJYLaEK3JDCeaIb9BSJuuOv8/edit",
    "sheetStart": "Main Day 1A",
    "sheetEnd": "Finale",
    "hourHeight": 60,
    "selectedDay": "9/10",
    "dayTabItems": [{"id": "9/10", "label": "9/10(木)"}],
    "tournamentsByDay": {
        "9/10": [
            {
                "name": "Main Day 1A",
                "fee": "¥60,000",
                "chips": "50,000",
                "sheetName": "Main Day 1A",
                "blocks": [
                    {
                        "type": "level",
                        "label": "100-200",
                        "startMin": 1080,
                        "endMin": 1140,
                        "levelNum": 1,
                    }
                ],
            }
        ]
    },
}


def source_has(marker: str) -> None:
    html = (ROOT / "index.html").read_text()
    if marker not in html:
        raise SystemExit(f"missing {marker} in index.html")


def main() -> int:
    source_has("function fetchSharedJson")
    source_has("function tryRestorePublishedTimetable")
    source_has("function loadViewerConfigFromEventsJson")
    source_has("function fetchGithubContentsJson")
    source_has("function mergeEventPair")
    source_has("function overlaySharedEventName")
    source_has("function filterDeletedEvents")

    tmp = Path(tempfile.mkdtemp(prefix="tt-cross-device-"))
    shutil.copy(ROOT / "index.html", tmp / "index.html")
    (tmp / "events.json").write_text(json.dumps(FIXTURE_EVENTS, ensure_ascii=False, indent=2) + "\n")
    published = tmp / "published"
    published.mkdir()
    (published / f"{SLUG}.json").write_text(
        json.dumps(FIXTURE_PUBLISHED, ensure_ascii=False, indent=2) + "\n"
    )

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(tmp), **kwargs)

        def log_message(self, format, *args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    import threading

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.2)
    base = f"http://127.0.0.1:{port}"

    def get(path: str) -> tuple[int, str]:
        req = urllib.request.Request(base + path, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=5) as res:
                return res.status, res.read().decode()
        except urllib.error.HTTPError as err:
            return err.code, err.read().decode()

    status, body = get("/events.json")
    assert status == 200, status
    events = json.loads(body)
    assert events["events"][0]["slug"] == SLUG, events

    status, body = get(f"/published/{SLUG}.json")
    assert status == 200, status
    published_json = json.loads(body)
    assert "Main Day 1A" in json.dumps(published_json)

    status, body = get("/index.html")
    assert status == 200, status
    assert "tryRestorePublishedTimetable" in body

    print(f"CROSS_DEVICE_OK {base}")
    print(f"VIEW {base}/?mode=view&event={SLUG}")
    print(f"ADMIN {base}/#/")
    print(f"DIR {tmp}")
    if "--serve" in sys.argv:
        print("serving until interrupt")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
    server.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
