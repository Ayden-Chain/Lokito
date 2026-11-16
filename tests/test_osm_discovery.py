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
    assert '"scrollWheelZoom": false' in rendered and '"touchZoom": true' in rendered
    assert 'lokito-gesture-hint' in rendered and 'Belum dicek Lokito' in rendered
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
    assert 'Ada toilet terpetakan di tempat ini' in markup
    assert 'Akses dan ketersediaan saat ini belum dicek' in markup
    assert 'Biasanya ada toilet' not in markup
    assert 'href="https://www.openstreetmap.org/' not in markup


def test_likely_toilet_venues_join_results_and_follow_filters():
    at = AppTest.from_file(str(ROOT/'app.py'), default_timeout=30).run()
    nearest = at.session_state['selected_id']
    assert any('43 toilet terpetakan' in m.value for m in at.markdown)
    next(b for b in at.button if b.label=='Pilih nomor 3 →').click().run()
    assert not at.exception and at.session_state['selected_id'] != nearest
    next(s for s in at.selectbox if s.label=='Jarak maksimal').set_value('1 km')
    next(b for b in at.button if b.label=='Terapkan').click().run()
    assert not at.exception and at.session_state['selected_id'] == nearest
    assert any('2 toilet terpetakan' in m.value for m in at.markdown)


def test_venue_rows_skip_kiosks_and_venues_with_a_mapped_toilet():
    from facility_finder.proxies import venue_rows
    catalog = {
        'way/1': {'venue_id':'way/1','venue_name':'Plaza','venue_category':'mall','latitude':-6.2,'longitude':106.8},
        'node/2': {'venue_id':'node/2','venue_name':'Pertamini Jaya','venue_category':'fuel','latitude':-6.2,'longitude':106.8},
        'node/3': {'venue_id':'node/3','venue_name':'Halte X','venue_category':'station','latitude':-6.2,'longitude':106.8},
        'way/4': {'venue_id':'way/4','venue_name':'RS Y','venue_category':'hospital','latitude':-6.2,'longitude':106.8},
    }
    rows = venue_rows(catalog, skip_venue_ids={'way/4'})
    assert list(rows.facility_id) == ['venue:way/1']
    assert rows.iloc[0].facility_category == 'toilets' and rows.iloc[0].fee == 'unknown'


def test_mosques_become_likely_toilets_with_their_own_note():
    from facility_finder.proxies import mosque_rows, NOTE
    mapped = pd.DataFrame([
        {'facility_id':'node/1','facility_category':'place_of_worship','religion':'muslim','name':'unknown',
         'latitude':-6.2,'longitude':106.8,'source_url':'u','coordinate_method':'node'},
        {'facility_id':'node/2','facility_category':'place_of_worship','religion':'christian','name':'Gereja',
         'latitude':-6.2,'longitude':106.8,'source_url':'u','coordinate_method':'node'}])
    rows = mosque_rows(mapped)
    assert list(rows.facility_id) == ['mosque:node/1'] and rows.iloc[0]['name'] == 'Masjid/musala'
    assert rows.iloc[0].facility_category == 'toilets' and 'wudu' in NOTE['mosque']


def test_osm_toilet_places_and_pertamina_labels(tmp_path):
    import json
    from facility_finder.proxies import tagged_rows, venue_rows, KIND
    from facility_finder.toilet_places import records
    elements = [{'type':'area','id':1,'tags':{'ISO3166-2':'ID-JK'}},
                {'type':'node','id':5,'lat':-6.2,'lon':106.8,'tags':{'toilets':'yes','name':'Indomaret','toilets:fee':'no','toilets:access':'permissive'}},
                {'type':'way','id':6,'center':{'lat':-6.21,'lon':106.81},'tags':{'railway':'station','station':'subway','name':'Blok M BCA'}},
                {'type':'node','id':7,'lat':-6.2,'lon':106.8,'tags':{'toilets':'yes'}}]
    rows = records(elements)
    assert [r['kind'] for r in rows] == ['tagged_open', 'mrt'] and rows[0]['fee'] == 'no'
    path = tmp_path / 'toilet_places.json'
    path.write_text(json.dumps({'places': rows}))
    tagged = tagged_rows(path)
    assert list(tagged.facility_id) == ['tagged:node/5', 'tagged:way/6'] and tagged.iloc[0].fee == 'no'
    assert tagged.iloc[0].access == 'permissive'  # so the "Terbuka untuk umum" filter keeps it
    assert tagged_rows(tmp_path / 'missing.json').empty
    fuel = {str(i): {'venue_id':f'node/{i}','venue_name':n,'venue_category':'fuel','latitude':-6.2,'longitude':106.8}
            for i, n in enumerate(['SPBU 34-11611', 'Shell', 'Pertashop'])}
    labels = dict(zip(venue_rows(fuel).name, venue_rows(fuel).venue_category))
    assert labels == {'SPBU 34-11611': 'fuel_pertamina', 'Shell': 'fuel'}
    assert 'gratis' in KIND['fuel_pertamina']
