# Lokito venue, media and feedback handover

Implemented 6 October 2026, using Python, Streamlit, Pandas, Folium and SQLite. This extends the current application. The original 5,824 facility records were not refreshed or rewritten.

## User journey

Find a toilet → read its venue context → inspect known details and optional venue photograph → open directions. Search now also matches venue names. An unnamed toilet can receive a display label such as “Toilet inside Pondok Indah Mall 1”; “Location label by Lokito” distinguishes it from an official source name. Named facilities retain their source title. Map tooltips and popups use the same contextual title as cards.

Directions remain the primary action and appear before images. Nearby cards do not load photos. At most one featured photo and its detail-dialog equivalent render. Images use a consistent 16:7 crop with a “cropped to fit” notice. On phones the map remains 220 px high; on tablets it is 300 px. Missing media produces no invented photograph; a failed image URL leaves a neutral frame and a source link.

“Help improve Lokito” opens a dedicated app-feedback form. Facility observations remain in facility details. Data & trust exposes source evidence and private owner feedback results.

## Measured coverage

The authoritative bundle is `data/enrichment/places.json`; metadata live in that same atomic file to avoid mismatched records and metadata sidecars.

| Measure | All 5,824 facilities | 141 toilets only |
|---|---:|---:|
| Explicit association (`at`) | 0 | 0 |
| Geometry containment (`inside`) | 40 | 16 |
| Proximity (`near`) | 1,130 | 49 |
| Any venue context | 1,170 | 65 |
| Wikimedia photo available | 36 | 21 |
| Google photos fetched | 0 | 0 |

There are 23 distinct Commons files across the photo-bearing facilities. Current photo licences: CC BY-SA 4.0 (26 facility associations), CC BY-SA 3.0 (7), CC BY 4.0 (2), CC BY 3.0 (1). These counts are associations, not distinct photos or photographed toilets.

The complete venue snapshot contains 5,120 named venues after conservative duplicate handling. Association counts by category: transit 110, parks 86, public buildings 596, markets 72, SPBU 46, universities 148, malls 70, hospitals 38, attractions 4. A venue appearing in this inventory does not establish that it has a toilet; only an existing mapped facility can receive an association.

The final geometry snapshot was acquired at `2026-10-06T01:32:45.370790+00:00` (08:32 Jakarta). Its OSM base is `2026-10-06T01:30:58Z`. Enrichment timestamps indicate processing, never verification.

## Matching rules

1. Preserve original names, operators, addresses, levels and other tags. Generic brand/operator tags do not prove venue membership. Explicit `located_in`, `located_in:wikidata`, or a toilet name that exactly names a venue may establish `at`, within a 1,000 m sanity bound.
2. `inside` requires a facility **node** strictly within a complete, valid closed venue ring and outside all inner rings, including their boundaries. Area-centre facility records cannot establish containment. Self-intersecting, incomplete or degenerate rings are rejected. Split multipolygon ways are not assembled; those objects remain eligible only for proximity or explicit association.
3. Otherwise use straight-line distance to the venue's mapped centre within its category limit. The UI says `near`, with approximate separation. This is not distance to an entrance and does not establish membership.

| Venue category | Maximum near distance |
|---|---:|
| Mall | 180 m |
| SPBU / fuel station | 70 m |
| Transit station | 120 m |
| Park | 100 m |
| Market | 100 m |
| Hospital | 100 m |
| University / college | 120 m |
| Tourist attraction | 100 m |
| Government / public building | 70 m |

Explicit evidence outranks containment, which outranks proximity. Multiple equally strong explicit or containing venues cause rejection. For proximity, reject if the runner-up is no more than `max(30 m, 35% of the best distance)` farther away. Ties sort by source ID for deterministic results; ambiguity is still rejected. Node/polygon duplicate representations merge only when the category and exact normalized name or Wikidata identity agree and centres are within 30 m; a usable polygon takes precedence.

The schema stores facility and venue IDs, venue name/category/coordinates, relationship, written evidence, confidence class, distance, OSM source URL, processing time and optional photo metadata. Confidence stays out of the main consumer UI. These conservative rules may omit legitimate associations, especially in mixed-use complexes. No access, fee, cleanliness, hours, ratings, floor, entrance or verification claim is inferred.

## Acquisition and cache behaviour

`facility_finder/enrich_places.py` explicitly downloads a Jakarta venue snapshot using Overpass `out meta geom`. Venue centres are computed from geometry bounds where needed. Raw responses, exact query and acquisition receipt are saved under `data/enrichment/raw`. Original `data/raw` and `data/processed` remain separate.

The matcher is pure and independent of remote calls. The browser app loads local JSON through a modification-time cache. Normal reruns do not query Overpass, Wikidata, Commons APIs or Places APIs. Loading thumbnail images and map tiles still creates ordinary browser requests to their providers.

Refresh rejects API errors, timeout remarks, missing category coverage, unusable coordinates, empty matches, invalid schema and an association-count decrease greater than 30%. Atomic replacement occurs only after validation. A failed refresh returns the previous valid bundle and logs `cache_fallback`. Any media lookup exception during a refresh with an existing cache preserves the entire old bundle. A first acquisition can save valid context with partial photos, explicitly marked `context_complete_media_partial`.

