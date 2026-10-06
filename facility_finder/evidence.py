"""Secondary evidence and venture views, kept out of the consumer journey."""
import json

import pandas as pd
import streamlit as st

from facility_finder.data import CATEGORY_LABELS
from facility_finder.presentation import facility_name
from facility_finder.ui import html


def render_trust(facilities, quality, selected_id, enrichment=None):
    html('<div class="eyebrow">Behind the pin</div><h1>Useful information.<br>Honest about the gaps.</h1>'
         '<p class="evidence-lead">Lokito starts with community-mapped places. We show what is listed and leave room for what still needs checking.</p>')
    st.subheader('Three different kinds of information')
    st.markdown('**Listed details** come from OpenStreetMap. **Visitor observations** are saved locally and await review. '
                '**Lokito verification** has not started: no place is shown as checked by us.')
    st.caption(f"Snapshot downloaded {quality['fetched_at'][:10]}. This is not live availability.")
    if enrichment:
        with st.expander('Venue context and photographs'):
            st.write('Near means proximity to a venue centre, not membership. At requires an explicit source association. Inside means a mapped facility node lies within a complete venue boundary; it does not confirm the floor, entrance or access.')
            st.write('Venue photographs are resolved through the venue’s Wikimedia or Wikidata reference and show the surrounding place, not necessarily the toilet. Creator and licence links appear with each photograph. Missing or unsupported images are omitted.')
            st.write('Context, media and product feedback do not establish facility verification. Search also matches enriched venue names.')
            st.json(enrichment.get('metadata',{'status':'No enrichment cache available'}))
            context=enrichment.get('records',{}).get(selected_id)
            if context: st.json(context)
    a, b = st.columns(2)
    with a:
        st.subheader('The Jakarta snapshot')
        st.dataframe(pd.DataFrame([{'Facility':CATEGORY_LABELS[k], 'Mapped places':v} for k,v in quality['by_category'].items()]), hide_index=True, use_container_width=True)
    with b:
        st.subheader('What is listed')
        st.dataframe(pd.DataFrame([{'Detail':k.replace('_',' ').title(), 'Known':v['known'], 'Coverage (%)':v['percent']} for k,v in quality['completeness'].items()]), hide_index=True, use_container_width=True)
    st.write(f"{quality['total_facilities']:,} OSM objects, not a confirmed count of unique physical facilities. "
             f"{quality['near_duplicate_pair_count']} same-category pairs within 30 metres need review.")
    with st.expander('How preferences and distances work'):
        st.write('Wheelchair accessible matches wheelchair=yes/designated; Free to use matches fee=no; '
                 'Open to the public matches access=yes/permissive. Unknown and limited wheelchair access do not pass the accessibility filter. '
                 'These are source claims, not field checks by Lokito. Being listed does not guarantee a facility is open now.')
        st.write('Distances use the Haversine formula and are straight-line estimates. Directions open Google Maps with your chosen starting point and destination; Lokito does not calculate routes or travel time.')
        st.write('Map markers are limited to the nearest 60 matches, plus the selected facility when needed. All matches remain browsable through Show more nearby.')
    with st.expander('Coverage, integrity and limitations'):
        st.write(f"Scope: {quality['scope']}. OSM database timestamp: {quality['osm_base_timestamp']}.")
        st.write(f"Duplicate normalized IDs: {quality['normalized_duplicate_ids']}. Rejected coordinates: {quality['ingestion']['missing_or_invalid_coordinates']}.")
        st.write('Mapping effort varies by neighborhood. Indoor toilets and prayer rooms may be missing. Worship facilities may restrict entry. Drinking-water points are not current water-quality tests. Area centers may differ from entrances.')
        st.write('Facility data work from the local cache. Map tiles and frontend map assets need internet or browser caching. The map uses OpenStreetMap tiles; attribution is also visible on the map.')
        st.dataframe(pd.DataFrame([{'Category':CATEGORY_LABELS[cat], 'Attribute':field, **counts}
                                  for cat, values in quality['completeness_by_category'].items() for field,counts in values.items()]), hide_index=True)
    match = facilities[facilities.facility_id == selected_id]
    if len(match):
        row = match.iloc[0].to_dict()
        with st.expander('Source details for your selected place'):
            st.write(facility_name(row))
            st.link_button('Original OpenStreetMap record ↗', row['source_url'])
            st.write('Source identifier:', row['facility_id'])
            st.write('Coordinates:', f"{row['latitude']:.7f}, {row['longitude']:.7f}")
            st.write('Coordinate method:', row['coordinate_method'])
            st.write('Downloaded:', row['last_data_refresh'])
            st.write('OSM last edited:', row['osm_last_edited'])
            st.write('OSM check date:', row['osm_check_date'])
            st.caption('None of these timestamps is a verification by Lokito.')
            st.json(row['tags'])
    st.download_button('Download quality audit', json.dumps(quality, indent=2), 'lokito-data-quality.json', 'application/json')
    st.download_button('Download facility dataset', facilities.drop(columns=['tags','venue_context'],errors='ignore').to_csv(index=False).encode('utf-8'), 'lokito-facilities.csv', 'text/csv')
    st.markdown('Data: [© OpenStreetMap contributors, ODbL](https://www.openstreetmap.org/copyright). '
                'Data source and raw snapshots are preserved in the project folder.')


def render_about():
    html('<div class="eyebrow">Lokasi Toilet → Lokito</div><h1>A small stop shouldn’t<br>be a big search.</h1>'
         '<p class="evidence-lead">Finding a nearby place is easy. Knowing whether you can use its toilet is another story.</p>')
    a, b = st.columns(2, gap='large')
    with a:
        st.subheader('A focused start')
        st.write('Lokito helps people find nearby toilets and see the details that matter: access, cost and accessibility. '
                 'It starts in Jakarta, with prayer spaces and drinking water available when needed.')
        st.subheader('Information people can rely on')
        st.write('Public mapping gives us a starting point. Field checks, community observations and facility-owner updates are the next step. '
                 'The intended long-term value is reliable facility information, not just pins on a map.')
    with b:
        st.subheader('A venture to test')
        st.write('Potential partners include campuses, malls, property managers and transport operators. '
                 'Provider profiles, directory partnerships and aggregated analytics are business hypotheses, not established revenue.')
        st.subheader('Prove it locally, then grow')
        st.write('Test real toilet-finding tasks and field-check one small area first. '
                 'Expansion to Jabodetabek and other Indonesian cities should follow evidence of demand and a repeatable verification process.')
    st.caption('Academic Venture Creation prototype. No live availability, independent facility verification or validated business results are claimed.')
