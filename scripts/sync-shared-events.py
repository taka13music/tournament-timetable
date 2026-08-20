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


def stamp(record):
    try:
        return int(record.get("updatedAt") or record.get("t") or 0)
    except (TypeError, ValueError):
        return 0


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
    by_id = {}
    by_slug = {}
    for event in data.get("events") or []:
        event_id = event.get("id")
        slug = normalize_slug(event.get("slug") or event.get("name"))
        if event_id:
            by_id[event_id] = event
        if slug:
            by_slug[slug] = event

    latest_by_id = {}
    latest_by_slug = {}
    for record in records:
        record_id = str(record.get("id") or "").strip()
        slug = normalize_slug(record.get("slug") or record.get("name"))
        rec_t = stamp(record)
        if record_id:
            prev = latest_by_id.get(record_id)
            if not prev or rec_t >= stamp(prev):
                latest_by_id[record_id] = record
        if slug:
            prev = latest_by_slug.get(slug)
            if not prev or rec_t >= stamp(prev):
                latest_by_slug[slug] = record

    def forget(event):
        if not event:
            return
        event_id = event.get("id")
        slug = normalize_slug(event.get("slug") or event.get("name"))
        if event_id:
            by_id.pop(event_id, None)
        if slug:
            by_slug.pop(slug, None)

    def upsert(record):
        slug = normalize_slug(record.get("slug") or record.get("name"))
        record_id = str(record.get("id") or "").strip()
        existing = (record_id and by_id.get(record_id)) or (slug and by_slug.get(slug)) or {}
        if record.get("deleted"):
            forget(existing)
            if slug:
                by_slug.pop(slug, None)
            return
        url = str(record.get("sheetUrl") or existing.get("sheetUrl") or "")
        if not SHEET_RE.search(url):
            return
        rec_t = stamp(record)
        exist_t = stamp(existing)
        if existing and rec_t < exist_t:
            return
        newer = record if rec_t >= exist_t else existing
        older = existing if newer is record else record
        new_event = {
            "id": record_id or existing.get("id") or f"evt-{slug}",
            "name": newer.get("name") or older.get("name") or slug,
            "slug": slug or normalize_slug(existing.get("slug") or existing.get("name")),
            "sheetUrl": url,
            "sheetStart": newer.get("sheetStart") or older.get("sheetStart") or "",
            "sheetEnd": newer.get("sheetEnd") or older.get("sheetEnd") or "",
            "updatedAt": max(rec_t, exist_t) or None,
        }
        if not new_event["updatedAt"]:
            new_event.pop("updatedAt", None)
        forget(existing)
        by_id[new_event["id"]] = new_event
        if new_event.get("slug"):
            by_slug[new_event["slug"]] = new_event

    seen_ids = set()
    for record in latest_by_id.values():
        upsert(record)
        if record.get("id"):
            seen_ids.add(str(record.get("id")))
    for record in latest_by_slug.values():
        if str(record.get("id") or "") in seen_ids:
            continue
        upsert(record)

    events = list(by_id.values())
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
