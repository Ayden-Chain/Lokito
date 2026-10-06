"""Lokito — toilet-first discovery. Run: streamlit run app.py"""
import hashlib
import json
import sqlite3
from html import escape

import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from facility_finder import community
from facility_finder.data import PROCESSED, filter_facilities, load_facilities, rank_nearest
from facility_finder.maps import build_map
from facility_finder.presentation import (directions_url, facility_name, marker_selection, map_view_for_selection,
                                         selected_facility, PLURALS)
from facility_finder.ui import ROOT, brand, details_content, featured_content, html, nearby_content
from facility_finder.enrichment import load_cache, CACHE
from facility_finder.venue_ui import render_photo, render_details, context_for
from facility_finder.media import valid_photo

st.set_page_config(page_title='Lokito · Find a toilet nearby', page_icon=str(ROOT / 'assets/lokito-mark.svg'), layout='wide')
html('<style>' + (ROOT / 'assets/lokito.css').read_text() + '</style>')

PRESETS = {'Bundaran HI': (-6.1950, 106.8230), 'Monas': (-6.1754, 106.8272),
           'Kota Tua': (-6.1352, 106.8133), 'Blok M': (-6.2444, 106.7990)}
CATEGORIES = {'Toilets': 'toilets', 'Prayer spaces': 'place_of_worship', 'Drinking water': 'drinking_water'}
DEFAULTS = {'view': 'discover', 'category': 'Toilets', 'location': 'Bundaran HI', 'origin': PRESETS['Bundaran HI'],
            'wheelchair': False, 'free': False, 'public': False, 'radius': '5 km', 'search': '',
            'religion': 'Any', 'selected_id': None, 'shown': 5, 'map_view': None, 'detail_id': None}
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
    st.error('We could not load nearby facilities. Please try again shortly.')
    with st.expander('Setup help'):
        st.write(str(exc))
        st.code('python -m facility_finder.ingest')
    st.stop()


@st.cache_data(show_spinner=False)
def read_enrichment(modified):
    return load_cache()


enrichment = read_enrichment(CACHE.stat().st_mtime_ns if CACHE.exists() else None)
facilities = facilities.copy()
facilities['venue_context'] = facilities.facility_id.map(enrichment['records'])


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


def apply_location():
    choice = st.session_state.location_choice
    st.session_state.location = choice
    st.session_state.origin = (st.session_state.custom_lat, st.session_state.custom_lon) if choice == 'Custom point' else PRESETS[choice]
    st.session_state.location_menu = False


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
    st.session_state.radius = 'Any distance'
    st.session_state.pref_radius = 'Any distance'


def save_observation(fid, availability='unknown', cleanliness=None, issue=''):
    try:
        community.add_report(fid, set(facilities.facility_id), availability, cleanliness, issue)
        st.success('Thank you. Your observation is saved on this device, awaiting review.')
    except (ValueError, OSError, sqlite3.Error) as exc:
        st.error(f'Your observation could not be saved: {exc}')


def close_details():
    st.session_state.detail_id = None


