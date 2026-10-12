"""Synthetic edge cases; no network and no changes to real data."""
import copy
import json
from unittest.mock import Mock

import pytest
import requests

from facility_finder import enrichment as en
from facility_finder import enrich_places as pipeline
from facility_finder import media
from facility_finder.venue_ui import display_title, context_copy, photo_html, nearby_venue_html


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    monkeypatch.setattr(requests.sessions.Session,'request',lambda *a,**k: pytest.fail('Unexpected network request'))


def facility(**kw):
    return dict(facility_id='node/900',osm_type='node',latitude=0.,longitude=0.,name='unknown',
                facility_category='toilets',tags={}) | kw


def venue(vid=1,cat='mall',lon=.001,name='Example Mall',geometry=None):
    return dict(venue_id=f'way/{vid}',venue_name=name,venue_category=cat,latitude=0.,longitude=lon,
                source='OpenStreetMap',source_url=f'https://www.openstreetmap.org/way/{vid}',tags={},outer=geometry or [],holes=[])


def match(row=None,venues=None):
    return en.match_venue(row or facility(),venues or [venue()],'2026-10-06T00:00:00Z')


def photo():
    return dict(provider='Wikimedia Commons',filename='File:Example venue.jpg',author='Example author',
                licence='CC BY-SA 4.0',licence_url='https://creativecommons.org/licenses/by-sa/4.0/',
                page_url='https://commons.wikimedia.org/wiki/File:Example_venue.jpg',
                thumbnail_url='https://thumb.wikimedia.org/wikipedia/commons/thumb/a/ab/Example_venue.jpg/640px-Example_venue.jpg',
                retrieved_at='2026-10-06T00:00:00Z',alt='Venue photograph of Example Mall',subject='venue',source_identifier='File:Example venue.jpg')


def test_explicit_priority_and_no_brand_inference():
    for row in (facility(tags={'located_in':'Example Mall'}),facility(name='Toilet di Example Mall')):
        assert match(row)['relationship_type']=='at'
    assert match(facility(tags={'brand':'Example Mall','operator':'Example Mall'}))['relationship_type']=='near'


def test_geometry_holes_boundaries_and_non_nodes():
    square=[(-.01,-.01),(.01,-.01),(.01,.01),(-.01,.01),(-.01,-.01)]
    v=venue(geometry=[square])
    assert match(venues=[v])['relationship_type']=='inside'
    assert match(facility(osm_type='way'),[v])['relationship_type']=='near'
    v['holes']=[square]
    assert match(venues=[v])['relationship_type']=='near'
    assert not en.inside_ring((.01,0),square)
    assert en.inside_ring((.01,0),square,boundary=True)
    assert en.ring([{'lon':x,'lat':y} for x,y in [(0,0),(1,1),(0,1),(1,0),(0,0)]]) is None


@pytest.mark.parametrize('cat',en.LIMITS)
def test_category_thresholds(cat):
    metres=en.LIMITS[cat]
    assert match(venues=[venue(cat=cat,lon=(metres-1)/111195)])['relationship_type']=='near'
    assert match(venues=[venue(cat=cat,lon=(metres+1)/111195)]) is None


def test_ambiguity_determinism_invalid_coordinates():
    a,b=venue(),venue(2,lon=.0011,name='Different mall')
    assert match(venues=[a,b]) is None
    b['longitude']=.0017
    assert match(venues=[a,b])==match(venues=[b,a])
    assert match(facility(latitude=float('nan'))) is None


def test_normalization_names_duplicates_and_geometry():
    node={'type':'node','id':1,'lat':0,'lon':0,'tags':{'shop':'mall','name':'Test Mall'}}
    geom=[{'lat':a,'lon':b} for a,b in [(-.001,-.001),(-.001,.001),(.001,.001),(.001,-.001),(-.001,-.001)]]
    way={'type':'way','id':2,'geometry':geom,'tags':node['tags']}
    unnamed=dict(node,id=3,tags={'shop':'mall'})
    result=en.normalize_venues([node,way,unnamed,node])
    assert len(result)==1 and result[0]['venue_id']=='way/2' and result[0]['outer']
    way['geometry']=geom[:-1]
    assert not en.normalize_venues([way])[0]['outer']


