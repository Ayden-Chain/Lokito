# Jakarta facility seed: data-quality assessment

Snapshot downloaded: **2026-09-14T13:15:32.318207+00:00**. OSM database timestamp: **2026-09-14T13:14:00Z**.

Scope: Jakarta administrative area, ISO3166-2=ID-JK. Grain: **one qualifying OSM node, way, or relation**. Counts are mapped objects, not a census of unique physical facilities.

## Profile

**5,824 normalized records**.

| Category | Records |
|---|---:|
| Toilet | 141 |
| Prayer / worship | 5,645 |
| Drinking water | 38 |

OSM element types: node: 315, relation: 7, way: 5,502.

## Metadata completeness

Known means a nonempty source value, not independently verified accuracy. Denominator is all retained records; missing values are `unknown`.

| Attribute | Known | Total | Coverage |
|---|---:|---:|---:|
| name | 5,393 | 5,824 | 92.60% |
| access | 45 | 5,824 | 0.77% |
| opening_hours | 14 | 5,824 | 0.24% |
| wheelchair | 36 | 5,824 | 0.62% |
| fee | 27 | 5,824 | 0.46% |

### Per-category completeness

| Category | Name | Access | Hours | Wheelchair | Fee |
|---|---:|---:|---:|---:|---:|
| Toilet | 11.35% | 30.50% | 2.13% | 11.35% | 16.31% |
| Prayer / worship | 94.72% | 0.00% | 0.19% | 0.32% | 0.00% |
| Drinking water | 78.95% | 5.26% | 0.00% | 5.26% | 10.53% |

## Integrity checks

- Raw qualifying elements: 5,824.
- Rejected missing/invalid coordinates: 0.
- Duplicate OSM type/ID elements removed: 0.
- Rejected malformed identifiers: 0.
- Duplicate IDs in normalized output: 0.
- Missing/invalid coordinates in normalized output: 0.
- Same-category pairs within 30 m: 104. These are review candidates, not confirmed duplicates.
- Coordinates are checked for finite values and global bounds. Jakarta scope is enforced by the Overpass administrative-area query; tests also check a regional bounding envelope.
- Nodes retain their point. Ways/relations use bounding-box centers, which may not identify entrances or lie inside complex footprints.

## Findings and practical impact

**High — incomplete metadata (high confidence).** The measured coverage above limits decisions about entry, fees, opening and wheelchair access. Preserve unknowns; field-check these attributes before promising reliable access. Strict filters intentionally exclude unknowns and can return few or zero options.

**High — seed coverage is not complete facility coverage (high confidence).** OSM mapping effort varies. The category counts cannot establish how many real facilities Jakarta has or how demand varies by area. Indoor amenities and some neighborhoods may be underrepresented. Prioritize field surveys in a small test area. No neighborhood coverage score is claimed without an authoritative denominator.

**Medium — possible multiple representations (high confidence in proximity, low confidence in duplication).** 104 pairs were flagged. Review the IDs in `data/processed/quality.json` before merging; nearby toilets or worship buildings can legitimately be distinct. Physical-facility counts may be overstated.

**High — operational freshness unknown (high confidence).** Download and OSM edit timestamps are provenance only. There are no field-verification records in the seed. Availability, cleanliness and current water safety are unknown. A new download cannot resolve this gap.

**Medium — category semantics (high confidence).** `place_of_worship` spans religions and is not synonymous with a public Muslim prayer room. `wheelchair=yes` on a worship building describes that object, not every amenity inside it. Accessibility results cover only the three seed categories. `amenity=drinking_water` describes mapped intended use, not a recent water test.

## Feasibility conclusion

The snapshot supports a technical seed-data demonstration of map discovery, filters and geographic ranking. It is not sufficient evidence for complete coverage, live availability or consistently suitable facilities. The highest-value next data work is field verification and targeted enrichment, especially where metadata is absent.

## Reproducibility and temporal limits

Run `python -m facility_finder.ingest` to normalize the saved raw snapshot without network access; run `python -m facility_finder.report` to rebuild this report. Inspect `docs/data_audit.ipynb` or the functions in `facility_finder/data.py` for calculations. This is a one-snapshot audit; no historical trend or freshness SLA has been established.

## Source receipt

- Source system: OpenStreetMap via Overpass, © OpenStreetMap contributors, ODbL.
- Evidence: `data/raw/latest.json` includes the exact query, endpoint, retrieval timestamp and original response; immutable individual snapshots are listed below.
- Derived artifacts: `data/processed/facilities.json`, `facilities.csv`, and `quality.json`.
- All metrics use the local snapshot only; no external business metrics or fabricated verification data.
- Primary tag documentation: [toilets](https://wiki.openstreetmap.org/wiki/Tag:amenity%3Dtoilets), [worship](https://wiki.openstreetmap.org/wiki/Tag:amenity%3Dplace_of_worship), [drinking water](https://wiki.openstreetmap.org/wiki/Tag:amenity%3Ddrinking_water), [wheelchair](https://wiki.openstreetmap.org/wiki/Key:wheelchair), [Overpass](https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL).

- `data/raw/2026-09-14T13-15-32_2b42ece403d3.json`
