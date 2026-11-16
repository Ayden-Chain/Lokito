"""Lokito — toilet-first discovery. Run: streamlit run app.py"""
import hashlib
import json
from html import escape
import sqlite3
import pandas as pd
from streamlit_folium import st_folium
import streamlit as st

from facility_finder import community
from facility_finder.data import PROCESSED, filter_facilities, load_facilities, rank_nearest, valid_coordinates
from facility_finder.google_map import map_url
from facility_finder.maps import build_map, legend_html
from facility_finder.community_ui import render_report_preview
from facility_finder.presentation import directions_url, selected_facility, marker_selection, map_view_for_selection, new_click, PLURALS
from facility_finder.ui import ROOT, brand, details_content, featured_content, html, nearby_content
from facility_finder.venue_ui import display_title
from facility_finder.presentation import distance_label
from facility_finder.enrichment import load_cache, CACHE
from facility_finder.venue_ui import render_photo, render_details, context_for
from facility_finder.media import valid_photo
from facility_finder.proxies import venue_rows, mosque_rows, tagged_rows, osm_id, is_venue
from facility_finder.toilet_places import OUTPUT as TOILET_PLACES
from facility_finder.locate import locate_button

st.set_page_config(page_title='Lokito · Cari toilet terdekat', page_icon=str(ROOT / 'assets/lokito-mark.svg'), layout='wide')
html('<style>' + (ROOT / 'assets/lokito.css').read_text() + '</style>')

PRESETS = {'Bundaran HI': (-6.1950, 106.8230), 'Monas': (-6.1754, 106.8272),
           'Kota Tua': (-6.1352, 106.8133), 'Blok M': (-6.2444, 106.7990)}
PICK = 'Pilih di peta'
GPS = 'Lokasiku'
MAP_POINT = 'Titik di peta'
CATEGORIES = {'Toilets': 'toilets', 'Prayer spaces': 'place_of_worship', 'Drinking water': 'drinking_water'}
CATEGORY_COPY = {'Toilets': 'Toilet', 'Prayer spaces': 'Tempat ibadah', 'Drinking water': 'Air minum'}
ANY_DISTANCE = 'Semua jarak'
DEFAULTS = {'view': 'discover', 'category': 'Toilets', 'location': 'Bundaran HI', 'origin': PRESETS['Bundaran HI'],
            'wheelchair': False, 'free': False, 'public': False, 'radius': '5 km', 'search': '',
            'religion': 'Any', 'selected_id': None, 'shown': 5, 'map_view': None, 'detail_id': None,
            'pick_on_map': False, 'map_nonce': 0, 'last_map_click': None,
            'custom_lat': PRESETS['Bundaran HI'][0], 'custom_lon': PRESETS['Bundaran HI'][1]}
for key, value in DEFAULTS.items():
    st.session_state.setdefault(key, value)


@st.cache_data(show_spinner=False)
def read_cache(modified):
    return load_facilities(), json.loads((PROCESSED / 'quality.json').read_text())


try:
    modified = tuple((PROCESSED / file).stat().st_mtime_ns for file in ('facilities.json', 'quality.json'))
    facilities, quality = read_cache(modified)
except (OSError, ValueError, KeyError) as exc:
    brand()
    st.error('Data fasilitas belum bisa dimuat. Coba lagi sebentar lagi.')
    with st.expander('Bantuan setup'):
        st.write(str(exc))
        st.code('python -m facility_finder.ingest')
    st.stop()


@st.cache_data(show_spinner=False)
def read_enrichment(modified):
    return load_cache()