def test_cache_validation_and_failed_refresh_preserves_bytes(tmp_path):
    path=tmp_path/'places.json'
    for content in ('','[]','{broken','{"schema_version":1,"records":{}}'):
        path.write_text(content)
        assert en.load_cache(path)['records']=={}
    cache={'schema_version':1,'records':{'node/900':match()}}
    pipeline.commit(cache,path)
    original=path.read_bytes()
    def failure(*a,**k): raise requests.Timeout()
    result,mode=pipeline.refresh(path=path,fetcher=failure)
    assert mode=='cache_fallback' and path.read_bytes()==original
    with pytest.raises(ValueError): pipeline.commit({'schema_version':1,'records':{}},path,cache)
    bad=copy.deepcopy(cache); bad['records']['node/900']['distance_metres']=float('nan')
    with pytest.raises(ValueError): pipeline.commit(bad,path,cache)
    assert path.read_bytes()==original


def test_build_complete_snapshot_and_partial_rejection(monkeypatch):
    monkeypatch.setattr(pipeline,'validate_response',lambda x: None)
    vs=[venue(i+1,cat=cat,lon=10+i) for i,cat in enumerate(en.LIMITS)]
    vs[0]['longitude']=.001
    monkeypatch.setattr(pipeline,'normalize_venues',lambda elements:vs)
    snapshot={'payload':{'elements':[]},'fetched_at':'2026-10-06','endpoint':'https://example.test','query':'fixture'}
    result=pipeline.build(snapshot,[facility()],photo_limit=0)
    assert result['metadata']['facilities_enriched']==1
    vs.pop()
    with pytest.raises(ValueError,match='Incomplete'): pipeline.build(snapshot,[facility()])


def test_build_keeps_valid_media_when_other_lookups_fail(monkeypatch):
    monkeypatch.setattr(pipeline,'validate_response',lambda x: None)
    first=venue(1,name='First Mall',lon=.001)
    second=venue(2,name='Second Mall',lon=.002)
    others=[venue(i+3,cat=cat,lon=10+i) for i,cat in enumerate(en.LIMITS) if cat!='mall']
    monkeypatch.setattr(pipeline,'normalize_venues',lambda elements:[first,second,*others])
    snapshot={'payload':{'elements':[]},'fetched_at':'2026-10-06','endpoint':'https://example.test','query':'fixture'}
    previous={'schema_version':1,'records':{'node/900':match()}}
    def resolver(item):
        if item['venue_name']=='Second Mall': raise ValueError('Commons page unavailable')
        return photo()
    result=pipeline.build(snapshot,[facility()],resolver=resolver,previous=previous,photo_limit=2)
    assert result['venues']['way/1']['photo']['filename']==photo()['filename']
    assert result['venues']['way/2']['photo'] is None
    assert result['metadata']['media_failures']==['way/2']
    assert result['metadata']['status']=='context_complete_media_partial'
    assert result['metadata']['media_attempted']==2
    previous=result
    def limited(item): raise media.MediaRateLimited('provider backoff')
    again=pipeline.build(snapshot,[facility()],resolver=limited,previous=previous,photo_limit=60)
    assert again['venues']['way/1']['photo']==result['venues']['way/1']['photo']
    assert again['metadata']['media_attempted']==1 and again['metadata']['media_rate_limited']


def test_wikidata_name_search_requires_nearby_coordinates(monkeypatch):
    resolver=media.Wikimedia()
    tags={'_venue_name':'Example Mall','_venue_latitude':0.,'_venue_longitude':0.}
    entity={'entities':{'Q123':{'claims':{'P18':[{'mainsnak':{'datavalue':{'value':'Example.jpg'}}}],
        'P625':[{'mainsnak':{'datavalue':{'value':{'latitude':30.,'longitude':30.}}}}]}}}}
    resolver.get=Mock(side_effect=[{'search':[{'label':'Example Mall','id':'Q123'}]},entity])
    assert resolver.filename(tags) is None
    entity['entities']['Q123']['claims']['P625'][0]['mainsnak']['datavalue']['value']={'latitude':.001,'longitude':.001}
    resolver.get=Mock(return_value={'search':[{'label':'Example Mall','id':'Q123'}]})
    assert resolver.filename(tags)=='File:Example.jpg'


def test_commons_category_lookup_uses_source_category():
    resolver=media.Wikimedia()
    resolver.get=Mock(return_value={'query':{'pages':{}}})
    assert resolver.photo({'venue_name':'Grand Indonesia','tags':{'wikimedia_commons':'Category:Grand Indonesia'}}) is None
    params=resolver.get.call_args.kwargs['params']
    assert params['generator']=='categorymembers' and params['gcmtitle']=='Category:Grand Indonesia'


