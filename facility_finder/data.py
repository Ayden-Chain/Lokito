"""Normalization, audit, filtering and distance calculations. No network calls."""
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

from facility_finder.ingest import ROOT, atomic_json

CATEGORY_LABELS = {"toilets": "Toilet", "place_of_worship": "Prayer / worship", "drinking_water": "Drinking water"}
METADATA_FIELDS = ("name", "access", "opening_hours", "wheelchair", "fee")
UNKNOWN = "unknown"
PROCESSED = ROOT / "data" / "processed"


def clean_text(value):
    if value is None or not isinstance(value, (str, int, float)):
        return UNKNOWN
    result = str(value).strip()
    return result if result and result.casefold() not in ("nan", "none", "null", "unknown", "n/a") else UNKNOWN


def valid_coordinates(lat, lon):
    try:
        lat, lon = float(lat), float(lon)
        return math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180
    except (TypeError, ValueError):
        return False


def haversine_km(lat1, lon1, lat2, lon2):
    if not valid_coordinates(lat1, lon1) or not valid_coordinates(lat2, lon2):
        raise ValueError("Latitude must be -90…90 and longitude -180…180, both finite")
    a1, a2 = math.radians(float(lat1)), math.radians(float(lat2))
    da = a2 - a1
    dl = math.radians(float(lon2) - float(lon1))
    h = math.sin(da / 2) ** 2 + math.cos(a1) * math.cos(a2) * math.sin(dl / 2) ** 2
    return 6371.0088 * 2 * math.asin(math.sqrt(min(1, max(0, h))))


def normalize(snapshot):
    records, seen = [], set()
    stats = Counter(raw_facility_elements=0, missing_or_invalid_coordinates=0,
                    duplicate_osm_elements_removed=0, rejected_identifiers=0)
    for element in snapshot["payload"]["elements"]:
        tags = element.get("tags") or {}
        category = tags.get("amenity")
        if element.get("type") not in ("node", "way", "relation") or category not in CATEGORY_LABELS:
            continue
        stats["raw_facility_elements"] += 1
        osm_id = element.get("id")
        if not isinstance(osm_id, int) or isinstance(osm_id, bool) or osm_id <= 0:
            stats["rejected_identifiers"] += 1
            continue
        fid = f"{element['type']}/{osm_id}"
        if fid in seen:
            stats["duplicate_osm_elements_removed"] += 1
            continue
        point = element if element["type"] == "node" else (element.get("center") or {})
        lat, lon = point.get("lat"), point.get("lon")
        if not valid_coordinates(lat, lon):
            stats["missing_or_invalid_coordinates"] += 1
            continue
        seen.add(fid)
        street = " ".join(str(tags[k]).strip() for k in ("addr:street", "addr:housenumber") if tags.get(k))
        address = tags.get("addr:full") or ", ".join(str(v) for v in
                    (street, tags.get("addr:suburb"), tags.get("addr:city"), tags.get("addr:postcode")) if v)
        record = {
            "facility_id": fid, "osm_type": element["type"], "osm_id": osm_id,
            "facility_category": category, "latitude": float(lat), "longitude": float(lon),
            "coordinate_method": "OSM node" if element["type"] == "node" else "OSM bounding-box center",
            "name": clean_text(tags.get("name") or tags.get("name:id") or tags.get("name:en")),
            "address": clean_text(address), "source": "OpenStreetMap",
            "source_url": f"https://www.openstreetmap.org/{fid}",
            "last_data_refresh": snapshot["fetched_at"],
            "osm_last_edited": clean_text(element.get("timestamp")),
            "osm_check_date": clean_text(tags.get("check_date")),
            "verification_status": "Not community verified", "last_verified_at": None,
            "tags": tags,
        }
        for key in ("access", "fee", "opening_hours", "wheelchair", "operator", "changing_table",
                    "religion", "denomination", "wheelchair:description", "drinking_water"):
            record[key] = clean_text(tags.get(key))
        records.append(record)
    records.sort(key=lambda r: (r["facility_category"], r["facility_id"]))
    return records, dict(stats)


