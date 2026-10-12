# Lokito map and scrolling QA — 11 October 2026

Current implementation and verification record. This supersedes the historical Google Maps handoff-panel iteration in `GOOGLE_MAPS_QA.md`. No reset, commit, push or deployment was performed. Existing local work was retained.

## Result

The discovery page again renders an interactive Folium/Leaflet map using OpenStreetMap tiles, without a Google key. Google Maps remains available through exact-coordinate and directions links. Desktop has a scrolling left result panel with search/preferences outside that scrolling region; the map remains beside it. Mobile renders controls, map and results in normal page flow.

Numbered brown dashed pins are mapped, unverified toilets. Blue M/S circles represent mall/SPBU landmarks, secondary facility categories use purple numbered pins, and a dark circle marks the starting point. A dark outline indicates selection, never verification. Facility and venue clusters are separate. All 5,824 original records have `Not community verified` and no verification date, so there are no confirmed markers to display. Visitor reports, OSM presence and geometric containment do not create verification.

At Bundaran HI with the default 5 km radius, there are **43 toilet results** and **116 separate mall/SPBU landmarks**. The nearest toilet remains `node/14140086914`, about 810 m away. The map includes every matching venue within the radius even if its card is beyond the first five. Venues with an existing toilet association are retained with an appropriate association notice; other venues say no toilet is explicitly linked in Lokito, without claiming toilets do not exist there.

## Automated checks

- `.venv/bin/python -m pytest -q`: **83 passed** on 11 October 2026.
- `git diff --check`: passed.
- `shasum -a 256 -c docs/enrichment-baseline/data-sha256.txt`: all five original raw/processed files passed.
- Regression coverage includes every nearby venue in the rendered map, unchanged facility data/ranking, origin and venue clicks at shared coordinates, facility/venue selection independence, filter reset, old-cache compatibility, partial photo-refresh success and private report-field exclusion. Network calls are blocked in automated tests; submissions use temporary databases.
- No photo refresh or facility ingestion was run for the OSM/scroll change. Existing media/cache recovery behavior was retained and tested.

## Browser checks

Preview processes were started with the current project at **http://127.0.0.1:8501/** and **http://127.0.0.1:8502/**. Main visual QA used port 8501.

- At **1280 × 900**, the result area has a 530 px viewport with approximately 3,960 px of content. Scrolling it to 1,800 px left the map and toolbar at the same vertical position (232 px). Search/preferences remained usable.
- At **1024 × 768**, the results viewport is approximately 398 px and map frame 421 px; document width equals viewport width with no horizontal overflow.
- At **390 × 844**, controls come before the 300 px map and results. The result panel has normal visible overflow, not an internal scrolling viewport. Scrolling the page moved the toolbar offscreen. Document width remained 390 px. Mobile popup content stayed within the map frame and could scroll when long.
- Mouse-wheel zoom changed the OSM tile level from 13 to 14. The plus control also zoomed the map. Pin selection on the map changed the featured card to “Toilet near Tanah Abang”; the nearest-option action restored the original recommendation.
- Focusing Plaza Indonesia and Grand Indonesia left the selected toilet unchanged. Clicking their blue marker opened the correct venue popup, with distance labeled as straight-line, a plain-text OSM source, and coordinate-specific Google links.
- Both Wikimedia photos rendered visibly in cards and popups. No OSM object-page link remains in the discovery venue cards or location-context detail; the required map/footer attribution remains linked.
- Structured visitor reports remain visible without expanding a reports section. No new test report was submitted to the real local database. No browser console errors were observed during the interaction check.

## Photos

| Venue | Photo creator | Licence | Status |
| --- | --- | --- | --- |
| Plaza Indonesia | Baqotun0023 | CC BY-SA 4.0 | Cached metadata passes validation; photograph rendered in browser |
| Grand Indonesia Shopping Town | Timothy Antonio | CC BY-SA 4.0 | Cached metadata passes validation; photograph rendered in browser |

Creator, Commons source, licence links and crop notices remain visible. These are venue photographs and do not establish the appearance or exact location of a toilet. Current cache coverage remains **5,120 venues, 28 venue photographs, and 41 facility-photo associations including 24 toilets**. Missing images remain absent; no Google imagery was scraped.

## Evidence

- [Desktop — Plaza Indonesia](qa-osm/desktop-plaza.jpg)
- [Desktop — Grand Indonesia](qa-osm/desktop-grand.jpg)
- [Mobile layout](qa-osm/mobile.jpg)
- [Desktop overview](qa-osm/desktop-overview.jpg)

## Remaining limits

- Physical touchscreen pinch and a hardware trackpad have not been device-tested. Leaflet wheel/touch zoom options are enabled; wheel and zoom-button behavior were browser-tested.
- No facility currently has a verified status. A positive verification style needs a defined, authoritative verification workflow and real verification data; the application does not invent either.
- The map displays up to 60 facility results, including the selected facility, with a visible notice when that limit applies. All matching mall/SPBU landmarks remain in the map. More facility results can be browsed in the list.
- OSM tiles, map frontend assets and Wikimedia images depend on network access. Venue coordinates can represent a centre rather than an entrance. Lokito calculates straight-line distances, not routes or walking times.
- Streamlit can redraw the map when the selected facility, venue focus or query changes. Mobile QA used a browser viewport, not a physical handset.
- Google Embed and optional Places helpers remain in the codebase for compatibility, but discovery uses OSM and requires neither a Google key nor a Google billing configuration. No Google live API call was made in this work.

## Files changed in the map/scroll continuation

- App/UI: `app.py`, `assets/lokito.css`, `facility_finder/maps.py`, `facility_finder/presentation.py`, `facility_finder/venue_ui.py`, `facility_finder/evidence.py`.
- Tests: `tests/test_enrichment.py`, `tests/test_google_map_reports.py`, `tests/test_presentation.py`, `tests/test_osm_discovery.py`.
- Documentation: `.env.example`, `README.md`, `PROJECT_STATUS.md`, `docs/ENRICHMENT_HANDOVER.md`, `docs/ENRICHMENT_QA.md`, `docs/QA_RESULTS.md`, `docs/GOOGLE_MAPS_QA.md`, this record and `docs/qa-osm/` screenshots.

Earlier uncommitted changes to enrichment/media, community previews and the cache remain in the working tree. They were not reset or published.
