# Lokito redesign handover

Completed 22 September 2026. This is the consumer redesign of the existing Jakarta Streamlit MVP, not a new data acquisition or a production deployment.

## What changed and why

Lokito means **Lokasi Toilet**. The product opens directly with the nearest toilet: confirm a starting area → read the featured option → open directions → optionally browse nearby cards or report a real visit. Prayer spaces and drinking water live under Other facilities. Wheelchair, free and public-access requirements are preferences.

Warm paper (#F8F5F0), charcoal (#292622) and terracotta (#A6422A) replace the technical dashboard appearance. A compact original SVG toilet/pin mark takes directional inspiration from the supplied logo; the old wordmark and blue/green palette are not reused. Generous spacing, typography and restrained numbered markers provide the hierarchy. Measured contrast ratios: white on accent 6.12:1, ink on paper 13.85:1, muted copy on paper 5.05:1, accent on paper 5.62:1.

The sidebar, category radio row, KPI strip, primary dataframe and facility selectbox were removed. Nearby cards, a featured recommendation, a designed detail dialog and an explicit Google Maps handoff now form the main journey. The default is the nearest option, not an unsupported “best” recommendation. Data & trust retains the quality audit, source details and downloads; About holds the venture framing.

Cards and numbered map pins use one selected facility ID. Pins sharing identical coordinates resolve through their visible numbered tooltip. Changing filters or origin resets selection to the nearest match. Mobile map framing includes both the starting point and selected place; 60 results render on the map, including a selected result farther down the list. All results remain available through progressive card pagination.

## Preserved truth and functionality

The original ingestion, normalization, Haversine ranking, strict tag filters, data-quality audit, cache fallback and SQLite persistence remain. The 5,824 real OSM records are unchanged: 141 toilets, 5,645 places of worship and 38 water points. All raw/processed file SHA-256 hashes match the pre-redesign baseline. No data refresh was performed.

Unknown fields become one concise message, not positive claims. OSM edits/downloads are not verification dates. No ratings, live opening state, walking time, cleanliness or field verification have been invented. Google Maps provides route information after the external handoff. Community confirmations and change reports are saved locally as pending observations; they cannot award a verified badge. An accuracy confirmation does not infer availability.

## Validation

- Baseline: 15 tests passed before editing; original UI inspected in the browser. The workspace had no Git repository, so relevant originals were saved under `docs/redesign-baseline/`.
- Final: **30 tests passed** (`python -m pytest -q`, 4.22 seconds); Python compile check passed.
- All 13 original core tests are unchanged. AppTest journeys were migrated to the new controls and expanded to five tests. Twelve presentation cases cover directions encoding/invalid coordinates, unknowns, distance text, nearest/selected state, mobile framing and co-located map selection.
- UI coverage: default discovery, all categories, custom location, strict preferences, empty results/recovery, pagination, card selection/reset, Data & trust/About navigation, dialog reports and accuracy confirmation. Submission tests use temporary SQLite databases. Real community report count after QA: **0**.
- Browser testing verified actual map tiles, clusters, numbered pin selection updating the featured card and directions destination, card selection updating the map, details, category switching, preferences and empty-state recovery. The external directions URL was inspected and parsed in tests; Google Maps route computation was not assessed.

## Responsive and accessibility QA

| Viewport | Checks and observed result |
|---|---|
| 1440 × 1000 desktop | Consumer header, featured card left and map right; clear primary directions action; warm neutral map tiles and selected marker. |
| 1280 × 900 laptop | Cards/map retained side by side; live pin 5 selected the matching featured card and changed the directions URL. |
| 768 × 1024 tablet | Map above recommendation, 300px map height, 712px usable card width; document width exactly 768px. |
| 430 × 932 mobile | 220px map; clear empty-state recovery; filter panel and detail dialog fit the screen; document width exactly 430px. |
| 390 × 844 mobile | Toilet, prayer and water journeys; selected pin visible in compact map; known/unknown details and longer names; document width exactly 390px. |

Main action buttons are 44px high. Toolbar controls and map zoom targets were increased to 44px after measurement. Markers retain smaller visual symbols to keep the map readable. Text labels and pin numbers supplement color; CSS provides visible keyboard focus and honors reduced-motion preferences. Keyboard Tab navigation was checked: the focused About button had a visible 3px outline. The 54-character real facility name “HKBP Distrik VIII DKI Jakarta Ressort Palmerah-Petamburan” wrapped within a 354px mobile card without horizontal overflow. This was browser viewport QA, not a physical-device or complete assistive-technology accessibility certification.

## Implementation inventory

- `app.py`: discovery state, responsive layout, popovers, directions and observation dialog.
- `assets/lokito.css`, `assets/lokito-mark.svg`: reusable visual identity and responsive rules.
- `facility_finder/presentation.py`: pure selection, distance/unknown formatting, map framing and URL helpers.
- `facility_finder/ui.py`: brand, featured/nearby cards and detail rendering.
- `facility_finder/evidence.py`: separate source/trust and venture content.
- `facility_finder/maps.py`: numbered markers, selected state, neutral map and safe popups.
- `.streamlit/config.toml`, `requirements.txt`: warm theme and Streamlit 1.63 minimum for controlled popovers. The exact tested environment is in `requirements-lock.txt`.
- `tests/test_app.py`, `tests/test_presentation.py`: updated journeys and focused pure-logic coverage.
- `README.md`, `PROJECT_STATUS.md`, `docs/VENTURE_BRIEF.md`, this document: current setup, boundaries and lecturer demo. Original QA remains historical in `docs/QA_RESULTS.md`.

## References and adopted principles

- [Google Maps URLs](https://developers.google.com/maps/documentation/urls/get-started): a clear, lightweight external directions handoff using `api=1`, coordinates and walking mode. Lokito does not claim ownership of route calculation.
- [Airbnb: Using search filters](https://www.airbnb.com/help/article/479): needs such as amenities/accessibility belong in discoverable preferences, leaving initial discovery simple. No proprietary layout/assets were copied.
- [AccessAble: What is an Access Guide?](https://www.accessable.co.uk/what-is-an-access-guide): factual, specific access information helps a person judge suitability. Sparse tags should not become broad verification claims.
- Installed Streamlit API documentation and streamlit-folium implementation were inspected for popover state, dialogs and the actual marker event payload.

## Limits and deliberately deferred work

Streamlit reruns and iframe replacement can briefly redraw the map when selection changes; this is not a continuously animated native map. Mobile visual order puts the map first while semantic DOM order keeps the recommendation before the map. CSS uses named containers plus Streamlit test IDs, so dependency upgrades need visual regression checks. Very dense map clusters require zooming before selecting an individual pin.

Map tiles and frontend libraries need network access or browser cache. Data remain a dated seed snapshot with sparse metadata; field verification is still the highest-value next step. Browser geolocation, in-app routing, authentication, moderation tools, production abuse controls, provider accounts, payments and nationwide expansion are deliberately deferred. No framework migration or new backend was introduced.