@st.cache_data(show_spinner=False)
def search_rows(modified, enrichment_modified, toilet_places_modified):
    """Mapped facilities plus likely-toilet venues, built once per data change."""
    records = read_enrichment(enrichment_modified)['records']
    mapped = read_cache(modified)[0].copy()
    mapped['venue_context'] = mapped.facility_id.map(records)
    mapped['kind'] = 'facility'
    # A venue that already holds a mapped toilet is shown through that toilet only.
    toilet_ids = set(mapped.loc[mapped.facility_category == 'toilets', 'facility_id'])
    skip = {context['venue_id'] for facility_id, context in records.items()
            if facility_id in toilet_ids and context.get('relationship_type') in ('inside', 'at')}
    # A place OSM records as having a toilet replaces its "usually has a toilet" duplicate.
    venues = read_enrichment(enrichment_modified).get('venues', {})
    tagged = tagged_rows(catalog=venues)
    skip |= {osm_id(fid) for fid in tagged.get('facility_id', [])}
    combined = pd.concat([mapped, tagged, venue_rows(venues, skip),
                          mosque_rows(mapped, skip)], ignore_index=True)
    combined['kind'] = combined['kind'].fillna('facility')
    return mapped, combined


enrichment_modified = CACHE.stat().st_mtime_ns if CACHE.exists() else None
enrichment = read_enrichment(enrichment_modified)
# mapped_facilities is the OSM source data; facilities adds likely-toilet venues for search only.
toilet_places_modified = TOILET_PLACES.stat().st_mtime_ns if TOILET_PLACES.exists() else None
mapped_facilities, facilities = search_rows(modified, enrichment_modified, toilet_places_modified)
reportable_ids = set(mapped_facilities.facility_id)


def change_view(view):
    if view == 'feedback' and st.session_state.view != 'feedback':
        st.session_state.feedback_context = dict(st.session_state.get('discovery_context', {}))
    st.session_state.view = view
    st.session_state.detail_id = None


def change_category(category):
    st.session_state.category = category
    st.session_state.religion = 'Any'
    st.session_state.other_menu = False


def choose_facility(fid):
    st.session_state.selected_id = fid
    st.session_state.map_view = None


def set_origin(point, location):
    st.session_state.update(origin=point, location=location, pick_on_map=False)


def apply_location():
    set_origin(PRESETS[st.session_state.location_choice], st.session_state.location_choice)
    st.session_state.location_menu = False


def apply_coordinates():
    set_origin((st.session_state.custom_lat, st.session_state.custom_lon), MAP_POINT)
    st.session_state.location_menu = False


def start_picking():
    st.session_state.pick_on_map = True
    st.session_state.location_menu = False


def cancel_picking():
    st.session_state.pick_on_map = False


def recenter_map():
    st.session_state.map_view = None
    st.session_state.map_nonce += 1


def apply_preferences():
    for setting in ('wheelchair', 'free', 'public', 'radius', 'search', 'religion'):
        key = f'pref_{setting}'
        if key in st.session_state:
            st.session_state[setting] = st.session_state[key]
    st.session_state.preferences_menu = False


def reset_preferences():
    for setting in ('wheelchair', 'free', 'public', 'search', 'religion'):
        st.session_state[setting] = DEFAULTS[setting]
        st.session_state[f'pref_{setting}'] = DEFAULTS[setting]


def clear_preferences():
    reset_preferences()
    st.session_state.preferences_menu = False


def widen_search():
    st.session_state.radius = ANY_DISTANCE
    st.session_state.pref_radius = ANY_DISTANCE


def save_observation(fid, availability='unknown', cleanliness=None, issue=''):
    try:
        community.add_report(fid, reportable_ids, availability, cleanliness, issue)
        st.success('Terima kasih. Laporanmu tersimpan di server Lokito dan menunggu ditinjau.')
    except (ValueError, OSError, sqlite3.Error) as exc:
        st.error(f'Laporanmu belum bisa disimpan: {exc}')


def close_details():
    st.session_state.detail_id = None