def test_wikimedia_metadata_and_html_attribution():
    p=photo()
    payload={'query':{'pages':{'1':{'title':p['filename'],'imageinfo':[{'thumburl':p['thumbnail_url'],
        'descriptionurl':p['page_url'],'extmetadata':{k:{'value':v} for k,v in {
        'Artist':'<a href="https://example.test">Example author</a>','LicenseShortName':p['licence'],
        'LicenseUrl':p['licence_url']}.items()}}]}}}}
    parsed=media.parse_imageinfo(payload,'Example Mall')
    assert parsed['author']=='Example author' and media.valid_photo(parsed)
    markup=photo_html(parsed)
    assert 'not necessarily a photo of the toilet' in markup and p['licence_url'] in markup
    payload['query']['pages']['1']['imageinfo'][0]['extmetadata'].pop('LicenseUrl')
    assert media.parse_imageinfo(payload,'Example Mall') is None
    for invalid in ([], {'query':[]}, {'query':{'pages':[]}}, {'query':{'pages':{'1':{'imageinfo':{}}}}}):
        with pytest.raises(ValueError): media.parse_imageinfo(invalid,'Example Mall')


@pytest.mark.parametrize('field,value',[
    ('thumbnail_url','https://upload.wikimedia.org.evil.test/wikipedia/commons/a.jpg'),
    ('thumbnail_url','javascript:alert(1)'),('thumbnail_url','https://user@upload.wikimedia.org/a.jpg'),
    ('licence_url','https://creativecommons.org/licenses/by-nc/4.0/'),('licence_url','https://evil.test/by/4.0'),
    ('filename','File:Example logo.png'),('filename','File:Example.svg'),('author','')])
def test_unsafe_or_unlicensed_media_hidden(field,value):
    p=photo();p[field]=value
    assert not media.valid_photo(p) and photo_html(p)==''


def test_context_long_names_escape_and_missing_image():
    context=match(venues=[venue(name='<script>alert(1)</script> '+'Long venue '*30)])
    row=facility(venue_context=context)
    assert 'near' in display_title(row)
    markup=context_copy(row,detail=True)
    assert '<script>' not in markup and '&lt;script&gt;' in markup and 'Location label by Lokito' in markup
    assert photo_html(None)=='' and context_copy(facility())==''


def test_nearby_venues_include_malls_without_claiming_toilet_and_apply_filters():
    catalog={
        'way/1': {'venue_id':'way/1','venue_name':'Plaza Indonesia','venue_category':'mall','latitude':0.,'longitude':.001,'source_url':'https://www.openstreetmap.org/way/1'},
        'node/2': {'venue_id':'node/2','venue_name':'SPBU Sudirman','venue_category':'fuel','latitude':0.,'longitude':.002,'source_url':'https://www.openstreetmap.org/node/2'},
        'way/3': {'venue_id':'way/3','venue_name':'Far mall','venue_category':'mall','latitude':0.,'longitude':1.,'source_url':'https://www.openstreetmap.org/way/3'},
    }
    nearby=en.nearby_venues(catalog,(0.,0.),radius_km=1)
    assert [place['venue_name'] for place in nearby]==['Plaza Indonesia','SPBU Sudirman']
    assert en.nearby_venues(catalog,(0.,0.),search='plaza')[0]['venue_id']=='way/1'
    assert en.nearby_venues(catalog,(0.,0.),categories=('mall',))[0]['venue_category']=='mall'
    assert [p['venue_id'] for p in en.nearby_venues(catalog,(0.,0.),radius_km=1,exclude_ids={'way/1'})]==['node/2']
    markup=nearby_venue_html(nearby[0],(0.,0.))
    assert 'Plaza Indonesia' in markup and 'Sumber data: OpenStreetMap' in markup
    assert 'No toilet location is explicitly linked inside this venue' in markup
    assert 'does not mean the venue has no toilets' in markup
    assert 'href="https://www.openstreetmap.org/' not in markup


def test_map_contains_separate_blue_venue_pin_with_explicit_caveat():
    import pandas as pd
    from facility_finder.maps import build_map
    venue={'venue_id':'way/1','distance_km':0.157,'venue_name':'Plaza Indonesia','venue_category':'mall','latitude':-.001,'longitude':.001,
           'source_url':'https://www.openstreetmap.org/way/1'}
    rendered=build_map(pd.DataFrame(columns=['facility_id','latitude','longitude']), (0.,0.), venues=[venue]).get_root().render()
    assert 'place: Mall: Plaza Indonesia' in rendered
    assert 'No toilet location is explicitly linked inside this venue' in rendered
