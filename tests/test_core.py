"""Synthetic edge cases are test-only; real app data always comes from OSM."""
import copy
import json
import math
import sqlite3

import pandas as pd
import pytest

from facility_finder.community import add_report, list_reports, connect
from facility_finder.data import (audit, filter_facilities, haversine_km, load_facilities,
                                  normalize, possible_duplicates, rank_nearest, write_processed)
from facility_finder.ingest import acquire, atomic_json, make_query, validate_response
from facility_finder.maps import build_map, popup_html


@pytest.fixture
def snapshot():
    return {"fetched_at": "2026-09-14T00:00:00+00:00", "scope": "TEST FIXTURE ONLY", "query": make_query(),
            "payload": {"elements": [
                {"type": "area", "id": 3600000000, "tags": {"ISO3166-2": "ID-JK"}},
                {"type": "node", "id": 1, "lat": -6.2, "lon": 106.8,
                 "tags": {"amenity": "toilets", "name": "Test-only toilet", "fee": "no", "wheelchair": "yes", "access": "yes"}},
                {"type": "way", "id": 1, "center": {"lat": -6.2001, "lon": 106.8},
                 "tags": {"amenity": "toilets", "wheelchair": "limited"}},
                {"type": "relation", "id": 2, "center": {"lat": -6.3, "lon": 106.9},
                 "tags": {"amenity": "place_of_worship", "religion": "muslim"}},
                {"type": "node", "id": 3, "lat": -6.21, "lon": 106.81,
                 "tags": {"amenity": "drinking_water"}},
            ]}}


def test_query_includes_all_osm_types_and_boundary():
    q = make_query()
    assert 'nwr[' in q and 'ID-JK' in q and 'out meta center' in q
    assert 'drinking_water' in q


def test_normalization_keeps_unknowns_and_type_ids(snapshot):
    records, stats = normalize(snapshot)
    assert len(records) == 4
    assert {r["facility_id"] for r in records} == {"node/1", "way/1", "relation/2", "node/3"}
    by_id = {r["facility_id"]: r for r in records}
    assert by_id["node/3"]["wheelchair"] == "unknown"
    assert by_id["relation/2"]["name"] == "unknown"
    assert by_id["way/1"]["coordinate_method"] == "OSM bounding-box center"
    assert all(r["last_verified_at"] is None for r in records)


def test_reject_coordinates_and_exact_duplicates(snapshot):
    bad = copy.deepcopy(snapshot["payload"]["elements"][1])
    bad.update(id=99, lat=math.nan)
    snapshot["payload"]["elements"].extend([bad, copy.deepcopy(snapshot["payload"]["elements"][1]),
                                            {"type": "way", "id": 100, "tags": {"amenity": "toilets"}}])
    records, stats = normalize(snapshot)
    assert len(records) == 4
    assert stats["duplicate_osm_elements_removed"] == 1
    assert stats["missing_or_invalid_coordinates"] == 2


def test_audit_has_correct_denominators_and_near_pairs(snapshot):
    records, stats = normalize(snapshot)
    result = audit(records, stats, snapshot)
    assert result["completeness"]["name"] == {"known": 1, "total": 4, "percent": 25.0}
    assert result["by_category"]["toilets"] == 2
    assert result["near_duplicate_pair_count"] == 1
    assert result["normalized_duplicate_ids"] == 0


def test_strict_filters_exclude_unknown_and_limited(snapshot):
    frame = pd.DataFrame(normalize(snapshot)[0])
    assert len(filter_facilities(frame, ["toilets"])) == 2
    assert len(filter_facilities(frame, ["toilets"], wheelchair_only=True)) == 1
    assert len(filter_facilities(frame, ["drinking_water"], free_only=True)) == 0
    assert len(filter_facilities(frame, ["toilets"], explicit_access_only=True)) == 1
    assert len(filter_facilities(frame, ["place_of_worship"], religion="muslim")) == 1
    assert len(filter_facilities(frame, ["toilets"], search="[")) == 0
    assert len(filter_facilities(frame, [])) == 0


