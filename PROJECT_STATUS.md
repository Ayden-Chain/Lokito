# Project status — Lokito

As of **22 September 2026**. The requested consumer redesign is implemented and locally validated. No production deployment has been performed.

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
