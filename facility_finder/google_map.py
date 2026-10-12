"""Google Maps handoff and optional Embed API. Never reuse the server Places key."""
import os
from html import escape
from urllib.parse import urlencode

import streamlit as st
import streamlit.components.v1 as components

from facility_finder.data import valid_coordinates


def coordinate_query(point):
    if len(point) != 2 or not valid_coordinates(*point):
        raise ValueError('Invalid map coordinates')
    return f'{float(point[0]):.7f},{float(point[1]):.7f}'


def map_url(point):
    return 'https://www.google.com/maps/search/?' + urlencode({'api': '1', 'query': coordinate_query(point)})


def embed_url(point, key):
    return 'https://www.google.com/maps/embed/v1/place?' + urlencode({
        'key': key, 'q': coordinate_query(point), 'zoom': 16})


def render_map(point, title, kind):
    st.markdown(f'<div class="google-map-heading"><span>{escape(kind)}</span><h3>{escape(title)}</h3></div>', unsafe_allow_html=True)
    # Embed keys are public browser credentials, restricted to the deployment's
    # website origins and Maps Embed API. Server-side Places credentials stay private.
    key = os.environ.get('GOOGLE_MAPS_EMBED_API_KEY', '').strip()
    if key:
        src = escape(embed_url(point, key), quote=True)
        components.html(
            '<style>html,body{height:100%;margin:0}iframe{width:100%;height:100%;border:0}</style>'
            f'<iframe title="Google Maps: {escape(title, quote=True)}" loading="lazy" '
            f'referrerpolicy="strict-origin-when-cross-origin" allowfullscreen src="{src}"></iframe>',
            height=440, scrolling=False)
    else:
        st.markdown('<div class="map-handoff"><span aria-hidden="true">↗</span>'
                    '<p>Explore this location in Google Maps.</p>'
                    '<small>The link opens the selected coordinates on your phone or browser.</small></div>',
                    unsafe_allow_html=True)
    st.link_button('Buka di Google Maps ↗', map_url(point), type='primary', use_container_width=True)
    st.caption(f'Location: {coordinate_query(point)} · The mapped point may differ from the entrance.')
