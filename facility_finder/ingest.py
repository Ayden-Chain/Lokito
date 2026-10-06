"""Respectful Overpass ingestion with raw snapshots and last-good-cache fallback.

Run from the project root: python -m facility_finder.ingest
"""
import argparse
import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
ENDPOINTS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
)
CATEGORIES = ("toilets", "place_of_worship", "drinking_water")
LOG = logging.getLogger(__name__)


def make_query(categories=CATEGORIES):
    # ISO administrative area avoids a rectangular footprint spilling into Bekasi/Tangerang.
    values = "|".join(categories)
    return (
        '[out:json][timeout:120];\n'
        'area["ISO3166-2"="ID-JK"]["boundary"="administrative"]->.jakarta;\n'
        '.jakarta out tags;\n'
        f'nwr["amenity"~"^({values})$"](area.jakarta);\n'
        'out meta center;'
    )


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def validate_response(payload):
    if not isinstance(payload, dict) or not isinstance(payload.get("elements"), list):
        raise ValueError("Overpass response has no elements array")
    if payload.get("remark"):
        raise ValueError(f"Overpass returned incomplete/error output: {payload['remark']}")
    if not any(e.get("type") == "area" and e.get("tags", {}).get("ISO3166-2") == "ID-JK"
               for e in payload["elements"]):
        raise ValueError("Jakarta administrative area was not resolved; refusing ambiguous data")
    return payload


def request_query(query, raw_dir=RAW_DIR, endpoints=ENDPOINTS):
    """At most two sequential attempts, one per endpoint, with backoff."""
    errors = []
    for attempt, endpoint in enumerate(endpoints):
        if attempt:
            time.sleep(8 * attempt)
        try:
            LOG.info("Requesting %s", endpoint)
            response = requests.get(endpoint, params={"data": query}, timeout=(20, 155),
                                     headers={"User-Agent": "DekatAcademicMVP/0.1 (Jakarta facility research)"})
            response.raise_for_status()
            payload = validate_response(response.json())
            fetched = datetime.now(timezone.utc).isoformat()
            digest = hashlib.sha256(query.encode()).hexdigest()[:12]
            name = f"{fetched[:19].replace(':', '-')}_{digest}.json"
            snapshot = {"fetched_at": fetched, "endpoint": endpoint, "query": query,
                        "scope": "Jakarta administrative area, ISO3166-2=ID-JK",
                        "payload": payload}
            atomic_json(Path(raw_dir) / name, snapshot)
            return snapshot, name
        except (requests.RequestException, ValueError) as exc:
            errors.append(f"{endpoint}: {exc}")
            LOG.warning("%s", errors[-1])
    raise RuntimeError("; ".join(errors))


def acquire(raw_dir=RAW_DIR, refresh=False, fetcher=request_query):
    """Reuse complete snapshots by default; failed refresh never replaces last-good data."""
    raw_dir = Path(raw_dir)
    cache = raw_dir / "latest.json"
    cached = None
    if cache.exists():
        try:
            cached = json.loads(cache.read_text(encoding="utf-8"))
            validate_response(cached["payload"])
            from facility_finder.data import normalize
            if not cached.get("scope") or not normalize(cached)[0]:
                raise ValueError("Cached snapshot has no usable facilities or scope")
        except (ValueError, KeyError, TypeError) as exc:
            LOG.warning("Cached snapshot is invalid: %s", exc)
            cached = None
    if cached and not refresh:
        return cached, "cache"
    try:
        snapshot, name = fetcher(make_query(), raw_dir=raw_dir)
        # An unexpected all-zero refresh is suspicious; never erase a useful cache.
        if not any(e.get("type") in ("node", "way", "relation") for e in snapshot["payload"]["elements"]):
            raise RuntimeError("No facility elements returned")
        snapshot["raw_files"] = [name]
        snapshot["categories_requested"] = list(CATEGORIES)
        from facility_finder.data import normalize
        if not normalize(snapshot)[0]:
            raise RuntimeError("No usable facility coordinates returned; keeping last-good data")
    except RuntimeError as full_error:
        if cached:
            LOG.warning("REFRESH FAILED; keeping snapshot from %s. %s", cached["fetched_at"], full_error)
            return cached, "cache_fallback"
        LOG.warning("Full query failed. Trying three smaller category queries: %s", full_error)
        snapshots, filenames = [], []
        for category in CATEGORIES:
            time.sleep(5)
            part, name = fetcher(make_query((category,)), raw_dir=raw_dir)
            snapshots.append(part)
            filenames.append(name)
        snapshot = dict(snapshots[-1])
        unique = {(e["type"], e["id"]): e for part in snapshots for e in part["payload"]["elements"]}
        snapshot["payload"] = dict(snapshot["payload"], elements=list(unique.values()))
        snapshot["query"] = [part["query"] for part in snapshots]
        snapshot["raw_files"] = filenames
        snapshot["categories_requested"] = list(CATEGORIES)
        snapshot["note"] = "Merged category queries; individual source timestamps are in raw_files."
        from facility_finder.data import normalize
        if not normalize(snapshot)[0]:
            raise RuntimeError("Category queries returned no usable facilities; no cache was replaced")
    atomic_json(cache, snapshot)
    return snapshot, "network"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="Request fresh OSM data; keep cache on failure")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    snapshot, mode = acquire(refresh=args.refresh)
    from facility_finder.data import write_processed
    report = write_processed(snapshot)
    print(json.dumps({"load_mode": mode, "records": report["total_facilities"],
                      "by_category": report["by_category"]}, indent=2))


if __name__ == "__main__":
    main()
