"""Run: streamlit run app.py"""
import json
import sqlite3
from html import escape

import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from facility_finder.community import add_report, list_reports
from facility_finder.data import (CATEGORY_LABELS, PROCESSED, UNKNOWN, display_name,
                                  filter_facilities, load_facilities, rank_nearest)
from facility_finder.maps import build_map

st.set_page_config(page_title="Dekat · Find what you need", page_icon="📍", layout="wide")
st.markdown("""<style>
    .block-container {padding-top:4rem; max-width:1500px}
    h1 {letter-spacing:-.045em} h2 {letter-spacing:-.025em}
    [data-testid="stMetric"] {background:white;border:1px solid #E5EAF0;border-radius:14px;padding:14px 18px}
    .eyebrow {color:#087F75;font-size:12px;font-weight:750;letter-spacing:.15em;margin-bottom:8px}
    .lead {font-size:18px;color:#536678;max-width:760px;margin-bottom:24px}
</style>""", unsafe_allow_html=True)


@st.cache_data
def read_cache(modified):
    return load_facilities(), json.loads((PROCESSED / "quality.json").read_text())


try:
    modified = ((PROCESSED / "facilities.json").stat().st_mtime_ns,
                (PROCESSED / "quality.json").stat().st_mtime_ns)
    facilities, quality = read_cache(modified)
except (OSError, ValueError, KeyError) as exc:
    st.title("Dekat")
    st.error(f"Cannot load the local facility dataset: {exc}")
    st.code("python -m facility_finder.ingest")
    st.info("Run this command from the project folder, then reload this page.")
    st.stop()

st.markdown('<div class="eyebrow">DEKAT / JAKARTA PILOT</div>', unsafe_allow_html=True)
st.title("Find what you need. Nearby.")
st.markdown('<div class="lead">A toilet, a place to pray, a drink of water. '
            'Start with your need and discover mapped facilities around you.</div>', unsafe_allow_html=True)
discover, evidence, venture = st.tabs(["Explore facilities", "Data & trust", "The venture"])

with st.sidebar:
    st.markdown("### Your starting point")
    st.caption("Choose an approximate location. No GPS permission needed.")
    presets = {
        "Bundaran HI": (-6.1950, 106.8230),
        "Monas": (-6.1754, 106.8272),
        "Kota Tua": (-6.1352, 106.8133),
        "Blok M": (-6.2444, 106.7990),
        "Custom coordinates": None,
    }
    location = st.selectbox("Start near", list(presets))
    if location == "Custom coordinates":
        lat = st.number_input("Latitude", min_value=-90.0, max_value=90.0, value=-6.195, format="%.6f")
        lon = st.number_input("Longitude", min_value=-180.0, max_value=180.0, value=106.823, format="%.6f")
        origin = (lat, lon)
    else:
        origin = presets[location]
    st.caption(f"Approximate point: {origin[0]:.4f}, {origin[1]:.4f}")
    if not (-6.5 < origin[0] < -5.0 and 106.3 < origin[1] < 107.1):
        st.warning("This starting point is outside the Jakarta pilot vicinity. Results still use Jakarta data only.")
    st.divider()
    st.markdown("### Refine your needs")
    wheelchair = st.checkbox("Wheelchair access tagged yes")
    free = st.checkbox("Free of charge tagged")
    access = st.checkbox("Public access explicitly tagged")
    radius = st.selectbox("Search radius", ["Any distance", "1 km", "3 km", "5 km", "10 km"], index=3)
    st.caption("Strict filters exclude unknown values. Wheelchair: yes/designated; fee: no; access: yes/permissive.")
    st.divider()
    st.caption("LOCAL SNAPSHOT")
    st.write(f"{len(facilities):,} mapped facility records")
    st.caption(f"Downloaded {quality['fetched_at'][:10]} (UTC). This is not live availability.")
    st.markdown("[© OpenStreetMap contributors · ODbL](https://www.openstreetmap.org/copyright)")