@st.dialog('Detail', width='small', on_dismiss=close_details)
def show_details(row):
    details_content(row)
    st.link_button('Arahkan ↗', directions_url(row, st.session_state.origin), type='primary', use_container_width=True)
    st.link_button('Buka di Google Maps ↗', map_url((row['latitude'], row['longitude'])))
    if is_venue(row):
        render_photo(row)
        return
    report_preview = st.container()
    render_details(row)
    from facility_finder.google_places import configured, load_ids, policy_urls
    context = context_for(row)
    if context and configured() and policy_urls() and context['venue_id'] in load_ids():
        if st.button('Foto lain · Google Maps'):
            st.session_state.google_context = context
            change_view('google_photos')
            st.rerun(scope='app')
    st.divider()
    st.write('**Baru ke sini? Apakah infonya akurat?**')
    st.caption('Laporan tersimpan di server Lokito dan bisa dilihat pengunjung lain. Laporan tidak membuat lencana terverifikasi.')
    if st.button('Ya, infonya akurat', key=f'accurate_{row["facility_id"]}'):
        save_observation(row['facility_id'], issue='Visitor confirmed the displayed details were accurate. Availability was not separately assessed.')
    with st.expander('Laporkan perubahan'):
        with st.form(f'report_{row["facility_id"]}', clear_on_submit=True):
            available = st.selectbox('Apakah toiletnya bisa dipakai?', ['Belum dicek', 'Ya', 'Tidak'])
            cleanliness = st.selectbox('Kebersihan · opsional', ['Tidak dinilai', 1, 2, 3, 4, 5], help='1 = sangat buruk; 5 = sangat bersih')
            issue = st.text_area('Apa yang perlu diketahui orang lain?', max_chars=1000, help='Jangan tulis data pribadi.')
            submitted = st.form_submit_button('Simpan laporan')
        if submitted:
            if available == 'Belum dicek' and cleanliness == 'Tidak dinilai' and not issue.strip():
                st.warning('Isi laporan dulu sebelum menyimpan.')
            else:
                save_observation(row['facility_id'], {'Belum dicek':'unknown', 'Ya':'yes', 'Tidak':'no'}[available],
                                 None if cleanliness == 'Tidak dinilai' else cleanliness, issue)
    with report_preview:
        render_report_preview(row['facility_id'])


with st.container(key='header'):
    logo, trust, about = st.columns([8, 1, 1])
    with logo:
        brand()
    trust.button('Data', on_click=change_view, args=('trust',), use_container_width=True)
    about.button('Tentang', on_click=change_view, args=('about',), use_container_width=True)

