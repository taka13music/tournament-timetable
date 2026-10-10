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
        return {"version": 1, "selectedId": None, "events": [], "deleted": []}
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        data = {}
    events = data.get("events")
    if not isinstance(events, list):
        events = []
    deleted = data.get("deleted")
    if not isinstance(deleted, list):
        deleted = []
    return {
        "version": 1,
        "selectedId": data.get("selectedId"),
        "events": events,
        "deleted": deleted,
    }


def deleted_key(record):
    return str(record.get("id") or "").strip() or normalize_slug(record.get("slug") or record.get("name"))


def merge_deleted(existing, incoming):
    by_key = {}
    for rec in list(existing or []) + list(incoming or []):
        if not isinstance(rec, dict):
            continue
        key = deleted_key(rec)
        if not key:
            continue
        prev = by_key.get(key)
        if not prev or stamp(rec) >= stamp(prev):
            by_key[key] = {
                "id": str(rec.get("id") or "").strip(),
                "slug": normalize_slug(rec.get("slug") or rec.get("name")),
                "t": stamp(rec),
            }
    out = [rec for rec in by_key.values() if rec.get("id") or rec.get("slug")]
    out.sort(key=lambda rec: rec.get("t") or 0, reverse=True)
    return out[:200]


def fetch_ntfy_rows():
    req = urllib.request.Request(NTFY_URL, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as res:
        text = res.read().decode("utf-8").strip()
    if not text:
        return []
    if text.startswith("["):
        rows = json.loads(text)
    else:
        rows = [json.loads(line) for line in text.splitlines() if line.strip()]
    return [row for row in rows if isinstance(row, dict)]


def records_from_rows(rows):
    records = []
    for row in rows:
        if is_snapshot_row(row):
            continue
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


def fetch_ntfy():
    return records_from_rows(fetch_ntfy_rows())


def is_snapshot_row(row):
    tags = row.get("tags") or []
    title = str(row.get("title") or "")
    return title == "snapshot" or (isinstance(tags, list) and "snapshot" in tags)


def snapshot_slug(name):
    filename = str(name or "")
    if not filename.endswith(".json"):
        return ""
    slug = normalize_slug(filename[: -len(".json")])
    if not slug or f"{slug}.json" != filename:
        return ""
    return slug


def payload_time(payload):
    try:
        return int(payload.get("t") or 0)
    except (TypeError, ValueError):
        return 0


def write_snapshot_payload(dest, payload):
    if not isinstance(payload, dict) or payload.get("v") not in (4, 5):
        return False
    days = payload.get("s")
    if not isinstance(days, list) or not days:
        return False
    incoming_t = payload_time(payload)
    if dest.exists():
        try:
            old = json.loads(dest.read_text())
        except (OSError, json.JSONDecodeError):
            old = None
        if isinstance(old, dict):
            old_body = {key: value for key, value in old.items() if key != "t"}
            new_body = {key: value for key, value in payload.items() if key != "t"}
            if json.dumps(old_body, sort_keys=True) == json.dumps(new_body, sort_keys=True):
                return False
            old_t = payload_time(old)
            if incoming_t and old_t and incoming_t < old_t:
                return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")
    return True


def sync_snapshots(rows, allowed_slugs, published_dir=Path("published")):
    latest = {}
    for row in rows:
        if not is_snapshot_row(row):
            continue
        attachment = row.get("attachment") or {}
        slug = snapshot_slug(attachment.get("name"))
        url = str(attachment.get("url") or "")
        if not slug or slug not in allowed_slugs:
            continue
        if not url.startswith("https://ntfy.sh/file/"):
            continue
        prev = latest.get(slug)
        try:
            row_time = int(row.get("time") or 0)
        except (TypeError, ValueError):
            row_time = 0
        try:
            prev_time = int(prev.get("time") or 0) if prev else -1
        except (TypeError, ValueError):
            prev_time = -1
        if not prev or row_time >= prev_time:
            latest[slug] = row
    changed = False
    for slug, row in latest.items():
        url = row["attachment"]["url"]
        try:
            with urllib.request.urlopen(url, timeout=30) as res:
                data = res.read(2_000_001)
        except Exception as err:
            print(f"snapshot download failed {slug}: {err}", file=sys.stderr)
            continue
        if len(data) > 2_000_000:
            print(f"snapshot too large {slug}", file=sys.stderr)
            continue
        try:
            payload = json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        dest = published_dir / f"{slug}.json"
        if write_snapshot_payload(dest, payload):
            print(f"updated published/{slug}.json")
            changed = True
    return changed


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

    deleted = merge_deleted(data.get("deleted"), [])

    def matches_deleted(event, rec):
        event_id = str(event.get("id") or "").strip()
        rec_id = str(rec.get("id") or "").strip()
        slug = normalize_slug(event.get("slug") or event.get("name"))
        rec_slug = rec.get("slug") or ""
        if event_id and rec_id and event_id == rec_id:
            return True
        if slug and rec_slug and slug == rec_slug and (not rec_id or rec_id == event_id):
            if slug in ("event",) or slug.startswith("event-"):
                return bool(rec_id and rec_id == event_id)
            return True
        return False

    def upsert(record):
        slug = normalize_slug(record.get("slug") or record.get("name"))
        record_id = str(record.get("id") or "").strip()
        existing = (record_id and by_id.get(record_id)) or (slug and by_slug.get(slug)) or {}
        rec_t = stamp(record)
        if record.get("deleted"):
            if not record_id and (slug == "event" or (slug or "").startswith("event-")):
                deleted[:] = merge_deleted(deleted, [record])
                return
            forget(existing)
            if slug:
                by_slug.pop(slug, None)
            deleted[:] = merge_deleted(deleted, [record])
            return
        url = str(record.get("sheetUrl") or existing.get("sheetUrl") or "")
        if not SHEET_RE.search(url):
            return
        name = str(record.get("name") or existing.get("name") or slug).strip()
        if name in ("新しい大会", "無題の大会") and (not slug or slug == "event" or slug.startswith("event-")):
            return
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
        created_vals = []
        for src in (existing, record):
            try:
                n = int(src.get("createdAt") or 0)
            except (TypeError, ValueError):
                n = 0
            if n > 0:
                created_vals.append(n)
        if created_vals:
            new_event["createdAt"] = min(created_vals)
        forget(existing)
        by_id[new_event["id"]] = new_event
        if new_event.get("slug"):
            by_slug[new_event["slug"]] = new_event
        deleted[:] = [
            rec
            for rec in deleted
            if not matches_deleted(new_event, rec) or stamp(rec) > rec_t
        ]

    seen_ids = set()
    for record in latest_by_id.values():
        upsert(record)
        if record.get("id"):
            seen_ids.add(str(record.get("id")))
    for record in latest_by_slug.values():
        if str(record.get("id") or "") in seen_ids:
            continue
        upsert(record)

    events = [
        event
        for event in by_id.values()
        if not any(matches_deleted(event, rec) for rec in deleted)
    ]
    original_order = {
        str(event.get("id") or ""): i
        for i, event in enumerate(data.get("events") or [])
        if event.get("id")
    }

    def created_at(event):
        try:
            n = int(event.get("createdAt") or 0)
            return n if n > 0 else 0
        except (TypeError, ValueError):
            return 0

    for i, event in enumerate(events):
        if created_at(event):
            continue
        orig = original_order.get(str(event.get("id") or ""), len(events) + i)
        event["createdAt"] = orig + 1
    events.sort(key=lambda event: (-(created_at(event) or 0), str(event.get("id") or "")))
    selected = data.get("selectedId")
    if selected and not any(event.get("id") == selected for event in events):
        selected = events[0]["id"] if events else None
    elif not selected and events:
        selected = events[0]["id"]
    payload = {"version": 1, "selectedId": selected, "events": events}
    if deleted:
        payload["deleted"] = deleted
    return payload


def main():
    path = Path("events.json")
    before = load_events(path)
    try:
        rows = fetch_ntfy_rows()
    except Exception as err:
        print(f"ntfy fetch failed: {err}", file=sys.stderr)
        return 0
    after = apply_updates(before, records_from_rows(rows))
    events_changed = json.dumps(before, sort_keys=True) != json.dumps(after, sort_keys=True)
    if events_changed:
        path.write_text(json.dumps(after, ensure_ascii=False, indent=2) + "\n")
        print("updated events.json")
    else:
        print("no event changes")
    allowed = {
        normalize_slug(event.get("slug") or event.get("name"))
        for event in after.get("events") or []
    }
    allowed.discard("")
    try:
        sync_snapshots(rows, allowed)
    except Exception as err:
        print(f"snapshot sync failed: {err}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
