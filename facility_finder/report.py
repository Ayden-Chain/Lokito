"""Rebuild the human-readable data audit from the real cached snapshot."""
import json
from pathlib import Path

from facility_finder.data import CATEGORY_LABELS, PROCESSED
from facility_finder.ingest import ROOT


def main():
    q = json.loads((PROCESSED / "quality.json").read_text())
    lines = ["# Jakarta facility seed: data-quality assessment", "",
             f"Snapshot downloaded: **{q['fetched_at']}**. OSM database timestamp: **{q['osm_base_timestamp']}**.", "",
             f"Scope: {q['scope']}. Grain: **{q['grain']}**. Counts are mapped objects, not a census of unique physical facilities.", "",
             "## Profile", "", f"**{q['total_facilities']:,} normalized records**.", "",
             "| Category | Records |", "|---|---:|"]
    for category, count in q["by_category"].items():
        lines.append(f"| {CATEGORY_LABELS[category]} | {count:,} |")
    lines += ["", "OSM element types: " + ", ".join(f"{k}: {v:,}" for k, v in q["by_osm_type"].items()) + ".",
              "", "## Metadata completeness", "", "Known means a nonempty source value, not independently verified accuracy. Denominator is all retained records; missing values are `unknown`.",
              "", "| Attribute | Known | Total | Coverage |", "|---|---:|---:|---:|"]
    for field, counts in q["completeness"].items():
        lines.append(f"| {field} | {counts['known']:,} | {counts['total']:,} | {counts['percent']:.2f}% |")
    lines += ["", "### Per-category completeness", "", "| Category | Name | Access | Hours | Wheelchair | Fee |", "|---|---:|---:|---:|---:|---:|"]
    for cat, fields in q["completeness_by_category"].items():
        lines.append("| " + CATEGORY_LABELS[cat] + " | " + " | ".join(f"{fields[f]['percent']:.2f}%" for f in ("name", "access", "opening_hours", "wheelchair", "fee")) + " |")
    lines += ["", "## Integrity checks", "",
              f"- Raw qualifying elements: {q['ingestion']['raw_facility_elements']:,}.",
              f"- Rejected missing/invalid coordinates: {q['ingestion']['missing_or_invalid_coordinates']:,}.",
              f"- Duplicate OSM type/ID elements removed: {q['ingestion']['duplicate_osm_elements_removed']:,}.",
              f"- Rejected malformed identifiers: {q['ingestion']['rejected_identifiers']:,}.",
              f"- Duplicate IDs in normalized output: {q['normalized_duplicate_ids']:,}.",
              f"- Missing/invalid coordinates in normalized output: {q['normalized_missing_coordinates']:,}.",
              f"- Same-category pairs within 30 m: {q['near_duplicate_pair_count']:,}. These are review candidates, not confirmed duplicates.",
              "- Coordinates are checked for finite values and global bounds. Jakarta scope is enforced by the Overpass administrative-area query; tests also check a regional bounding envelope.",
              "- Nodes retain their point. Ways/relations use bounding-box centers, which may not identify entrances or lie inside complex footprints.",
              "", "## Findings and practical impact", "",
              "**High — incomplete metadata (high confidence).** The measured coverage above limits decisions about entry, fees, opening and wheelchair access. Preserve unknowns; field-check these attributes before promising reliable access. Strict filters intentionally exclude unknowns and can return few or zero options.",
              "", "**High — seed coverage is not complete facility coverage (high confidence).** OSM mapping effort varies. The category counts cannot establish how many real facilities Jakarta has or how demand varies by area. Indoor amenities and some neighborhoods may be underrepresented. Prioritize field surveys in a small test area. No neighborhood coverage score is claimed without an authoritative denominator.",
              "", f"**Medium — possible multiple representations (high confidence in proximity, low confidence in duplication).** {q['near_duplicate_pair_count']:,} pairs were flagged. Review the IDs in `data/processed/quality.json` before merging; nearby toilets or worship buildings can legitimately be distinct. Physical-facility counts may be overstated.",
              "", "**High — operational freshness unknown (high confidence).** Download and OSM edit timestamps are provenance only. There are no field-verification records in the seed. Availability, cleanliness and current water safety are unknown. A new download cannot resolve this gap.",
              "", "**Medium — category semantics (high confidence).** `place_of_worship` spans religions and is not synonymous with a public Muslim prayer room. `wheelchair=yes` on a worship building describes that object, not every amenity inside it. Accessibility results cover only the three seed categories. `amenity=drinking_water` describes mapped intended use, not a recent water test.",
              "", "## Feasibility conclusion", "",
              "The snapshot supports a technical seed-data demonstration of map discovery, filters and geographic ranking. It is not sufficient evidence for complete coverage, live availability or consistently suitable facilities. The highest-value next data work is field verification and targeted enrichment, especially where metadata is absent.",
              "", "## Reproducibility and temporal limits", "",
              "Run `python -m facility_finder.ingest` to normalize the saved raw snapshot without network access; run `python -m facility_finder.report` to rebuild this report. Inspect `docs/data_audit.ipynb` or the functions in `facility_finder/data.py` for calculations. This is a one-snapshot audit; no historical trend or freshness SLA has been established.",
              "", "## Source receipt", "",
              "- Source system: OpenStreetMap via Overpass, © OpenStreetMap contributors, ODbL.",
              "- Evidence: `data/raw/latest.json` includes the exact query, endpoint, retrieval timestamp and original response; immutable individual snapshots are listed below.",
              "- Derived artifacts: `data/processed/facilities.json`, `facilities.csv`, and `quality.json`.",
              "- All metrics use the local snapshot only; no external business metrics or fabricated verification data.",
              "- Primary tag documentation: [toilets](https://wiki.openstreetmap.org/wiki/Tag:amenity%3Dtoilets), [worship](https://wiki.openstreetmap.org/wiki/Tag:amenity%3Dplace_of_worship), [drinking water](https://wiki.openstreetmap.org/wiki/Tag:amenity%3Ddrinking_water), [wheelchair](https://wiki.openstreetmap.org/wiki/Key:wheelchair), [Overpass](https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL).", ""]
    lines += [f"- `data/raw/{name}`" for name in q["raw_files"]]
    (ROOT / "DATA_QUALITY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Wrote DATA_QUALITY.md")


if __name__ == "__main__":
    main()
