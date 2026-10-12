"""Regression checks for landmark separation and honest map status."""
from pathlib import Path
import copy
import pandas as pd
from streamlit.testing.v1 import AppTest

from facility_finder.data import load_facilities, rank_nearest
from facility_finder.enrichment import load_cache, nearby_venues
from facility_finder.maps import build_map
from facility_finder.presentation import marker_selection
from facility_finder.venue_ui import nearby_venue_html

ORIGIN = (-6.195, 106.823)
ROOT = Path(__file__).resolve().parents[1]


def test_real_map_contains_every_nearby_venue_and_preserves_toilets():
    facilities = load_facilities()
    toilets = rank_nearest(facilities[facilities.facility_category == 'toilets'], *ORIGIN)
    toilets = toilets[toilets.distance_km <= 5].copy()
    toilets['result_number'] = range(1, len(toilets) + 1)
    before = toilets.copy(deep=True)
    venues = nearby_venues(load_cache()['venues'], ORIGIN)
    original_venues = copy.deepcopy(venues)
    rendered = build_map(toilets, ORIGIN, toilets.iloc[0].facility_id, venues).get_root().render()
    assert len(toilets) == 43
    for venue in venues:
        assert f'data-venue-id="{venue["venue_id"]}"' in rendered
    assert 'Plaza Indonesia' in rendered and 'Grand Indonesia Shopping Town' in rendered
    assert 'tile.openstreetmap.org' in rendered and 'openstreetmap.org/copyright' in rendered
    assert '"scrollWheelZoom": true' in rendered and '"touchZoom": true' in rendered
    assert 'Not verified by Lokito' in rendered
    assert 'class="lokito-pin verified' not in rendered
    assert 'href="https://www.openstreetmap.org/way/' not in rendered
    pd.testing.assert_frame_equal(toilets, before)
    assert venues == original_venues


def test_origin_click_cannot_select_colocated_facility():
    displayed = pd.DataFrame([{'facility_id':'node/7','latitude':ORIGIN[0],'longitude':ORIGIN[1]}])
    event = {'last_object_clicked':{'lat':ORIGIN[0],'lng':ORIGIN[1]},
             'last_object_clicked_tooltip':'Your starting point'}
    assert marker_selection(event, displayed) is None


def test_linked_venue_copy_does_not_claim_missing_toilet_or_verified_access():
    venue = nearby_venues(load_cache()['venues'], ORIGIN)[0] | {'toilet_linked':True}
    markup = nearby_venue_html(venue, ORIGIN)
    assert 'A mapped toilet is associated' in markup
    assert 'Access and current availability still need checking' in markup
    assert 'No toilet location' not in markup
    assert 'href="https://www.openstreetmap.org/' not in markup


def test_venue_focus_and_filter_change_keep_facility_selection_independent():
    at = AppTest.from_file(str(ROOT/'app.py'), default_timeout=30).run()
    nearest = at.session_state['selected_id']
    for venue_id in ['way/538319726','way/974882100']:
        at.button(key=f'venue_{venue_id}').click().run()
        assert not at.exception
        assert at.session_state['selected_id'] == nearest
        assert at.session_state['focus_venue_id'] == venue_id
        assert any('43 toilets within 5 km' in m.value for m in at.markdown)
    next(b for b in at.button if b.label=='Show option 3 on map →').click().run()
    assert at.session_state['selected_id'] != nearest
    assert at.session_state['focus_venue_id'] is None
    next(s for s in at.selectbox if s.label=='Look within').set_value('1 km')
    next(b for b in at.button if b.label=='Apply preferences').click().run()
    assert not at.exception and at.session_state['focus_venue_id'] is None
    assert any('2 toilets within 1 km' in m.value for m in at.markdown)