def possible_duplicates(records, threshold_km=0.03):
    """Flag same-category objects <=30m apart; never automatically merge OSM objects.

    Grid size is conservative at Jakarta's latitude. Unnamed and node/way pairs
    are included; two nearby objects can also legitimately represent separate facilities.
    """
    grid, pairs = defaultdict(list), []
    for row in records:
        x, y = math.floor(row["latitude"] / 0.001), math.floor(row["longitude"] / 0.001)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for other in grid[(row["facility_category"], x + dx, y + dy)]:
                    distance = haversine_km(row["latitude"], row["longitude"], other["latitude"], other["longitude"])
                    if distance <= threshold_km:
                        same_name = row["name"] != UNKNOWN and row["name"].casefold() == other["name"].casefold()
                        pairs.append({"facility_id_a": other["facility_id"], "facility_id_b": row["facility_id"],
                                      "distance_m": round(distance * 1000, 1), "same_name": same_name})
        grid[(row["facility_category"], x, y)].append(row)
    return pairs


def audit(records, stats, snapshot):
    def completeness(rows):
        return {field: {"known": sum(r[field] != UNKNOWN for r in rows),
                        "total": len(rows),
                        "percent": round(100 * sum(r[field] != UNKNOWN for r in rows) / len(rows), 2) if rows else 0.0}
                for field in METADATA_FIELDS}
    candidates = possible_duplicates(records)
    return {
        "total_facilities": len(records), "grain": "one qualifying OSM node, way, or relation",
        "scope": snapshot["scope"], "fetched_at": snapshot["fetched_at"],
        "osm_base_timestamp": snapshot["payload"].get("osm3s", {}).get("timestamp_osm_base", UNKNOWN),
        "by_category": {key: sum(r["facility_category"] == key for r in records) for key in CATEGORY_LABELS},
        "by_osm_type": dict(Counter(r["osm_type"] for r in records)),
        "completeness": completeness(records),
        "completeness_by_category": {key: completeness([r for r in records if r["facility_category"] == key])
                                     for key in CATEGORY_LABELS},
        "ingestion": stats,
        "normalized_duplicate_ids": len(records) - len({r["facility_id"] for r in records}),
        "normalized_missing_coordinates": sum(not valid_coordinates(r["latitude"], r["longitude"]) for r in records),
        "near_duplicate_pair_count": len(candidates), "near_duplicate_pairs": candidates,
        "wheelchair_values": dict(Counter(r["wheelchair"] for r in records)),
        "access_values": dict(Counter(r["access"] for r in records)),
        "raw_files": snapshot.get("raw_files", []),
    }


def write_processed(snapshot, output_dir=PROCESSED):
    records, stats = normalize(snapshot)
    if not records:
        raise ValueError("No usable facilities; existing processed files were not replaced")
    report = audit(records, stats, snapshot)
    output_dir = Path(output_dir)
    atomic_json(output_dir / "facilities.json", records)
    atomic_json(output_dir / "quality.json", report)
    csv_path = output_dir / "facilities.csv"
    temp = csv_path.with_suffix(".csv.tmp")
    pd.DataFrame([{**r, "tags": json.dumps(r["tags"], ensure_ascii=False)} for r in records]).to_csv(temp, index=False)
    temp.replace(csv_path)
    return report


def load_facilities(path=PROCESSED / "facilities.json"):
    records = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(records, list) or not records:
        raise ValueError("The facility cache is empty or invalid. Run the ingestion command.")
    required = {"facility_id", "name", "latitude", "longitude", "facility_category"}
    for row in records:
        if not required.issubset(row) or not valid_coordinates(row["latitude"], row["longitude"]):
            raise ValueError("The facility cache contains invalid records. Run ingestion again.")
    return pd.DataFrame(records)


def filter_facilities(df, categories, wheelchair_only=False, free_only=False,
                      explicit_access_only=False, search="", religion=None):
    result = df[df.facility_category.isin(categories)]
    if wheelchair_only:
        result = result[result.wheelchair.isin(["yes", "designated"])]
    if free_only:
        result = result[result.fee == "no"]
    if explicit_access_only:
        result = result[result.access.isin(["yes", "permissive"])]
    if religion:
        result = result[result.religion == religion]
    if search.strip():
        result = result[result["name"].str.contains(search.strip(), case=False, regex=False) |
                        result.address.str.contains(search.strip(), case=False, regex=False)]
    return result.copy()


def rank_nearest(df, latitude, longitude):
    if not valid_coordinates(latitude, longitude):
        raise ValueError("Invalid search coordinates")
    result = df.copy()
    result["distance_km"] = [haversine_km(latitude, longitude, r.latitude, r.longitude) for r in result.itertuples()]
    return result.sort_values(["distance_km", "facility_id"]).reset_index(drop=True)


def display_name(row):
    return row["name"] if row["name"] != UNKNOWN else f"Unnamed {CATEGORY_LABELS[row['facility_category']].lower()}"