@st.dialog('Facility details', width='small', on_dismiss=close_details)
def show_details(row):
    details_content(row)
    st.link_button('Open directions ↗', directions_url(row, st.session_state.origin), type='primary', use_container_width=True)
    st.caption('Opens Google Maps. Route and travel time are provided there.')
    render_details(row)
    from facility_finder.google_places import configured, load_ids, policy_urls
    context = context_for(row)
    if context and configured() and policy_urls() and context['venue_id'] in load_ids():
        if st.button('More venue photos · Google Maps'):
            st.session_state.google_context = context
            change_view('google_photos')
            st.rerun(scope='app')
    st.divider()
    st.write('**Visited recently? Were these details accurate?**')
    st.caption('Observations stay on this device until reviewed. They do not create a verified badge.')
    if st.button('Yes, details were accurate', key=f'accurate_{row["facility_id"]}'):
        save_observation(row['facility_id'], issue='Visitor confirmed the displayed details were accurate. Availability was not separately assessed.')
    with st.expander('Report a change'):
        with st.form(f'report_{row["facility_id"]}', clear_on_submit=True):
            available = st.selectbox('Could you use the facility?', ['Not checked', 'Yes', 'No'])
            cleanliness = st.selectbox('Cleanliness · optional', ['Not assessed', 1, 2, 3, 4, 5], help='1 = very poor; 5 = very clean')
            issue = st.text_area('What should others know?', max_chars=1000, help='Please leave out personal information.')
            submitted = st.form_submit_button('Save observation')
        if submitted:
            if available == 'Not checked' and cleanliness == 'Not assessed' and not issue.strip():
                st.warning('Add an observation before saving.')
            else:
                save_observation(row['facility_id'], {'Not checked':'unknown', 'Yes':'yes', 'No':'no'}[available],
                                 None if cleanliness == 'Not assessed' else cleanliness, issue)
    try:
        reports = community.list_reports(row['facility_id'])
        if reports:
            with st.expander(f'Visitor observations ({len(reports)}) · unreviewed'):
                for report in reports:
                    html(f'<div class="report-note"><small>{escape(report["submitted_at"][:10])} · Awaiting review</small>'
                         f'<p>{escape(report["issue"] or "No written note.")}</p>'
                         f'<small>Availability reported: {escape(report["available"])} · Cleanliness: {report["cleanliness"] if report["cleanliness"] is not None else "Not assessed"}</small></div>')
    except (OSError, sqlite3.Error) as exc:
        st.error(f'Visitor observations could not be loaded: {exc}')


with st.container(key='header'):
    logo, trust, about = st.columns([7, 1.6, 1])
    with logo:
        brand()
    trust.button('Data & trust', on_click=change_view, args=('trust',), use_container_width=True)
    about.button('About', on_click=change_view, args=('about',), use_container_width=True)

