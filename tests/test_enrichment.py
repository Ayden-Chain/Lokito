"""Synthetic edge cases; no network and no changes to real data."""
import copy
import json
from unittest.mock import Mock

import pytest
import requests

from facility_finder import enrichment as en
from facility_finder import enrich_places as pipeline
from facility_finder import media
from facility_finder.venue_ui import display_title, context_copy, photo_html


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