with discover:
    st.subheader("What do you need?")
    options = {"🚻 Toilet": ["toilets"], "🕌 Prayer / worship": ["place_of_worship"],
               "💧 Drinking water": ["drinking_water"], "♿ Accessible facility": list(CATEGORY_LABELS),
               "All facilities": list(CATEGORY_LABELS)}
    need = st.radio("Choose a need", list(options), horizontal=True, label_visibility="collapsed")
    col_search, col_religion = st.columns([2, 1])
    search = col_search.text_input("Search name or address", placeholder="Try Istiqlal, a street, or a neighborhood")
    religion = None
    if need == "🕌 Prayer / worship":
        religions = sorted(facilities.loc[facilities.facility_category == "place_of_worship", "religion"].unique())
        chosen = col_religion.selectbox("Religion (OSM tag)", ["All religions"] + religions)
        religion = chosen if chosen != "All religions" else None
        st.caption("Places of worship include multiple religions. This seed does not comprehensively cover indoor prayer rooms.")
    subset = filter_facilities(facilities, options[need], wheelchair or need == "♿ Accessible facility",
                               free, access, search, religion)
    ranked = rank_nearest(subset, *origin)
    if radius != "Any distance":
        ranked = ranked[ranked.distance_km <= float(radius.split()[0])].reset_index(drop=True)
    m1, m2, m3 = st.columns(3)
    m1.metric("Matching mapped facilities", f"{len(ranked):,}")
    m2.metric("Closest straight-line distance", f"{ranked.iloc[0].distance_km:.2f} km" if len(ranked) else "—")
    m3.metric("With wheelchair information", f"{int((ranked.wheelchair != UNKNOWN).sum()):,}")
    st.caption("Distances are straight-line estimates, not walking routes. Access, opening and current condition may be unknown.")
    if not len(ranked):
        st.info("No mapped facilities match these filters. Try a wider radius or fewer restrictions. No results does not mean no facilities exist.")
    map_col, detail_col = st.columns([1.65, 1], gap="large")
    with detail_col:
        st.markdown("### Nearby options")
        if len(ranked):
            # Every matching record is selectable. The map caps markers for classroom laptop performance.
            rows = {r["facility_id"]: r for r in ranked.to_dict("records")}
            selected = st.selectbox("Select a facility · nearest first", list(rows),
                                   format_func=lambda fid: f"{display_name(rows[fid])} · {rows[fid]['distance_km']:.2f} km · {fid}")
            row = rows[selected]
            st.markdown(f"<h3>{escape(display_name(row))}</h3>", unsafe_allow_html=True)
            st.caption(f"{CATEGORY_LABELS[row['facility_category']]} · {row['distance_km']:.2f} km away")
            st.dataframe(pd.DataFrame({"Detail": ["Access", "Fee", "Opening hours", "Wheelchair", "Address", "Religion", "Operator", "Changing table", "Available now", "Cleanliness", "Last community verification"],
                                       "OSM information / status": [row["access"], row["fee"], row["opening_hours"], row["wheelchair"],
                                                                   row["address"], row["religion"], row["operator"], row["changing_table"],
                                                                   "Unknown", "Unknown", "Not verified"]}),
                         hide_index=True, use_container_width=True)
            st.caption("Values are source tags: fee=no means mapped as free; access=customers/private may restrict entry. Unknown is not a confirmation.")
            if row["wheelchair:description"] != UNKNOWN:
                st.write("Wheelchair notes:", row["wheelchair:description"])
            st.link_button("View original OpenStreetMap record ↗", row["source_url"])
            with st.expander("Source and coordinates"):
                st.write(f"OSM ID: {selected}")
                st.write(f"Coordinates: {row['latitude']:.6f}, {row['longitude']:.6f}")
                st.write("Position:", row["coordinate_method"])
                st.write("Downloaded:", row["last_data_refresh"])
                st.write("OSM object last edited:", row["osm_last_edited"])
                st.write("OSM check_date tag:", row["osm_check_date"])
                st.caption("An edit date or mapper check_date is not verification by this platform. Area centers may not identify entrances.")
                st.json(row["tags"])
            with st.expander("Share an observation · local prototype"):
                st.caption("Reports stay on this computer, pending review. They do not change OSM tags or create a verified badge. Do not include personal information.")
                with st.form(f"report_{selected}", clear_on_submit=True):
                    available = st.selectbox("Was the facility available when you visited?", ["unknown", "yes", "no"])
                    cleanliness = st.selectbox("Cleanliness · optional", ["Not assessed", 1, 2, 3, 4, 5],
                                               help="1 = very poor; 5 = very clean")
                    issue = st.text_area("Observation or issue", max_chars=1000)
                    submit = st.form_submit_button("Save local observation")
                if submit:
                    try:
                        add_report(selected, set(facilities.facility_id), available,
                                   None if cleanliness == "Not assessed" else cleanliness, issue)
                        st.success("Observation saved locally, pending review. Facility facts remain unverified.")
                    except (ValueError, sqlite3.Error, OSError) as exc:
                        st.error(f"Could not save observation: {exc}")
                try:
                    reports = list_reports(selected)
                    if reports:
                        st.caption("Most recent local observations (unmoderated)")
                        st.dataframe(pd.DataFrame(reports)[["submitted_at", "available", "cleanliness", "issue", "moderation_status"]], hide_index=True)
                    else:
                        st.caption("No observations yet. Be the first to contribute after a visit.")
                except (sqlite3.Error, OSError) as exc:
                    st.error(f"Cannot read local observations: {exc}")
        else:
            selected = None
            st.caption("Matching facility details will appear here.")
    with map_col:
        visible = ranked.head(400)
        if selected is not None and selected not in set(visible.facility_id):
            visible = pd.concat([visible.head(399), ranked[ranked.facility_id == selected]])
        st_folium(build_map(visible, origin, selected), height=540, use_container_width=True,
                  returned_objects=[], key=f"facility_map_{need}_{selected}_{origin}")
        st.caption(f"Showing {len(visible):,} of {len(ranked):,} matching records. Up to 400 nearest markers; your selected facility is always included. Click a marker for details.")
        st.caption("🟢 Toilet · 🟣 Prayer / worship · 🔵 Drinking water · Person marker: your starting point")
    if len(ranked):
        st.download_button("Download matching results (CSV)", ranked.drop(columns=["tags"]).to_csv(index=False).encode("utf-8"),
                           "dekat-matching-facilities.csv", "text/csv")

