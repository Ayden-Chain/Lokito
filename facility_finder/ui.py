"""Small presentation helpers; native Streamlit controls retain keyboard behaviour."""
from html import escape
from pathlib import Path

import streamlit as st

from facility_finder.presentation import facility_name, distance_label, known_details, unknown_summary, LABELS
from facility_finder.venue_ui import display_title, context_copy

ROOT = Path(__file__).resolve().parents[1]


def html(value):
    st.markdown(value, unsafe_allow_html=True)


def brand():
    mark = (ROOT / 'assets/lokito-mark.svg').read_text()
    html(f'<div class="brand" aria-label="Lokito, Jakarta">{mark}<span class="brand-name">lokito</span>'
         '<span class="brand-city">JAKARTA</span></div>')


def featured_content(row, nearest):
    number = int(row['result_number'])
    label = 'Nearest option' if nearest else 'Your selected option'
    html(f'<div class="feature-label"><span class="index-dot">{number}</span>{label}</div>'
         f'<h2 class="facility-title">{escape(display_title(row))}</h2>'
         f'<div class="distance-line"><strong>{distance_label(row["distance_km"])}</strong> away · {LABELS[row["facility_category"]]}</div>')
    html(context_copy(row))
    chips = known_details(row)
    if chips:
        html('<div class="chips">' + ''.join(f'<span class="chip">{escape(value)}</span>' for _, value, _ in chips[:3]) + '</div>')
    missing = unknown_summary(row, compact=True)
    if missing:
        html(f'<p class="unknown-note">{escape(missing)}</p>')


def nearby_content(row):
    details = known_details(row)
    fact = details[0][1] if details else 'Details not yet added'
    html(f'<div class="small-card"><span class="small-number">{int(row["result_number"])}</span>'
         f'<div class="small-card-info"><h3>{escape(display_title(row))}</h3>'
         f'<p>{distance_label(row["distance_km"])} away · {escape(fact)}</p></div></div>')


def details_content(row):
    html(f'<h2 class="facility-title">{escape(display_title(row))}</h2>'
         f'<div class="distance-line"><strong>{distance_label(row["distance_km"])}</strong> straight-line distance · {LABELS[row["facility_category"]]}</div>')
    details = known_details(row)
    for field, label in [('address', 'Address'), ('operator', 'Managed by'), ('changing_table', 'Changing table'),
                         ('religion', 'Religion'), ('denomination', 'Denomination'), ('wheelchair:description', 'Wheelchair notes')]:
        value = row.get(field, 'unknown')
        if value and value != 'unknown':
            if field == 'changing_table':
                value = {'yes':'Available', 'no':'Not available'}.get(value, value)
            details.append((label, str(value), field))
    if details:
        html('<dl class="detail-list">' + ''.join(f'<div><dt>{escape(label)}</dt><dd>{escape(value)}</dd></div>' for label, value, _ in details) + '</dl>')
    missing = unknown_summary(row)
    if missing:
        html(f'<div class="detail-message">{escape(missing)}</div>')
    st.caption('Listed information has not been checked by Lokito. Current availability and cleanliness are not confirmed.')
    if row.get('coordinate_method') == 'OSM bounding-box center':
        st.caption('The pin marks the facility area. The entrance may be elsewhere.')
    if row['facility_category'] == 'place_of_worship':
        st.caption('Entry rules vary. A place of worship may not offer a public prayer room.')
    elif row['facility_category'] == 'drinking_water':
        st.caption('This is a mapped drinking-water point, not a recent water-quality check.')
