#!/usr/bin/env python3
import json
import re
import sys
import urllib.request
from pathlib import Path

NTFY_URL = "https://ntfy.sh/tournament-timetable-taka13music-events/json?poll=1"
SHEET_RE = re.compile(r"docs\.google\.com/spreadsheets/d/[a-zA-Z0-9-_]+", re.I)
SLUG_RE = re.compile(r"[^a-z0-9-]+")


def normalize_slug(raw):
    slug = SLUG_RE.sub("-", str(raw or "").strip().lower()).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug


def load_events(path):
    if not path.exists():
        return {"version": 1, "selectedId": None, "events": []}
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        data = {}
    events = data.get("events")
    if not isinstance(events, list):
        events = []
    return {
        "version": 1,
        "selectedId": data.get("selectedId"),
        "events": events,
    }


def fetch_ntfy():
    req = urllib.request.Request(NTFY_URL, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as res:
        text = res.read().decode("utf-8").strip()
    if not text:
        return []
    if text.startswith("["):
        rows = json.loads(text)
    else:
        rows = [json.loads(line) for line in text.splitlines() if line.strip()]
    records = []
    for row in rows:
        if row.get("event") not in (None, "message"):
            continue
        message = row.get("message", row)
        if isinstance(message, str):
            try:
                message = json.loads(message)
            except json.JSONDecodeError:
                continue
        if isinstance(message, dict):
            records.append(message)
    return records


def apply_updates(data, records):
    by_slug = {}
    for event in data.get("events") or []:
        slug = normalize_slug(event.get("slug") or event.get("name"))
        if slug:
            by_slug[slug] = event

    latest = {}
    for record in records:
        slug = normalize_slug(record.get("slug") or record.get("name"))
        if slug:
            latest[slug] = record

    for slug, record in latest.items():
        if record.get("deleted"):
            by_slug.pop(slug, None)
            continue
        url = str(record.get("sheetUrl") or "")
        if not SHEET_RE.search(url):
            continue
        existing = by_slug.get(slug) or {}
        by_slug[slug] = {
            "id": record.get("id") or existing.get("id") or f"evt-{slug}",
            "name": record.get("name") or existing.get("name") or slug,
            "slug": slug,
            "sheetUrl": url,
            "sheetStart": record.get("sheetStart") or existing.get("sheetStart") or "",
            "sheetEnd": record.get("sheetEnd") or existing.get("sheetEnd") or "",
        }

    events = list(by_slug.values())
    selected = data.get("selectedId")
    if selected and not any(event.get("id") == selected for event in events):
        selected = events[0]["id"] if events else None
    elif not selected and events:
        selected = events[0]["id"]
    return {"version": 1, "selectedId": selected, "events": events}


def main():
    path = Path("events.json")
    before = load_events(path)
    try:
        records = fetch_ntfy()
    except Exception as err:
        print(f"ntfy fetch failed: {err}", file=sys.stderr)
        return 0
    after = apply_updates(before, records)
    if json.dumps(before, sort_keys=True) == json.dumps(after, sort_keys=True):
        print("no event changes")
        return 0
    path.write_text(json.dumps(after, ensure_ascii=False, indent=2) + "\n")
    print("updated events.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
