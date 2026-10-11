# Historical Google Maps iteration QA — 6 October 2026

Historical record only. The OSM restoration and current test total are documented in [OSM_MAP_QA.md](OSM_MAP_QA.md); the observations and 78-test count below describe the earlier Google Maps iteration. No commit, push or deployment was performed.

## Automated verification

Run `.venv/bin/python -m pytest -q` from the project root: **78 passed**.

Coverage includes old-cache compatibility, separate mall/SPBU results, preservation of the original toilet selection, coordinate-safe Google Maps URLs, dedicated public Embed key isolation from server Places credentials, direct-link fallback, partial media success, preserving previous valid photos, stopping after provider rate limiting, coordinate validation for name-based Wikidata resolution, Commons Category lookup, and public report field restrictions. Synthetic reports and submissions use temporary databases. Tests block live HTTP.

## Live browser verification

The original localhost process was restarted at **http://127.0.0.1:8502/** with current modules. No Google Embed or Places key is configured.

- Bundaran HI still returns **43 mapped toilets within 5 km**. The nearest mapped toilet remains `node/14140086914` at about 810 m.
- Independent cards show **Plaza Indonesia (210 m)** and **Grand Indonesia Shopping Town (250 m)**, with exact-coordinate Google Maps links and separate OSM provenance links. Neither is added to the mapped-toilet count.
- The map selector changes the destination between a mapped facility, starting point and venue. Choosing either mall leaves the featured toilet and count unchanged. No OSM basemap or Leaflet frame is rendered by the app.
- The keyless panel exposes a coordinate URL; opening that URL in Google Maps resolved to **-6.1957624,106.8208806**, matching the selected Grand Indonesia record. A selected venue also displays its cached photograph. Grand Indonesia's actual Wikimedia image rendered visibly with creator and CC BY-SA 4.0 attribution. Both malls have valid image metadata and source links.
- Visitor observations are visible on the featured card without opening details. Pending reports say “Awaiting review”; free text and contributor/reviewer identities do not appear. The existing local reports were preserved; no live-browser test report was submitted.
- At **1280 × 900**, the result and Google Maps panels display in columns. At **390 × 844**, the map destination panel stacks above results; its title, controls and button fit. Document width equals viewport width (390 px), with no horizontal overflow.
- The redundant “Opens Google Maps” text is absent. Directions and map links remain separate actions.

## Photo acquisition and source integrity

Latest explicit refresh replayed the existing complete venue snapshot with a 12 missing-photo lookup budget. It made 11 attempts, retained three additional valid images, and stopped on Wikimedia HTTP backoff. Current cache: **5,120 venues, 28 venue photographs, 41 facility-photo associations including 24 toilets**. Missing media remain absent; source timestamps and licences are retained. No Google imagery was scraped.

The original facility snapshot remains **5,824 records / 141 toilets / 5,645 places of worship / 38 drinking-water points**. Raw and processed file hashes are checked against `docs/enrichment-baseline/data-sha256.txt`. Enrichment stays in its separate bundle.

## Limits

Live Google Embed rendering, API-key restrictions/billing configuration, physical touchscreen gestures and a hardware trackpad are not verified without the required configured environment/devices. Embed markup and key separation are covered offline; the direct link is available regardless of embedded-map setup or failure. Google Maps shows one selected coordinate, not all nearby Lokito pins simultaneously. Coordinates may identify a venue centre rather than its entrance. Photos depict venues, not confirmed toilet interiors. Current data contain no explicit toilet association inside Plaza Indonesia or Grand Indonesia; that does not imply those malls lack toilets. No facility field verification was performed.

Google documentation reviewed on 6 October: [Embed setup and prerequisites](https://developers.google.com/maps/documentation/embed/quickstart), [Embed billing](https://developers.google.com/maps/documentation/embed/usage-and-billing), [security restrictions](https://developers.google.com/maps/api-security-best-practices), [Maps URLs](https://developers.google.com/maps/documentation/urls/get-started).

## Changed files (including continued local work)

- Application/UI: `app.py`, `assets/lokito.css`, `facility_finder/google_map.py`, `facility_finder/community_ui.py`, `facility_finder/community.py`, `facility_finder/venue_ui.py`, `facility_finder/evidence.py`.
- Venue/media pipeline and retained compatibility helpers: `facility_finder/enrichment.py`, `facility_finder/enrich_places.py`, `facility_finder/media.py`, `facility_finder/maps.py`, `facility_finder/presentation.py`, `data/enrichment/places.json`.
- Tests: `tests/test_enrichment.py`, `tests/test_presentation.py`, `tests/test_google_map_reports.py`.
- Setup/documentation: `.env.example`, `README.md`, `PROJECT_STATUS.md`, `docs/ENRICHMENT_HANDOVER.md`, `docs/ENRICHMENT_QA.md`, `docs/QA_RESULTS.md`, this file.
