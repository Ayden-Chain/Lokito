# Venue enrichment and feedback QA — 6 October 2026

This record covers the October implementation, including the final resumed pass after the user pushed the initial work to GitHub. It does not claim physical-device certification or a live Google Places test.

## Automated validation

Baseline: 30 tests passed before edits. Final: **68 tests passed** with the existing 30 preserved. Run `python -m pytest -q` from the activated project environment. The suite blocks live HTTP requests globally; Places response tests use mock sessions. Files and SQLite databases created by tests use pytest temporary directories.

Coverage includes explicit association; polygon containment, holes and boundaries; invalid geometry; non-node containment rejection; all nine distance thresholds; ambiguity; deterministic matching; duplicate/unnamed venues; long names and escaping; cache generation, malformed/empty caches and byte-for-byte preservation on failed refresh; Wikimedia parsing, licence and URL validation; missing photos; disabled and mocked Google calls; feedback validation, minimal context, idempotency, persistence and owner gating; and real consumer journeys with/without enrichment.

An additional final fix accepts non-ASCII characters in an owner's password by comparing encoded bytes. The owner-gate AppTest now exercises that case. Malformed nested Wikimedia metadata is rejected cleanly and malformed Google type lists are ignored safely.

## Browser checks

Actual Streamlit server on `127.0.0.1:8502`, with `LOKITO_FEEDBACK_DB=/private/tmp/lokito-qa-feedback-20261006.sqlite3` and a temporary QA-only owner password. The Google key was absent. The ordinary application at port 8501 was not used for test submissions.

| Viewport | Observed outcome |
|---|---|
| 1440 × 1000 | Desktop columns, real station photo and attribution, directions above photo, map and selected card coordinated |
| 1280 × 900 | Laptop layout inspected; no horizontal overflow |
| 768 × 1024 | Map stacks above results at 300 px; recommendation and directions readable |
| 430 × 932 | Full featured card/photo inspected; text wraps and no horizontal overflow |
| 390 × 844 | Map is 220 px; primary buttons are 44 px high; image is 312 × 136.5 px (16:7); no horizontal overflow |

The image crop was finalized at 16:7 after the first desktop/tablet screenshots. The final desktop and mobile-card screenshots show that version. Mobile directions remain above the photo; depending on viewport and title length, a short page scroll is needed to reach them.

| Scenario | Result and evidence |
|---|---|
| Real venue photograph | Balai Kota transit station rendered from Commons; creator Irvan Cahyo N, CC BY-SA 4.0 and Commons links visible |
| Venue without photograph | Pondok Indah Mall 1 contextual toilets displayed with mapped containment; no placeholder pretending to be a place photo |
| Unnamed toilet without enrichment | Bundaran HI result 3 retains “Toilet”, source access information, directions and details |
| SPBU context | Pertamina Perdatam and SPBU Pertamina COCO 31.139.02 displayed with `near` wording |
| Long venue name | Dinas Kelautan Dan Pertanian UPT Pusat Promosi dan Pemasaran Hasil Hortikuktura wrapped correctly in a phone detail dialog |
| Evidence wording | Near details explicitly say membership is not established; containment details retain entrance/access caveats |
| Map → card | Opened a visible cluster and selected pin 2, Taman Kudus; featured card changed to that facility |
| Card → map | Selected option 4, Balai Kota; selected numbered marker and contextual tooltip updated |
| Zoom | Browser wheel input changed OSM tile zoom from 12 to 16; zoom buttons and cluster expansion also exercised |
| Pinch/trackpad | Folium configuration keeps `touchZoom` and `scrollWheelZoom` enabled. Physical pinch gestures and a hardware trackpad were not available to this browser automation |
| Directions | Visible link points to the chosen facility coordinate; not activated into a navigation session |
| Preferences/empty state | Applied Free to use plus a nonexistent venue query; zero results displayed; Clear preferences restored nearby results |
| Feedback validation | Empty required answers showed a warning and did not save |
| Feedback submission | One response saved successfully in the dedicated temporary QA database; confirmation displayed |
| Private summary | Comment absent before unlock, visible after QA password, absent after Lock results |
| Keyboard focus | Tab reached the photo attribution link with visible focus outline; primary controls retain native keyboard behaviour |
| Missing image | A separate temporary fixture deliberately used a missing Commons thumbnail URL; neutral frame, attribution/source links and an independent button remained rendered |

The missing-image fixture was `/private/tmp/lokito-browser-qa.SzjoHd/fallback.py`, served only on loopback port 8503 and stopped after inspection. It did not edit the real cache. Automated AppTest also covers an entirely absent enrichment cache. A browser failure to load a thumbnail does not crash or remove directions; `photo_shown` records rendered photo markup, not a successful download.

Text and primary actions were visually inspected for readability. Core foreground/background contrast uses the existing dark/warm palette; this was not a full accessibility audit. Google live photos were not checked because there was no configured key/billing/published policy environment. Mocked adapter coverage is not a substitute for that deployment check.

## Data preservation

`shasum -a 256 -c docs/enrichment-baseline/data-sha256.txt` reports OK for both original raw JSON files and the three original processed files. The seed remains 5,824 records: 141 toilets, 5,645 worship places and 38 water points.

`data/product-feedback.sqlite3` was absent after QA. The temporary browser database has exactly one synthetic feedback response. The real community database has one existing observation dated 22 September 2026; it was preserved and no October test report was added. The older September documentation's “0 reports” statement is historical and does not describe the present database.

## Screenshots

- [Final desktop, 1440 px](enrichment-qa/desktop-final-1440.jpg)
- [Laptop, 1280 px](enrichment-qa/laptop-1280.jpg)
- [Tablet, 768 px](enrichment-qa/tablet-768.jpg)
- [Final mobile card, 430 px](enrichment-qa/mobile-card-430.jpg)
- [Mobile photo and keyboard focus, 390 px](enrichment-qa/mobile-photo-390.jpg)
- [Feedback confirmation](enrichment-qa/feedback-mobile.jpg)
- [Deliberately unavailable image fixture](enrichment-qa/missing-image-fixture.jpg)

Before a public pilot, check a physical iPhone/Android device and trackpad, configure durable feedback storage and owner access on the chosen host, and perform any live Google test with the operator's own restricted key and billing limits.
