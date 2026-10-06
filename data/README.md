# Data provenance

The `raw` and `processed` folders contain real OpenStreetMap-derived data, © OpenStreetMap contributors, under the [Open Database License](https://www.openstreetmap.org/copyright).

`raw/latest.json` records the complete successful Jakarta query, Overpass endpoint, fetch timestamp, administrative area metadata and original API response. The timestamped file is the immutable source snapshot. `processed/facilities.json` and `facilities.csv` contain normalized OSM objects; `quality.json` contains reproducible audit results and all 104 proximity-review pairs for the initial snapshot.

Unknown attributes remain unknown. There are no synthetic facility rows or pre-existing community reports. `community.sqlite3` is created locally with an empty report table when the app opens; it stores only subsequently submitted observations and is excluded from git.

Run `python -m facility_finder.ingest` from the project root to reproduce normalization from the saved raw data. `--refresh` explicitly requests a new source snapshot. The initial snapshot was downloaded on 2026-09-14; it is not a live feed and does not confirm current facility status.