if st.session_state.view == 'discover':
    category = CATEGORIES[st.session_state.category]
    place = {GPS: 'lokasimu', MAP_POINT: 'titik pilihanmu'}.get(st.session_state.location, st.session_state.location)
    # The headline and tagline stay in English on purpose: they are the brand line.
    heading = {'toilets': 'Find a toilet <span class="accent">nearby.</span>',
               'place_of_worship': 'A place to pray, <span class="accent">nearby.</span>',
               'drinking_water': 'Find drinking water <span class="accent">nearby.</span>'}[category]
    html(f'<div class="hero"><h1>{heading}</h1><p>A quick stop. A little less guesswork.</p></div>')
    with st.container(key='results-layout'):
        results_col, map_col = st.columns([1, 1.55], gap='large')
    with results_col:
        with st.container(key='toolbar'):
            location_col, prefs_col, other_col = st.columns([2.5, 1.15, 1.2])
            with location_col:
                with st.container(key='locate'):
                    position = locate_button()
                if position and valid_coordinates(*position):
                    set_origin(position, GPS)
                    st.rerun()
                with st.popover(f'Mulai dari {place}', icon=':material/location_on:', key='location_menu', on_change='rerun', use_container_width=True):
                    st.write('**Mulai dari mana?**')
                    options = [*PRESETS, PICK]
                    current = st.session_state.location if st.session_state.location in PRESETS else PICK
                    # Choice is outside the form so the map option appears immediately.
                    choice = st.selectbox('Titik awal', options, index=options.index(current), key='location_choice')
                    with st.form('location_form'):
                        if choice == PICK:
                            st.caption('Tekan tombol di bawah, lalu ketuk lokasimu di peta.')
                            st.form_submit_button('Ketuk di peta', type='primary', on_click=start_picking, use_container_width=True)
                            with st.expander('Atau masukkan koordinat'):
                                st.number_input('Latitude', min_value=-90.0, max_value=90.0, format='%.6f', key='custom_lat')
                                st.number_input('Longitude', min_value=-180.0, max_value=180.0, format='%.6f', key='custom_lon')
                                st.form_submit_button('Pakai koordinat ini', on_click=apply_coordinates, use_container_width=True)
                        else:
                            st.form_submit_button('Gunakan lokasi ini', type='primary', on_click=apply_location, use_container_width=True)
            with prefs_col:
                active = sum(bool(st.session_state[k]) for k in ('wheelchair','free','public','search')) + (st.session_state.religion != 'Any')
                with st.popover('Preferensi' + (f' · {active}' if active else ''), icon=':material/tune:', key='preferences_menu', on_change='rerun', use_container_width=True):
                    st.write('**Sesuaikan kebutuhanmu**')
                    with st.form('preferences_form'):
                        st.checkbox('Ramah kursi roda', value=st.session_state.wheelchair, key='pref_wheelchair')
                        st.checkbox('Gratis', value=st.session_state.free, key='pref_free')
                        st.checkbox('Terbuka untuk umum', value=st.session_state.public, key='pref_public')
                        st.caption('Hanya tempat yang mencantumkan info ini yang ditampilkan, jadi tempat tanpa info itu tidak ikut. Info belum dicek oleh Lokito.')
                        radii = ['1 km', '3 km', '5 km', '10 km', ANY_DISTANCE]
                        st.selectbox('Jarak maksimal', radii, index=radii.index(st.session_state.radius), key='pref_radius')
                        st.text_input('Nama atau jalan', value=st.session_state.search, key='pref_search', placeholder='Nama tempat atau jalan')
                        if category == 'place_of_worship':
                            religions = ['Any'] + sorted(facilities.loc[facilities.facility_category == category, 'religion'].unique())
                            st.selectbox('Agama', religions, index=religions.index(st.session_state.religion), key='pref_religion',
                                         format_func=lambda value: 'Semua' if value == 'Any' else value)
                        st.form_submit_button('Terapkan', type='primary', on_click=apply_preferences, use_container_width=True)
                    st.button('Hapus preferensi', on_click=clear_preferences)
            with other_col:
                with st.popover('Fasilitas lain' if category == 'toilets' else CATEGORY_COPY[st.session_state.category], key='other_menu', on_change='rerun', use_container_width=True):
                    st.caption('Cari yang lain?')
                    for label in CATEGORIES:
                        st.button(CATEGORY_COPY[label], key=f'category_{label}', on_click=change_category, args=(label,), use_container_width=True)
    origin = st.session_state.origin
    if not (-6.5 < origin[0] < -5.0 and 106.3 < origin[1] < 107.1):
        st.warning('Titik awalmu di luar Jakarta. Saat ini Lokito baru mencakup Jakarta.')
    query = (category, origin, *(st.session_state[k] for k in ('wheelchair','free','public','radius','search','religion')))
    signature = hashlib.sha256(repr(query).encode()).hexdigest()[:12]
    if st.session_state.get('query_signature') != signature:
        st.session_state.update(query_signature=signature, selected_id=None, shown=5, map_view=None, detail_id=None, last_map_click=None)
    subset = filter_facilities(facilities, [category], st.session_state.wheelchair, st.session_state.free,
                               st.session_state.public, '',
                               None if st.session_state.religion == 'Any' or category != 'place_of_worship' else st.session_state.religion)
    if st.session_state.search.strip():
        search = st.session_state.search.strip()
        venue_names = subset.venue_context.map(lambda c: c['venue_name'] if isinstance(c,dict) else '')
        subset = subset[subset.name.str.contains(search,case=False,regex=False) |
                        subset.address.str.contains(search,case=False,regex=False) |
                        venue_names.str.contains(search,case=False,regex=False)]
    ranked = rank_nearest(subset, *origin)
    if st.session_state.radius != ANY_DISTANCE:
        ranked = ranked[ranked.distance_km <= float(st.session_state.radius.split()[0])].reset_index(drop=True)
    ranked['result_number'] = range(1, len(ranked) + 1)
    row = selected_facility(ranked, st.session_state.selected_id)
    st.session_state.selected_id = row['facility_id'] if row else None
    context = context_for(row) if row else None
    st.session_state.discovery_context = {'facility_id':row['facility_id'] if row and not is_venue(row) else None,
        'category':category,'starting_preset':st.session_state.location if st.session_state.location in PRESETS else None,
        'venue_shown':bool(context),'photo_shown':bool(context and valid_photo(context.get('photo')))}
    radius_copy = 'di seluruh Jakarta' if st.session_state.radius == ANY_DISTANCE else f'dalam {st.session_state.radius}'
    venue_count = int((ranked.kind == 'venue').sum())
    count = lambda n: f'{n:,}'.replace(',', '.')  # Indonesian thousands separator: 1.049
    breakdown = (f'{count(len(ranked) - venue_count)} toilet terpetakan dan {count(venue_count)} tempat lain (minimarket, SPBU, mall, masjid, MRT)'
                 if category == 'toilets' else 'Diurutkan dari yang terdekat, jarak garis lurus')
    with results_col:
        with st.container(key='results-pane'):
            html(f'<div class="results-heading"><h2>{count(len(ranked))} {"pilihan" if category == "toilets" else PLURALS[category]} {radius_copy}</h2><span>{breakdown}</span></div>')
            if row:
                with st.container(key='featured'):
                    featured_content(row, row['result_number'] == 1)
                    with st.container(key='feature-actions'):
                        html(f'<div class="bar-summary"><b>{escape(display_title(row))}</b><span>{distance_label(row["distance_km"])}</span></div>')
                        directions, details = st.columns([1.25, 1])
                        directions.link_button('Arahkan ↗', directions_url(row, origin), type='primary', use_container_width=True)
                        if details.button('Detail', use_container_width=True):
                            st.session_state.detail_id = row['facility_id']
                    if not is_venue(row):
                        render_report_preview(row['facility_id'], quiet=True)
                    render_photo(row)
                if row['result_number'] != 1:
                    st.button('Kembali ke yang terdekat', on_click=choose_facility, args=(ranked.iloc[0].facility_id,))
                others = ranked[ranked.facility_id != row['facility_id']]
                if not others.empty:
                    html('<div class="other-heading">Pilihan lain di sekitar</div>')
                for other in others.head(st.session_state.shown).to_dict('records'):
                    with st.container(key=f'nearby-card-{other["result_number"]}'):
                        nearby_content(other)
                        st.button(f'Pilih nomor {other["result_number"]} →', key=f'choose_{other["facility_id"]}',
                                  on_click=choose_facility, args=(other['facility_id'],))
                if len(others) > st.session_state.shown:
                    if st.button('Tampilkan lebih banyak', use_container_width=True):
                        st.session_state.shown += 5
                        st.rerun()
                elif others.empty:
                    st.caption('Hanya ini pilihan yang terpetakan di area ini.')
            else:
                html('<div class="empty-state"><h2>Belum ada yang cocok.</h2><p>Coba perluas jarak atau kurangi preferensi. Mungkin ada tempat yang belum kami petakan.</p></div>')
                st.button('Hapus preferensi', key='empty_clear', on_click=clear_preferences, use_container_width=True)
                st.button('Cari di seluruh Jakarta', on_click=widen_search, use_container_width=True)
    with map_col:
        with st.container(key='map-pane'):
            picking = st.session_state.pick_on_map
            if picking:
                with st.container(key='pick-banner'):
                    st.info('Ketuk peta untuk memilih titik awalmu.', icon=':material/touch_app:')
                    st.button('Batal', on_click=cancel_picking)
            visible = ranked.head(60)
            if row and row['facility_id'] not in set(visible.facility_id):
                visible = pd.concat([visible.head(59), ranked[ranked.facility_id == row['facility_id']]])
            viewport = st.session_state.map_view or map_view_for_selection(origin, row)
            # The key changes only for a new search, an explicit recenter or pick mode,
            # so choosing a pin redraws markers without rebuilding the whole map.
            returned = ['last_object_clicked', 'last_object_clicked_popup', 'last_object_clicked_tooltip']
            event = st_folium(build_map(visible, origin, st.session_state.selected_id), height=610,
                use_container_width=True, key=f'map_{signature}_{st.session_state.map_nonce}_{"pick" if picking else "view"}',
                center=viewport['center'], zoom=viewport['zoom'],
                returned_objects=returned + (['last_clicked'] if picking else [])) or {}
            point = event.get('last_clicked') if picking else None
            if point and valid_coordinates(point.get('lat'), point.get('lng')):
                set_origin((float(point['lat']), float(point['lng'])), MAP_POINT)
                st.toast('Titik awal diperbarui', icon=':material/location_on:')
                st.rerun()
            stamp = new_click(event, st.session_state.last_map_click)
            if stamp:
                st.session_state.last_map_click = stamp
                clicked = marker_selection(event, visible)
                if clicked and clicked != st.session_state.selected_id:
                    st.session_state.selected_id = clicked
                    st.session_state.map_view = None
                    st.rerun()
            html(legend_html(category))
            st.button('Pusatkan peta', icon=':material/my_location:', on_click=recenter_map)
            st.caption('Pin menunjukkan lokasi terpetakan, bukan pintu masuk atau ketersediaan saat ini.')
            if len(ranked) > 60:
                st.caption('Peta menampilkan 60 pilihan terdekat, termasuk pilihanmu.')
            if category == 'place_of_worship':
                st.caption('Mencakup berbagai agama. Ruang salat umum dan akses masuk tidak dijamin.')

