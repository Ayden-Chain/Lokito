"""Isolated persistence and mocked Places API contract tests."""
import sqlite3
from unittest.mock import Mock

import pytest
import requests

from facility_finder import feedback as f
from facility_finder.google_places import GooglePlaces, configured, match_place_ids, policy_urls


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.delenv('GOOGLE_MAPS_API_KEY',raising=False)
    monkeypatch.setattr(requests.sessions.Session,'request',lambda *a,**k:pytest.fail('Live request prohibited'))


def answers(**kw):
    return dict(ease='Yes',location_understanding='Partly',venue_usefulness='It was not shown',
                photo_usefulness='It was not shown',tester_type='Prefer not to say',comment='',score=None)|kw


def test_feedback_private_minimal_and_idempotent(tmp_path):
    db=tmp_path/'feedback.sqlite3'
    context={'facility_id':'node/1','category':'toilets','starting_preset':'Custom point',
             'latitude':-6.123456,'longitude':106.123456,'email':'must-not-store@example.test'}
    a=answers(comment="TEST ONLY '; DROP TABLE product_feedback; --")
    assert f.submit(a,context,{'node/1'},'a'*32,db)==f.submit(a,context,{'node/1'},'a'*32,db)
    r=f.summary(db); assert r['total']==1 and r['average_score'] is None
    with sqlite3.connect(db) as conn:
        row=conn.execute('SELECT starting_preset,viewport_category FROM product_feedback').fetchone()
        assert row==(None,None)
        tables=conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        assert tables==[('product_feedback',)]
        columns=[r[1] for r in conn.execute('PRAGMA table_info(product_feedback)')]
        assert not {'email','latitude','longitude','ip','name'}.intersection(columns)
    assert f.summary(tmp_path/'missing.db')['total']==0
    assert not (tmp_path/'missing.db').exists()


@pytest.mark.parametrize('change',[{'ease':None},{'score':True},{'score':6},{'comment':'x'*1501},
                                 {'tester_type':'invented'},{'photo_usefulness':'Yes'},{'venue_usefulness':'Yes'}])
def test_feedback_validation(tmp_path,change):
    with pytest.raises(ValueError): f.submit(answers(**change),{},set(),'a'*32,tmp_path/'test.db')
    assert not (tmp_path/'test.db').exists()


def test_google_disabled_and_invalid_policy(monkeypatch,tmp_path):
    assert not configured() and GooglePlaces().match({}) is None
    assert match_place_ids({'records':{}},tmp_path/'ids.json')['status']=='disabled'
    assert not (tmp_path/'ids.json').exists()
    monkeypatch.setenv('LOKITO_PRIVACY_URL','https://[')
    assert policy_urls() is None


def client(monkeypatch,responses):
    monkeypatch.setenv('GOOGLE_MAPS_API_KEY','synthetic-test-key-not-a-credential')
    session=Mock()
    session.request.side_effect=[Mock(status_code=status,json=Mock(return_value=body)) for status,body in responses]
    return GooglePlaces(session),session


def test_mocked_matching_ambiguity_and_field_mask(monkeypatch):
    place={'id':'ExamplePlaceId123','displayName':{'text':'Example Mall'},'types':['shopping_mall'],
           'location':{'latitude':0.,'longitude':0.}}
    venue={'venue_name':'Example Mall','venue_category':'mall','latitude':0.,'longitude':0.}
    c,s=client(monkeypatch,[(200,{'places':[place]}),(200,{'places':[place,dict(place,id='OtherPlaceId123')]}),(429,{})])
    assert c.match(venue)=='ExamplePlaceId123'
    assert c.match(venue) is None and c.match(venue) is None
    assert s.request.call_args_list[0].kwargs['headers']['X-Goog-FieldMask']=='places.id,places.displayName,places.location,places.types'
    assert 'key=' not in s.request.call_args_list[0].args[1]


def test_mocked_photo_all_authors_and_transient_reference(monkeypatch):
    pid='ExamplePlaceId123'
    attrs=[{'displayName':'Author A','uri':'https://www.google.com/maps/contrib/1'},
           {'displayName':'Author B','uri':'https://www.google.com/maps/contrib/2'}]
    details={'photos':[{'name':f'places/{pid}/photos/ExamplePhoto','googleMapsUri':'https://www.google.com/maps/photo/1','authorAttributions':attrs}]}
    c,s=client(monkeypatch,[(200,details),(200,{'photoUri':'https://lh3.googleusercontent.com/example'})])
    p=c.photo(pid)
    assert p['authors']==attrs and 'name' not in p and 'photoUri' not in p
    assert s.request.call_args_list[1].kwargs['params']=={'maxWidthPx':640,'skipHttpRedirect':True}