Media requests are bounded (default 60 venue lookups, toilet venues first). Previously valid photos outside that batch are retained. A successful lookup returning no permitted image removes that photo. Deferred lookups are reported. Wikimedia rate limiting caused eight failures in the initial 35-venue batch; the completed geometry pass retained already validated photos with `--photo-limit 0`. Final matching changed some venue choices, leaving 36 photo-bearing facilities. More media coverage is possible through a later successful refresh. Old thumbnail timestamps remain truthful; they are not silently advanced.

Missing, empty or malformed enrichment files yield an ordinary facility-only app. The facility dataset itself must still be valid. A normal command uses a valid cache without remote calls; with no valid cache it performs initial acquisition. A snapshot replay can recompute context, but media may change unless disabled or retained from the existing bundle.

## Wikimedia media

Source selection uses the chosen venue's explicit `wikimedia_commons`/`image` File reference, Wikidata QID P18 claim, or Wikipedia-to-Wikidata resolution. There is no image search or arbitrary website scraping. Images are treated as venue images; their relationship to the actual toilet is not claimed.

Commons imageinfo returns a thumbnail and machine-readable creator/licence metadata. The cache records source identifier, filename, thumbnail URL, file-page URL, creator, credit, licence name and URL, description, retrieval timestamp, alt text and subject. HTML metadata is stripped and escaped before rendering.

Only HTTPS Commons file pages, Commons thumbnail hosts, supported raster types (JPEG, PNG, WebP), known Creative Commons attribution/share-alike or public-domain licence paths, and non-empty author/licence metadata are accepted. Restricted/non-free metadata, logos detected from filenames, SVG/video and unsafe URLs are rejected. Filename checks cannot establish every visual subject, and source references can be mistaken; spot checks are still valuable. Files with unsupported or incomplete licence metadata are omitted even if another reuse basis might exist.

Every photo includes a visible venue-photo label, creator/Commons link and licence link. Thumbnails are requested at 640 px; Wikimedia may serve a standard size bucket. Full-resolution files are not downloaded. CSS background rendering gives a neutral failure state; it does not provide an image-load acknowledgement. `photo_shown` therefore means a photo frame was rendered from valid metadata, not proof that the browser fetched it or the tester saw it. The feedback answer “It was not shown” remains available.

## Optional Google Places

Google is disabled unless `GOOGLE_MAPS_API_KEY` is present in the server environment. No key was available during development; live photos, billing and account eligibility were not tested. Automated tests use synthetic mock responses and block live requests.

The explicit `--google-map-ids` command performs up to 50 unique-venue lookups using Places API (New) Text Search and a field mask limited to ID, name, location and types. An exact normalized name, compatible type and centre distance ≤150 m are required, and multiple accepted IDs are rejected. Only OSM-ID-to-Place-ID mappings persist in `google-place-ids.json`; no Google names, ratings, hours or coordinates are copied into OSM facts.

On a separate photo page, an explicit “Load venue photo” click fetches fresh details (`photos` field mask) then a photo URL with `maxWidthPx=640`. Photo resource names, URLs and downloaded files are never written into the enrichment cache or session cache. Ordinary reruns do not re-request a photo. Invalid keys, quota limits, failed requests and unmatched venues leave the OSM/Wikimedia experience available.

Google-derived media are shown **without the OSM map**, with Google Maps attribution, all returned named author links, supported author images and an original-photo link. No Google-derived relationship claims are made. The adapter also requires `LOKITO_PRIVACY_URL` and `LOKITO_TERMS_URL` HTTPS links before exposing the photo journey. URL validation cannot verify the content of those policies; the operator must publish suitable policies and comply with Google Maps Platform requirements.

Enable Places API (New) and billing on your own Google Cloud project. Apply API/key restrictions and quotas and monitor usage; budgets are alerts, not guaranteed spending caps. Explicit matching and photo clicks can be billable. Consult current Google pricing rather than assuming a free allowance. Do not paste a real key into the repository, screenshots or research exports. `.env.example` is documentation only; the app does not automatically read `.env`.

## Feedback and privacy

`data/product-feedback.sqlite3` is created only on a real submission. It is separate from `data/community.sqlite3` and contains a `product_feedback` table. It uses parameterized SQL, enum/length/score validation and a unique random submission token to prevent duplicates on Streamlit reruns. The form allows one saved response per browser session; refreshing creates a new session, so this is not abuse prevention.

Required answers cover ease of finding and understanding the location, usefulness of venue information and photo. Comments are optional and limited to 1,500 characters. Score 1–5 is optional; tester type defaults to “Prefer not to say”. No name, email, phone, account identity, IP or precise starting coordinates are collected by the feedback code. Stored context includes selected facility/category, a recognized preset name, whether context/photo markup was offered, schema version and submission time. Viewport is nullable and is currently left empty; no fingerprinting script is used.

