from urllib.parse import parse_qs, urlparse

import pandas as pd
import pytest

from facility_finder.presentation import (directions_url, distance_label, facility_name, known_details,
                                         marker_selection, selected_facility, unknown_summary, map_view_for_selection)


def test_directions_url_is_encoded_and_uses_exact_destination():
    url = directions_url({'latitude':-6.2022718, 'longitude':106.8222273}, (-6.195,106.823))
    parsed = urlparse(url)
    assert (parsed.scheme, parsed.netloc, parsed.path) == ('https','www.google.com','/maps/dir/')
    q = parse_qs(parsed.query)
    assert q['api'] == ['1'] and q['destination'] == ['-6.2022718,106.8222273']
    assert q['origin'] == ['-6.1950000,106.8230000'] and q['travelmode'] == ['walking']
    assert '%2C' in url
    assert 'origin' not in parse_qs(urlparse(directions_url({'latitude':0,'longitude':0})).query)


@pytest.mark.parametrize('lat,lon', [(float('nan'),0), (91,0), (0,181), (None,0), ('x',0)])
def test_invalid_directions_coordinates_are_rejected(lat,lon):
    with pytest.raises(ValueError):
        directions_url({'latitude':lat,'longitude':lon})


def test_unknowns_are_compact_and_do_not_create_positive_claims():
    row = {'facility_category':'toilets','name':'unknown','fee':None,'access':'unknown','wheelchair':'unknown'}
    assert facility_name(row) == 'Toilet'
    assert known_details(row) == []
    assert unknown_summary(row, compact=True) == "Access and fee details haven't been added yet."
    assert 'opening hours' in unknown_summary(row)
    assert 'wheelchair access' in unknown_summary(row)
    row.update(fee='no',access='customers',wheelchair='limited',opening_hours='Mo-Fr 08:00-17:00')
    values = [v for _,v,_ in known_details(row)]
    assert 'Free to use' in values and 'For customers' in values and 'Limited wheelchair access' in values
    assert 'Wheelchair accessible' not in values
    assert unknown_summary(row) == ''
    assert ('Opening hours','Mo-Fr 08:00-17:00','opening_hours') in known_details(row)


def test_distance_labels_do_not_infer_walking_time():
    assert distance_label(.813) == '810 m'
    assert distance_label(1.24) == '1.2 km'
    assert distance_label(0) == '0 m'
    with pytest.raises(ValueError):
        distance_label(-1)


def test_selection_preserves_valid_id_and_resets_missing_id():
    ranked = pd.DataFrame([{'facility_id':'node/7','distance_km':.2},{'facility_id':'node/8','distance_km':.4}])
    assert selected_facility(ranked)['facility_id'] == 'node/7'
    assert selected_facility(ranked,'node/8')['facility_id'] == 'node/8'
    assert selected_facility(ranked,'node/99')['facility_id'] == 'node/7'
    assert selected_facility(ranked.iloc[:0],'node/7') is None


def test_map_initial_view_accounts_for_mobile_height_and_selected_point():
    origin = (-6.195,106.823)
    near = map_view_for_selection(origin, {'latitude':-6.2022718, 'longitude':106.8222273})
    assert near['center'][0] == pytest.approx(-6.1986359)
    assert 12 <= near['zoom'] <= 14
    far = map_view_for_selection(origin, {'latitude':-6.35, 'longitude':106.8})
    assert far['zoom'] < near['zoom']
    assert map_view_for_selection(origin)['center'] == origin


def test_map_selection_only_accepts_current_results_and_resolves_collocated_records():
    rows = pd.DataFrame([{'facility_id':'node/7','latitude':-6.2,'longitude':106.8},
                         {'facility_id':'way/8','latitude':-6.2,'longitude':106.8}])
    event = {'last_object_clicked':{'lat':-6.2,'lng':106.8},'last_object_clicked_popup':'<div data-facility-id="way/8">Toilet</div>'}
    assert marker_selection(event, rows) == 'way/8'
    event['last_object_clicked_popup'] = '<div data-facility-id="node/999">Stale</div>'
    assert marker_selection(event, rows) is None
    event['last_object_clicked_popup'] = None
    assert marker_selection(event, rows) is None
    assert marker_selection(event, rows.head(1)) == 'node/7'
    assert marker_selection({}, rows) is None


def test_map_selection_uses_visible_tooltip_for_collocated_live_pin_events():
    rows = pd.DataFrame([{'facility_id':'node/7','latitude':-6.2,'longitude':106.8,'result_number':4},
                         {'facility_id':'way/8','latitude':-6.2,'longitude':106.8,'result_number':5}])
    event = {'last_object_clicked':{'lat':-6.2,'lng':106.8},
             'last_object_clicked_popup':'Toilet\nAccess and fee details have not been added yet.',
             'last_object_clicked_tooltip':'5. Toilet'}
    assert marker_selection(event, rows) == 'way/8'
    event['last_object_clicked_tooltip'] = '99. Toilet'
    assert marker_selection(event, rows) is None
