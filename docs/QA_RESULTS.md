# QA results — 14 September 2026

## Tested environment

macOS ARM64, Python 3.12.4, Streamlit 1.63.0, Pandas 2.3.3, Folium 0.20.0, streamlit-folium 0.27.4. Full versions are recorded in `requirements-lock.txt`.

## Automated validation

Command: `python -m pytest -q`

**Result: 15 passed in 3.63 seconds** on the final source, including the default 5 km radius and malformed-refresh protection.

| Check | Result |
|---|---|
| Query uses Jakarta administrative area and nodes/ways/relations | Pass |
| Normalize missing names, tags and source attributes without invented positives | Pass |
| Keep node/way numeric IDs distinct | Pass |
| Reject missing/non-finite coordinates and remove exact repeated OSM IDs | Pass |
| Audit denominators and 30 m proximity flags | Pass |
| Category, religion, explicit-access, free and strict wheelchair filters | Pass |
| Literal search handles regex characters and empty results | Pass |
| Haversine equatorial one-degree reference (~111.195 km), identical points and antimeridian | Pass |
| Distance ranking and empty candidate set | Pass |
| Simulated API failure preserves last-good raw bytes and original timestamp | Pass |
| Malformed-coordinate refresh preserves last-good raw snapshot | Pass |
| Reject Overpass timeout remarks and unresolved Jakarta area | Pass |
| Simulated full-query failure falls back to sequential category queries | Pass |
| Normalized JSON round trip | Pass |
| Escape script-shaped source text in popups and generate Leaflet/cluster markup | Pass |
| SQLite persistence, validation, pending status and no automatic verification | Pass |
| Real cache IDs, geographic envelope, categories and original tags | Pass |
| Streamlit launch, all need choices, no-match state, custom location and strict filters | Pass |
| Streamlit observation form submits into isolated temporary SQLite database | Pass |

These checks are grouped into 15 test functions; the table lists their covered behaviours. Synthetic edge cases exist only inside tests. The real community database was inspected after QA and contained **zero reports**.

## Actual data acquisition and cache execution

- Initial full-city POST requests failed on public Overpass servers (504/502/timeouts); the failure was visible. A smaller diagnostic GET query succeeded; the final GET ingestion subsequently retrieved the complete selected categories for Jakarta's OSM administrative area.
- Complete successful snapshot: **2026-09-14T13:15:32.318207+00:00**, OSM database timestamp **2026-09-14T13:14:00Z**.
- Actual normalized results: **5,824** (141 toilets, 5,645 worship, 38 drinking water).
- `python -m facility_finder.ingest` executed again using `load_mode: cache` and returned the same 5,824 records without an API request.
- `python -m facility_finder.report` regenerated `DATA_QUALITY.md` successfully.
- All audit notebook code cells were executed; the recomputed audit exactly matched `quality.json`.
- Integrity: 0 missing coordinates; 0 normalized duplicate IDs; 104 same-category proximity pairs retained for manual review.

## Actual browser checks

The app was launched on **http://127.0.0.1:8501** and inspected in the Codex in-app browser.

- Streamlit title, need controls, sidebar filters and facility details appeared.
- Actual OSM map tiles, scale, attribution and marker clusters rendered.
- Clicking a real toilet marker opened a popup for `node/9764148449` showing its category, unknown metadata, source and unverified status.
- Switching to drinking water changed the visible results to **13 within 5 km of Bundaran HI**, nearest **0.80 km**, and updated the selected facility and map.
- “Data & trust” displayed the full-snapshot audit independently of discovery filters.
- The final default toilet search returns **43 within 5 km**, nearest approximately **0.81 km**. These are snapshot-specific observations, not hard-coded inventory counts.

## Limits of QA

No field visit, water-quality check, accessibility audit, mobile-device matrix, route calculation, load test, penetration test, external authentication or production deployment was performed. Full offline map operation was not tested or promised; map assets require internet/browser cache. Automated AppTest covers Streamlit logic but not iframe JavaScript; the live browser checks supply that evidence for the map. API fallback failures are simulated after the real successful acquisition to avoid unnecessary requests.