if st.session_state.view == 'discover':
    category = CATEGORIES[st.session_state.category]
    heading = {'toilets':'Find a toilet <span class="accent">nearby.</span>',
               'place_of_worship':'A place to pray, <span class="accent">nearby.</span>',
               'drinking_water':'Find drinking water <span class="accent">nearby.</span>'}[category]
    html(f'<div class="hero"><h1>{heading}</h1><p>A quick stop. A little less guesswork.</p></div>')
    with st.container(key='toolbar'):
        location_col, prefs_col, other_col = st.columns([2.5, 1.15, 1.2])
        with location_col:
            with st.popover(f'Starting near {st.session_state.location}', icon=':material/location_on:', key='location_menu', on_change='rerun', use_container_width=True):
                st.write('**Where are you starting?**')
                # Choice is outside the form so custom fields appear immediately.
                choice = st.selectbox('Starting point', [*PRESETS, 'Custom point'],
                                      index=[*PRESETS, 'Custom point'].index(st.session_state.location), key='location_choice')
                with st.form('location_form'):
                    if choice == 'Custom point':
                        st.caption('Use an approximate location. Map tiles load from OpenStreetMap; directions open in Google Maps.')
                        st.number_input('Latitude', min_value=-90.0, max_value=90.0, value=float(st.session_state.origin[0]), format='%.6f', key='custom_lat')
                        st.number_input('Longitude', min_value=-180.0, max_value=180.0, value=float(st.session_state.origin[1]), format='%.6f', key='custom_lon')
                    st.form_submit_button('Use this location', type='primary', on_click=apply_location, use_container_width=True)
        with prefs_col:
            active = sum(bool(st.session_state[k]) for k in ('wheelchair','free','public','search')) + (st.session_state.religion != 'Any')
            with st.popover('Preferences' + (f' · {active}' if active else ''), icon=':material/tune:', key='preferences_menu', on_change='rerun', use_container_width=True):
                st.write('**Make it work for you**')
                with st.form('preferences_form'):
                    st.checkbox('Wheelchair accessible', value=st.session_state.wheelchair, key='pref_wheelchair')
                    st.checkbox('Free to use', value=st.session_state.free, key='pref_free')
                    st.checkbox('Open to the public', value=st.session_state.public, key='pref_public')
                    st.caption('Only places with this information listed are included. Details have not been checked by Lokito.')
                    radii = ['1 km', '3 km', '5 km', '10 km', 'Any distance']
                    st.selectbox('Look within', radii, index=radii.index(st.session_state.radius), key='pref_radius')
                    st.text_input('Name or street', value=st.session_state.search, key='pref_search', placeholder='Facility, venue or street')
                    if category == 'place_of_worship':
                        religions = ['Any'] + sorted(facilities.loc[facilities.facility_category == category, 'religion'].unique())
                        st.selectbox('Religion', religions, index=religions.index(st.session_state.religion), key='pref_religion')
                    st.form_submit_button('Apply preferences', type='primary', on_click=apply_preferences, use_container_width=True)
                st.button('Clear preferences', on_click=clear_preferences)
        with other_col:
            with st.popover('Other facilities' if category == 'toilets' else st.session_state.category, key='other_menu', on_change='rerun', use_container_width=True):
                st.caption('Looking for something else?')
                for label in CATEGORIES:
                    st.button(label, key=f'category_{label}', on_click=change_category, args=(label,), use_container_width=True)
    origin = st.session_state.origin
    if not (-6.5 < origin[0] < -5.0 and 106.3 < origin[1] < 107.1):
        st.warning('Your starting point is outside the Jakarta area. Lokito currently has facilities in Jakarta only.')
    query = (category, origin, *(st.session_state[k] for k in ('wheelchair','free','public','radius','search','religion')))
    signature = hashlib.sha256(repr(query).encode()).hexdigest()[:12]
    if st.session_state.get('query_signature') != signature:
        st.session_state.update(query_signature=signature, selected_id=None, shown=5, map_view=None, detail_id=None)
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
    if st.session_state.radius != 'Any distance':
        ranked = ranked[ranked.distance_km <= float(st.session_state.radius.split()[0])].reset_index(drop=True)
    ranked['result_number'] = range(1, len(ranked) + 1)
    row = selected_facility(ranked, st.session_state.selected_id)
    st.session_state.selected_id = row['facility_id'] if row else None
    context = context_for(row) if row else None
    st.session_state.discovery_context = {'facility_id':row['facility_id'] if row else None,
        'category':category,'starting_preset':st.session_state.location if st.session_state.location in PRESETS else None,
        'venue_shown':bool(context),'photo_shown':bool(context and valid_photo(context.get('photo')))}
    radius_copy = 'Jakarta' if st.session_state.radius == 'Any distance' else f'within {st.session_state.radius}'
    result_label = ({'toilets': 'toilet', 'place_of_worship': 'prayer space', 'drinking_water': 'drinking water point'}[category]
                    if len(ranked) == 1 else PLURALS[category])
    html(f'<div class="results-heading"><h2>{len(ranked):,} {result_label} {radius_copy}</h2><span>Nearest first · straight-line distances</span></div>')
    with st.container(key='results-layout'):
        results_col, map_col = st.columns([0.95, 1.55], gap='large')
        with results_col:
            with st.container(key='results-pane'):
                if row:
                    with st.container(key='featured'):
                        featured_content(row, row['result_number'] == 1)
                        with st.container(key='feature-actions'):
                            directions, details = st.columns([1.25, 1])
                            directions.link_button('Open directions ↗', directions_url(row, origin), type='primary', use_container_width=True)
                            if details.button('View details', use_container_width=True):
                                st.session_state.detail_id = row['facility_id']
                        html('<p class="directions-note">Opens Google Maps</p><div class="trust-note">Not yet checked by Lokito</div>')
                        render_photo(row)
                    if row['result_number'] != 1:
                        st.button('Back to nearest option', on_click=choose_facility, args=(ranked.iloc[0].facility_id,))
                    others = ranked[ranked.facility_id != row['facility_id']]
                    if not others.empty:
                        html(f'<div class="other-heading">Other {PLURALS[category]} nearby</div>')
                    for other in others.head(st.session_state.shown).to_dict('records'):
                        with st.container(key=f'nearby-card-{other["result_number"]}'):
                            nearby_content(other)
                            st.button(f'Show option {other["result_number"]} on map →', key=f'choose_{other["facility_id"]}',
                                      on_click=choose_facility, args=(other['facility_id'],))
                    if len(others) > st.session_state.shown:
                        if st.button('Show more nearby', use_container_width=True):
                            st.session_state.shown += 5
                            st.rerun()
                    elif others.empty:
                        st.caption('This is the only mapped match in this area.')
                else:
                    html('<div class="empty-state"><h2>No matches just yet.</h2><p>Try a wider area or fewer preferences. There may be facilities we haven’t mapped yet.</p></div>')
                    st.button('Clear preferences', key='empty_clear', on_click=clear_preferences, use_container_width=True)
                    st.button('Search all Jakarta', on_click=widen_search, use_container_width=True)
        with map_col:
            with st.container(key='map-pane'):
                visible = ranked.head(60)
                if row and row['facility_id'] not in set(visible.facility_id):
                    visible = pd.concat([visible.head(59), ranked[ranked.facility_id == row['facility_id']]])
                map_key = f'map_{signature}_{st.session_state.selected_id}'
                viewport = st.session_state.map_view or map_view_for_selection(origin, row)
                event = st_folium(build_map(visible, origin, st.session_state.selected_id), height=610,
                                  use_container_width=True, key=map_key,
                                  center=viewport.get('center'), zoom=viewport.get('zoom'),
                                  returned_objects=['last_object_clicked', 'last_object_clicked_popup',
                                                    'last_object_clicked_tooltip', 'center', 'zoom'])
                clicked = marker_selection(event, visible)
                if clicked and clicked != st.session_state.selected_id:
                    st.session_state.selected_id = clicked
                    if event.get('center') and event.get('zoom'):
                        st.session_state.map_view = {'center': (event['center']['lat'], event['center']['lng']), 'zoom': event['zoom']}
                    st.rerun()
                html('<div class="map-caption"><span class="map-start">Your starting point</span><span>Tap a numbered pin to choose a place</span></div>')
                if len(ranked) > 60:
                    st.caption('Map shows the closest 60 options, including your selection. Browse more in the list.')
                if category == 'place_of_worship':
                    st.caption('Includes different religions. Public prayer rooms and entry are not guaranteed.')

