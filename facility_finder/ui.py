"""Small presentation helpers; native Streamlit controls retain keyboard behaviour."""
from html import escape
from pathlib import Path

import streamlit as st

from facility_finder.presentation import distance_label, distance_parts, known_details, unknown_summary, LABELS
from facility_finder.venue_ui import display_title, context_copy
from facility_finder.proxies import is_venue, KIND, NOTE, DEFAULT_NOTE

ROOT = Path(__file__).resolve().parents[1]


def html(value):
    st.markdown(value, unsafe_allow_html=True)


def brand():
    mark = (ROOT / 'assets/lokito-mark.svg').read_text()
    html(f'<div class="brand" aria-label="Lokito, Jakarta">{mark}<span class="brand-name">lokito</span>'
         '<span class="brand-city">JAKARTA</span></div>')


def kind_label(row):
    """What the place is, in a few words."""
    if is_venue(row):
        return KIND[row['venue_category']]
    return LABELS[row['facility_category']]


def featured_content(row, nearest):
    """The answer, set like a wayfinding sign: distance first, then the place."""
    number = int(row['result_number'])
    label = 'Terdekat' if nearest else 'Pilihanmu'
    value, unit = distance_parts(row['distance_km'])
    html(f'<div class="sign-top"><span class="sign-badge{" venue" if is_venue(row) else ""}">{number} · {label}</span>'
         f'<span class="sign-kind">{escape(kind_label(row))}</span></div>'
         f'<div class="sign-distance">{value}<small>{unit}</small></div>'
         f'<h2 class="facility-title">{escape(display_title(row))}</h2>')
    if is_venue(row):
        html(f'<p class="unknown-note">{NOTE.get(row["venue_category"], DEFAULT_NOTE)} Belum dicek oleh Lokito.</p>')
        return
    html(context_copy(row))
    chips = known_details(row)
    if chips:
        html('<div class="chips">' + ''.join(f'<span class="chip">{escape(value)}</span>' for _, value, _ in chips[:3]) + '</div>')


def nearby_content(row):
    details = known_details(row)
    fact = kind_label(row) if is_venue(row) or not details else details[0][1]
    html(f'<div class="small-card"><span class="small-number{" venue" if is_venue(row) else ""}">{int(row["result_number"])}</span>'
         f'<div class="small-card-info"><h3>{escape(display_title(row))}</h3>'
         f'<p>{distance_label(row["distance_km"])} · {escape(fact)}</p></div></div>')


def details_content(row):
    html(f'<h2 class="facility-title">{escape(display_title(row))}</h2>'
         f'<div class="distance-line"><strong>{distance_label(row["distance_km"])}</strong> jarak garis lurus · {escape(kind_label(row))}</div>')
    if is_venue(row):
        html(f'<div class="detail-message">{NOTE.get(row["venue_category"], DEFAULT_NOTE)} '
             'Lokito belum mengecek lokasinya, jadi tanyakan ke petugas setibanya di sana.</div>')
        return
    details = known_details(row)
    for field, label in [('address', 'Alamat'), ('operator', 'Pengelola'), ('changing_table', 'Tempat ganti popok'),
                         ('religion', 'Agama'), ('denomination', 'Denominasi'), ('wheelchair:description', 'Catatan kursi roda')]:
        value = row.get(field, 'unknown')
        if value and value != 'unknown':
            if field == 'changing_table':
                value = {'yes':'Tersedia', 'no':'Tidak tersedia'}.get(value, value)
            details.append((label, str(value), field))
    if details:
        html('<dl class="detail-list">' + ''.join(f'<div><dt>{escape(label)}</dt><dd>{escape(value)}</dd></div>' for label, value, _ in details) + '</dl>')
    missing = unknown_summary(row)
    if missing:
        html(f'<div class="detail-message">{escape(missing)}</div>')
    st.caption('Info di atas belum dicek oleh Lokito. Ketersediaan dan kebersihan saat ini belum dikonfirmasi.')
    if row.get('coordinate_method') == 'OSM bounding-box center':
        st.caption('Titik menandai area fasilitas. Pintu masuknya bisa di tempat lain.')
    if row['facility_category'] == 'place_of_worship':
        st.caption('Aturan masuk berbeda-beda. Tidak semua tempat ibadah punya ruang salat umum.')
    elif row['facility_category'] == 'drinking_water':
        st.caption('Ini titik air minum yang terpetakan, bukan hasil cek kualitas air terbaru.')