def test_haversine_known_distance_and_sort(snapshot):
    assert haversine_km(0, 0, 0, 1) == pytest.approx(111.195, abs=0.01)
    assert haversine_km(-6.2, 106.8, -6.2, 106.8) == 0
    assert haversine_km(0, 179.9, 0, -179.9) == pytest.approx(22.239, abs=0.01)
    with pytest.raises(ValueError):
        haversine_km(float("nan"), 0, 0, 0)
    frame = pd.DataFrame(normalize(snapshot)[0])
    ranked = rank_nearest(frame, -6.2, 106.8)
    assert ranked.iloc[0].facility_id == "node/1"
    assert ranked.distance_km.is_monotonic_increasing
    assert rank_nearest(frame.iloc[:0], -6.2, 106.8).empty


def test_processed_round_trip_and_cache_fallback(snapshot, tmp_path):
    atomic_json(tmp_path / "latest.json", snapshot)
    def fail(*args, **kwargs):
        raise RuntimeError("Simulated offline API")
    saved = (tmp_path / "latest.json").read_bytes()
    cached, mode = acquire(tmp_path, refresh=True, fetcher=fail)
    assert mode == "cache_fallback" and cached == snapshot
    assert (tmp_path / "latest.json").read_bytes() == saved
    cached, mode = acquire(tmp_path, fetcher=fail)
    assert mode == "cache"
    write_processed(cached, tmp_path / "processed")
    assert len(load_facilities(tmp_path / "processed" / "facilities.json")) == 4


def test_partial_overpass_response_is_rejected(snapshot):
    snapshot["payload"]["remark"] = "runtime error: Query timed out"
    with pytest.raises(ValueError):
        validate_response(snapshot["payload"])
    with pytest.raises(ValueError):
        validate_response({"elements": []})


def test_unusable_refresh_keeps_last_good_snapshot(snapshot, tmp_path):
    atomic_json(tmp_path / "latest.json", snapshot)
    bad = copy.deepcopy(snapshot)
    for element in bad["payload"]["elements"]:
        element.pop("lat", None)
        element.pop("center", None)
    def fetch(*args, **kwargs):
        return bad, "invalid-coordinates.json"
    result, mode = acquire(tmp_path, refresh=True, fetcher=fetch)
    assert mode == "cache_fallback" and result == snapshot
    assert json.loads((tmp_path / "latest.json").read_text()) == snapshot


def test_category_fallback_and_failure_preserves_cache(snapshot, tmp_path):
    calls = []
    def fetch(query, raw_dir):
        calls.append(query)
        if len(calls) == 1:
            raise RuntimeError("full query timed out")
        return snapshot, f"part{len(calls)}.json"
    from unittest.mock import patch
    with patch("facility_finder.ingest.time.sleep"):
        result, mode = acquire(tmp_path, fetcher=fetch)
    assert len(calls) == 4 and mode == "network"
    assert len(result["payload"]["elements"]) == 5


def test_popup_escapes_untrusted_tags_and_map_renders(snapshot):
    records, _ = normalize(snapshot)
    records[0]["name"] = '<script>alert("bad")</script>'
    html = popup_html(records[0])
    assert "<script>" not in html and "&lt;script&gt;" in html
    assert "unknown" in html and "Not verified" in html
    rendered = build_map(pd.DataFrame(records), (-6.2, 106.8)).get_root().render()
    assert "L.map(" in rendered and "markerClusterGroup" in rendered and "OpenStreetMap" in rendered


def test_reports_persist_without_verification_or_seed_mutation(tmp_path):
    db = tmp_path / "reports.sqlite3"
    assert list_reports("node/1", db) == []
    add_report("node/1", {"node/1"}, "yes", 4, "Test-only report", db)
    rows = list_reports("node/1", db)
    assert len(rows) == 1 and rows[0]["moderation_status"] == "pending"
    assert rows[0]["reviewed_at"] is None and rows[0]["contributor_id"] is None
    conn = connect(db)
    assert conn.execute("SELECT COUNT(*) FROM verified_facilities").fetchone()[0] == 0
    conn.close()
    with pytest.raises(ValueError):
        add_report("node/2", {"node/1"}, "yes", path=db)
    with pytest.raises(ValueError):
        add_report("node/1", {"node/1"}, "yes", 6, path=db)


def test_real_cache_integrity():
    frame = load_facilities()
    assert frame.facility_id.is_unique
    assert frame.latitude.between(-6.5, -5.0).all()
    assert frame.longitude.between(106.3, 107.1).all()
    assert set(frame.facility_category) <= {"toilets", "place_of_worship", "drinking_water"}
    assert frame.tags.map(lambda tags: isinstance(tags, dict)).all()