elif st.session_state.view == 'trust':
    from facility_finder.evidence import render_trust
    st.button('← Kembali', on_click=change_view, args=('discover',))
    render_trust(mapped_facilities, quality, st.session_state.selected_id, enrichment)
    from facility_finder.feedback_ui import render_owner
    render_owner()
elif st.session_state.view == 'feedback':
    from facility_finder.feedback_ui import render_form
    st.button('← Kembali', on_click=change_view, args=('discover',))
    with st.container(key='feedback-content'):
        render_form(st.session_state.get('feedback_context',{}),reportable_ids)
elif st.session_state.view == 'google_photos':
    from facility_finder.google_places import render_view
    st.button('← Kembali', on_click=change_view, args=('discover',))
    render_view(st.session_state.get('google_context'))
else:
    from facility_finder.evidence import render_about
    st.button('← Kembali', on_click=change_view, args=('discover',))
    render_about()

if st.session_state.view != 'feedback':
    with st.container(key='feedback-footer'):
        st.button('Bantu kembangkan Lokito', on_click=change_view, args=('feedback',))

if st.session_state.view == 'discover' and st.session_state.detail_id is not None:
    detail_record = selected_facility(ranked, st.session_state.detail_id)
    if detail_record:
        show_details(detail_record)

html('<footer class="footer"><span><b>lokito</b> · Proyek mata kuliah Venture Creation</span>'
     '<span>Pilot Jakarta · <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">© OpenStreetMap contributors</a></span></footer>')