elif st.session_state.view == 'trust':
    from facility_finder.evidence import render_trust
    st.button('← Back to nearby', on_click=change_view, args=('discover',))
    render_trust(facilities, quality, st.session_state.selected_id, enrichment)
    from facility_finder.feedback_ui import render_owner
    render_owner()
elif st.session_state.view == 'feedback':
    from facility_finder.feedback_ui import render_form
    st.button('← Back to nearby', on_click=change_view, args=('discover',))
    with st.container(key='feedback-content'):
        render_form(st.session_state.get('feedback_context',{}),set(facilities.facility_id))
elif st.session_state.view == 'google_photos':
    from facility_finder.google_places import render_view
    st.button('← Back to nearby', on_click=change_view, args=('discover',))
    render_view(st.session_state.get('google_context'))
else:
    from facility_finder.evidence import render_about
    st.button('← Back to nearby', on_click=change_view, args=('discover',))
    render_about()

if st.session_state.view != 'feedback':
    with st.container(key='feedback-footer'):
        st.button('Help improve Lokito', on_click=change_view, args=('feedback',))

if st.session_state.view == 'discover' and st.session_state.detail_id is not None:
    detail_record = selected_facility(ranked, st.session_state.detail_id)
    if detail_record:
        show_details(detail_record)

html('<footer class="footer"><span><b>lokito</b> · Small stops. Better days.</span>'
     '<span>Jakarta pilot · <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">© OpenStreetMap contributors</a></span></footer>')
