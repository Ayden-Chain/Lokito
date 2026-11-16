"""Source-backed venue context and attributed media with no API calls."""
from html import escape

import streamlit as st

from facility_finder.enrichment import LABELS as SOURCE_LABELS
from facility_finder.media import valid_photo
from facility_finder.google_map import map_url
from facility_finder.presentation import facility_name, known, distance_label, directions_url


LABELS={'mall':'Mall','fuel':'SPBU','station':'Stasiun','park':'Taman','market':'Pasar','hospital':'Rumah sakit',
        'university':'Kampus','attraction':'Tempat wisata','public_building':'Gedung publik'}
RELATION={'inside':'di dalam','at':'di','near':'dekat'}
assert set(LABELS)==set(SOURCE_LABELS)


def relationship_label(context):
    words=RELATION.get(context['relationship_type'],context['relationship_type'])
    return f"{words[0].upper()+words[1:]} {context['venue_name']}"


def context_for(row):
    value=row.get('venue_context')
    return value if isinstance(value,dict) else None


def display_title(row):
    context=context_for(row)
    if context and not known(row.get('name')):
        return f"{facility_name(row)} {RELATION.get(context['relationship_type'],context['relationship_type'])} {context['venue_name']}"
    return facility_name(row)


def context_copy(row, detail=False):
    context=context_for(row)
    if not context: return ''
    subtitle=LABELS[context['venue_category']]
    if context['relationship_type']=='near':
        subtitle+=f" · sekitar {round(context['distance_metres']/10)*10:.0f} m dari titik toilet"
    title=relationship_label(context)
    generated=not known(row.get('name'))
    return (f'<div class="venue-context"><span class="venue-kicker">Lokasi</span>'
            f'<p>{escape(subtitle if generated and not detail else title)}</p>'
            + (f'<small>{escape(subtitle)}</small>' if detail or not generated else '')
            + ('<small>Label lokasi oleh Lokito</small>' if generated else '')+'</div>')


def photo_html(photo):
    if not valid_photo(photo): return ''
    # A CSS background falls back cleanly if the remote image fails, without
    # broken-image icons or injecting event-handler JavaScript into Streamlit.
    url=photo['thumbnail_url'].replace('"','%22').replace("'",'%27').replace('(','%28').replace(')','%29')
    return (f'<figure class="venue-photo"><div class="venue-photo-frame" role="img" aria-label="{escape(photo["alt"],quote=True)}" '
            f'style="background-image:url(&quot;{escape(url,quote=True)}&quot;)"></div>'
            '<figcaption><span>Foto tempat · bukan foto toiletnya</span>'
            f'<a href="{escape(photo["page_url"],quote=True)}" target="_blank" rel="noopener noreferrer">Foto: {escape(photo["author"])} · Wikimedia Commons</a>'
            f'<a href="{escape(photo["licence_url"],quote=True)}" target="_blank" rel="noopener noreferrer">{escape(photo["licence"])} · dipotong agar pas</a>'
            '<small>Jika foto tidak muncul, buka sumber foto di atas.</small></figcaption></figure>')


def render_photo(row):
    # Likely-toilet venues carry their own photo; mapped toilets borrow their venue's.
    context=context_for(row)
    photo=row.get('photo') if row.get('kind')=='venue' else (context or {}).get('photo')
    markup=photo_html(photo)
    if markup: st.markdown(markup,unsafe_allow_html=True)


def render_details(row):
    context=context_for(row)
    st.subheader('Lokasi')
    if not context:
        st.caption('Belum ada keterangan lokasi yang dapat diandalkan untuk toilet ini.')
        return
    st.markdown(context_copy(row,detail=True),unsafe_allow_html=True)
    if context['relationship_type']=='near':
        st.caption('Tempat ini hanya patokan terdekat, bukan berarti toiletnya ada di dalamnya.')
    elif context['relationship_type']=='inside':
        st.caption('Titik toilet berada di dalam area tempat ini. Pintu masuk, lantai, dan akses umum belum dicek.')
    else:
        st.caption('Sumber data menyebut tempat ini. Akses dan ketersediaan saat ini belum dicek.')
    st.caption('Sumber data: OpenStreetMap')
    render_photo(row)


def render_nearby_venue(place, origin):
    """A venue landmark card, clearly separate from mapped-toilet results."""
    st.markdown(nearby_venue_html(place, origin), unsafe_allow_html=True)


def nearby_venue_html(place, origin):
    """Build a venue card without making a toilet availability claim."""
    category=LABELS[place['venue_category']]
    context={'photo':place.get('photo')}
    photo=photo_html(context.get('photo'))
    target={'latitude':place['latitude'],'longitude':place['longitude']}
    direction=directions_url(target,origin)
    return (
        '<article class="nearby-venue">'
        f'<div class="nearby-venue-title">{escape(place["venue_name"])}</div>'
        f'<div class="nearby-venue-meta">{escape(category)} · {distance_label(place["distance_km"])}</div>'
        f'<p>{venue_notice(place)}</p>'
        f'<a class="nearby-venue-map" href="{escape(map_url((place["latitude"],place["longitude"])),quote=True)}" target="_blank" rel="noopener noreferrer">Buka di Google Maps ↗</a>'
        f'<a class="nearby-venue-directions" href="{escape(direction,quote=True)}" target="_blank" rel="noopener noreferrer">Arahkan ↗</a>'
        '<p class="nearby-venue-source">Sumber data: OpenStreetMap</p>'
        f'{photo}</article>')


def venue_notice(place):
    if place.get('toilet_linked'):
        return 'Ada toilet terpetakan di tempat ini. Akses dan ketersediaan saat ini belum dicek.'
    return 'Biasanya ada toilet di tempat seperti ini, tapi belum dicek oleh Lokito.'