with evidence:
    st.subheader("Useful seed data. Visible gaps.")
    st.write("Each record is an OSM object, not a field-verified facility. The audit below covers the complete local snapshot, regardless of search filters.")
    summary = pd.DataFrame([{"Need": CATEGORY_LABELS[k], "Mapped records": v} for k, v in quality["by_category"].items()])
    left, right = st.columns(2)
    left.dataframe(summary, hide_index=True, use_container_width=True)
    coverage = pd.DataFrame([{"Attribute": k.replace("_", " ").title(), "Known records": v["known"], "Coverage (%)": v["percent"]}
                             for k, v in quality["completeness"].items()])
    right.dataframe(coverage, hide_index=True, use_container_width=True)
    st.warning("No live availability, cleanliness score, or platform verification has been inferred from missing tags.")
    st.write(f"**Quality checks:** {quality['normalized_duplicate_ids']} duplicate normalized IDs; "
             f"{quality['ingestion']['missing_or_invalid_coordinates']} source records rejected for missing/invalid coordinates; "
             f"{quality['near_duplicate_pair_count']} same-category pairs within 30 metres flagged for review.")
    st.write("Nearby OSM objects may be separate facilities or duplicate representations (for example a node and a building). They are retained pending review.")
    st.caption(f"Boundary: {quality['scope']}. Download: {quality['fetched_at']}. OSM database timestamp: {quality['osm_base_timestamp']}.")
    with st.expander("Coverage by category"):
        st.dataframe(pd.DataFrame([{"Category": CATEGORY_LABELS[cat], "Attribute": field, **counts}
                                  for cat, values in quality["completeness_by_category"].items()
                                  for field, counts in values.items()]), hide_index=True)
    st.markdown("""- OSM is community maintained; coverage and metadata vary between neighborhoods.
- A mapped place of worship does not guarantee unrestricted entry or a dedicated public prayer room.
- Drinking-water tags describe mapped intent, not a current water-quality test.
- Map tiles need an internet connection; facility search and the saved dataset do not need Overpass.
- Sparse results reveal a data gap, not proven absence of a need or facility.""")
    st.download_button("Download full audit (JSON)", json.dumps(quality, indent=2), "dekat-data-quality.json", "application/json")

with venture:
    st.subheader("From finding places to meeting needs")
    a, b = st.columns(2)
    with a:
        st.markdown("""**The problem**

You can locate a mall or station, yet still struggle to find a toilet, drinking water or a suitable place to pray nearby.

**The solution**

Dekat starts with the facility you need. It exposes access conditions and missing information so you can choose with more context.

**The pilot**

Jakarta first. Test whether people can identify a suitable facility faster, then expand to Jabodetabek and other Indonesian cities.""")
    with b:
        st.markdown("""**The data strategy**

Public OSM seed data → official datasets → community observations → provider submissions. Long-term value comes from recent, reliable facility-level information.

**Business hypotheses**

Provider profiles, partnerships with property managers, campuses and transport operators, clearly labelled promotion, and aggregated facility analytics. These are unvalidated models.

**What this prototype proves**

Real public data can support a need-first discovery flow. It does not yet prove complete coverage, live reliability, market demand or revenue.""")
    st.info("Next validation: observe users completing urgent facility-finding tasks, then field-check a small area with facility operators and accessibility users.")

st.divider()
st.caption("Dekat · Academic Venture Creation MVP · Jakarta pilot · Source: © OpenStreetMap contributors, ODbL. No real-time availability claims.")