The exact privacy notice appears on the form. “Locally” means the computer/server running Streamlit. Free text can still contain personal information supplied by a tester. Hosting providers, map/image providers and web-server infrastructure may independently process request metadata; this app-level claim does not promise anonymous internet transport. Custom coordinates are used by the existing discovery/directions journey and are excluded from feedback persistence.

Owner results under Data & trust require `LOKITO_OWNER_PASSWORD`. With it unset, results are unavailable. Unlocking uses constant-time comparison and a session proof; comments are escaped and visible only after unlock. The summary includes answer distributions, total count, optional score mean with its response count, and latest 30 comments. Lock removes access in the session. The local prototype gate is not a substitute for production identity, access logging, abuse prevention, HTTPS and host access controls.

Choose a research retention period, limit access to the database and arrange durable storage/backups before a hosted pilot. Filesystem storage may disappear on ephemeral hosting. No automatic export, email notification or retention deletion is implemented.

## Commands (VS Code terminal, macOS zsh)

```bash
cd "/Users/hugowahyubagas/Documents/Venture Creation"
source .venv/bin/activate
python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

Stop that server with Ctrl+C before changing its environment. Another terminal can run:

```bash
python -m facility_finder.enrich_places
python -m facility_finder.enrich_places --refresh --photo-limit 60
python -m pytest -q
shasum -a 256 -c docs/enrichment-baseline/data-sha256.txt
```

Optional Google setup, in the terminal that will run the app:

```bash
read -rs "GOOGLE_MAPS_API_KEY?Google Maps API key: "
export GOOGLE_MAPS_API_KEY
export LOKITO_PRIVACY_URL="https://your-domain.example/privacy"
export LOKITO_TERMS_URL="https://your-domain.example/terms"
python -m facility_finder.enrich_places --google-map-ids
```

Replace example URLs with actual published policies. For private feedback results:

```bash
read -rs "LOKITO_OWNER_PASSWORD?Owner results password: "
export LOKITO_OWNER_PASSWORD
python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

`LOKITO_FEEDBACK_DB` optionally selects a separate database, used for browser QA. Never reuse the QA database for real research. Configuration changes need a server restart. A fresh installation uses `python -m pip install -r requirements-dev.txt` before tests. Windows setup is in README.

## Files and validation

New modules: `enrichment.py`, `enrich_places.py`, `media.py`, `venue_ui.py`, `google_places.py`, `feedback.py`, `feedback_ui.py` under `facility_finder`. Updated integration: `app.py`, `ui.py`, `maps.py`, `evidence.py`, `assets/lokito.css`. Added `.env.example`, ignore rules, separate enrichment data, tests, documentation and QA screenshots. The original ingestion, normalized facility data, ranking and community schema remain intact.

The original source backup and original-data checksum manifest are in `docs/enrichment-baseline`. Original raw/processed checksums match. The working project is now a Git repository created and pushed by the user; this resumed pass leaves reviewable local changes without automatically publishing them.

All 68 tests pass, including the original 30. Matching, thresholds, ambiguity, geometry, cache preservation, URL/licence handling, mocked Google responses, isolated feedback persistence and consumer fallback journeys are covered. Browser outcomes, screenshots and device limitations are recorded in [ENRICHMENT_QA.md](ENRICHMENT_QA.md).

## Official references and adopted principles

- [Overpass language](https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL): query all relevant object types and retain full geometry plus source receipts; reject timeout/error remarks.
- [OSM Wikidata tag](https://wiki.openstreetmap.org/wiki/Key:wikidata), [Wikipedia tag](https://wiki.openstreetmap.org/wiki/Key:wikipedia), [Wikimedia Commons tag](https://wiki.openstreetmap.org/wiki/Key:wikimedia_commons), [image tag](https://wiki.openstreetmap.org/wiki/Key:image): use explicit object references to resolve media; a URL tag alone is not reuse permission.
- [Wikidata data access](https://www.wikidata.org/wiki/Wikidata:Data_access): resolve entity claims through official endpoints.
- [Commons machine-readable metadata](https://commons.wikimedia.org/wiki/Commons:Machine-readable_data): require creator, licence and source before rendering reusable media.
- [Google Places policies](https://developers.google.com/maps/documentation/places/web-service/policies): retain only Place IDs, show required attribution, publish privacy/terms, and keep Google media off the OSM map page.
- [Text Search (New)](https://developers.google.com/maps/documentation/places/web-service/text-search), [Place Details (New)](https://developers.google.com/maps/documentation/places/web-service/place-details), [Place Photos (New)](https://developers.google.com/maps/documentation/places/web-service/place-photos): request limited fields, fetch fresh photo references on explicit demand, render returned author attributions. Policies were reviewed on 6 October 2026; operators should recheck before deployment.

## Next research experiment

Recruit 5–8 people across commuters, visitors and students. Give each two tasks: find a toilet near a known landmark and find one with a particular access need. Include examples with venue photos, context only and no enrichment. Observe time to choose, whether the venue helped them understand the location, whether they interpret “near” correctly, and whether they mistake a venue photo for the toilet. Ask them to use the feedback form after both tasks; keep only the minimum research notes needed. Assess actual access separately through a small field check rather than treating feedback scores as facility verification. Avoid claiming population-level results from this small pilot.
