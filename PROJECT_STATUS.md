# Project status — Lokito

As of **11 October 2026**. The venue-context, photo and product-feedback iteration is implemented on the existing consumer redesign. No production deployment has been performed. The earlier redesign record remains below; current evidence and setup are in [the enrichment handover](docs/ENRICHMENT_HANDOVER.md) and [QA record](docs/OSM_MAP_QA.md).

## October additions

- 5,120 named OSM venues from a separate geometry snapshot; 1,170 original facilities receive context: 0 explicit associations, 40 contained nodes, 1,130 proximity matches.
- Among 141 toilets: 65 receive context (16 inside, 49 near); 24 have licensed venue photos. All categories combined: 41 facility associations have photos. The independent catalog contains 28 photographed venues, including Plaza Indonesia and Grand Indonesia.
- Wikimedia photographs carry creator, licence and source links. Optional Google Places uses explicit API calls, ID-only disk caching and a separate photo page; no key was configured for live Google QA.
- Product feedback has its own SQLite database and owner-gated summary. Facility report previews show only structured fields with moderation status, directly on the featured card/details. Private notes and identities stay private. Existing local observations were preserved; test submissions use temporary databases.
- **83 automated tests pass.** Raw and processed facility checksums still match the pre-change baseline.
- Interactive OSM overview restored, with blue mall/SPBU markers separate from brown unverified toilets and a distinct starting point. At Bundaran HI: 43 toilets and 116 venue landmarks within 5 km. Desktop list scrolls independently with persistent controls; mobile uses normal page scrolling. Google Maps remains an outbound coordinate/directions action. Current preview: [Lokito](http://127.0.0.1:8501/); port 8502 is also restored. See [current QA](docs/OSM_MAP_QA.md). Physical pinch and hardware trackpad checks remain outstanding.

## September baseline (historical)

## Completed

- Toilet-first experience with Lokito branding, warm palette and original SVG mark.
- Immediate nearest recommendation, nearby cards, compact location/preferences, secondary facility categories and external Google Maps directions.
- Coordinated card/map selection, including OSM objects sharing coordinates; progressive browsing and empty-state recovery.
- Designed facility details and lightweight observations, persisted locally as pending review.
- Separate Data & trust and About views, preserving evidence and venture discussion.
- Responsive browser inspection at 1440, 1280, 768, 430 and 390px widths.
- **30 automated tests passed**, including all 13 unchanged original core tests; Python compilation passed.
- All real raw/processed data hashes unchanged. The seed remains 5,824 records (141 toilets, 5,645 worship objects, 38 water points). Real community reports after QA: 0; tests use isolated databases.
- Updated setup and lecturer demo. Local preview: [Lokito](http://127.0.0.1:8501); restart instructions are in README if the process stops.

## Remaining boundaries

- Metadata and coverage are incomplete; no field verification or live availability guarantee.
- Physical duplicate review remains outstanding; separate source IDs are preserved.
- Reports are local and anonymous; no authenticated contributor or moderation workflow.
- Maps depend on network tiles/frontend assets. Streamlit reruns can redraw the map; viewport QA is not a real-device certification.
- Demand, partner willingness to pay and economics remain hypotheses.
- GPS, in-app routing, additional categories, provider onboarding, payments and geographic expansion are deferred.

The source snapshot was downloaded **2026-09-14T13:15:32.318207+00:00** (OSM base **2026-09-14T13:14:00Z**). Neither timestamp indicates facility verification.

See [redesign handover](docs/REDESIGN_NOTES.md), [data quality](DATA_QUALITY.md), [venture/demo brief](docs/VENTURE_BRIEF.md), and the historical [original MVP QA](docs/QA_RESULTS.md). Next: a small field-verified pilot and observed user task tests.
