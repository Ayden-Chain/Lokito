"""Optional Places (New) adapter: persist IDs only; photos are explicitly requested."""
import json
import os
import re
from html import escape
from pathlib import Path

import requests

from facility_finder.data import haversine_km, valid_coordinates
from facility_finder.enrichment import CACHE, normalized_name
from facility_finder.ingest import atomic_json
from facility_finder.media import safe_url

IDS=CACHE.parent/'google-place-ids.json'
TYPES={'mall':{'shopping_mall'},'fuel':{'gas_station'},'station':{'transit_station','train_station','subway_station','bus_station'},
       'park':{'park'},'market':{'market','marketplace'},'hospital':{'hospital'},'university':{'university'},
       'attraction':{'tourist_attraction'},'public_building':{'government_office','local_government_office','city_hall'}}
PLACE_ID=re.compile(r'^[A-Za-z0-9_-]{10,300}$')


def configured(): return bool(os.environ.get('GOOGLE_MAPS_API_KEY'))


def policy_urls():
    urls=[os.environ.get(k,'') for k in ('LOKITO_PRIVACY_URL','LOKITO_TERMS_URL')]
    from urllib.parse import urlsplit
    try:
        return urls if all(safe_url(u,{urlsplit(u).hostname}) and urlsplit(u).hostname not in ('localhost','127.0.0.1') for u in urls) else None
    except ValueError: return None


class GooglePlaces:
    def __init__(self,session=None):
        self.session=session or requests.Session()

    def request(self,method,path,mask=None,**kwargs):
        key=os.environ.get('GOOGLE_MAPS_API_KEY')
        if not key: return None
        headers={'X-Goog-Api-Key':key}
        if mask: headers['X-Goog-FieldMask']=mask
        try:
            r=self.session.request(method,'https://places.googleapis.com/v1/'+path,headers=headers,
                                   timeout=(8,20),allow_redirects=False,**kwargs)
            if r.status_code != 200: return None
            result=r.json()
            return result if isinstance(result,dict) and not result.get('error') else None
        except (requests.RequestException,ValueError): return None  # Never log request URLs/headers.

    def match(self,venue):
        if not configured(): return None
        result=self.request('POST','places:searchText','places.id,places.displayName,places.location,places.types',json={
            'textQuery':venue['venue_name']+' Jakarta','pageSize':5,
            'locationBias':{'circle':{'center':{'latitude':venue['latitude'],'longitude':venue['longitude']},'radius':300.0}}})
        if not result or not isinstance(result.get('places',[]),list): return None
        matches=[]
        for p in result.get('places',[]):
            if not isinstance(p,dict) or not isinstance(p.get('location',{}),dict) or not isinstance(p.get('displayName',{}),dict) or not isinstance(p.get('types',[]),list): continue
            point=p.get('location',{})
            if normalized_name(p.get('displayName',{}).get('text','')) != normalized_name(venue['venue_name']): continue
            if not TYPES[venue['venue_category']].intersection(p.get('types',[])): continue
            if not valid_coordinates(point.get('latitude'),point.get('longitude')): continue
            if haversine_km(venue['latitude'],venue['longitude'],point['latitude'],point['longitude']) > .15: continue
            if isinstance(p.get('id'),str) and PLACE_ID.fullmatch(p['id']): matches.append(p['id'])
        return matches[0] if len(set(matches))==1 else None

    def photo(self,place_id):
        if not PLACE_ID.fullmatch(place_id): return None
        details=self.request('GET',f'places/{place_id}','photos')
        if not details or not isinstance(details.get('photos',[]),list): return None
        for photo in details.get('photos',[]):
            if not isinstance(photo,dict): continue
            name=photo.get('name','')
            if not isinstance(name,str) or not re.fullmatch(r'places/'+re.escape(place_id)+r'/photos/[A-Za-z0-9_-]+',name): continue
            source=photo.get('googleMapsUri','')
            if not safe_url(source,{'www.google.com','maps.google.com'}): continue
            attrs=photo.get('authorAttributions',[])
            if not isinstance(attrs,list) or any(not isinstance(a,dict) or not isinstance(a.get('displayName'),str) or not a['displayName'] or not safe_url(a.get('uri'),{'www.google.com','maps.google.com'}) for a in attrs): continue
            media=self.request('GET',name+'/media',params={'maxWidthPx':640,'skipHttpRedirect':True})
            if not media: continue
            uri=media.get('photoUri','')
            if not safe_url(uri,{'lh3.googleusercontent.com','lh4.googleusercontent.com','lh5.googleusercontent.com','lh6.googleusercontent.com'}): continue
            # This transient value is never written to disk or Streamlit cache.
            return {'url':uri,'source_url':source,'authors':attrs}
        return None


def load_ids(path=IDS):
    try:
        payload=json.loads(Path(path).read_text())
        return {k:v for k,v in payload.items() if isinstance(v,str) and PLACE_ID.fullmatch(v)} if isinstance(payload,dict) else {}
    except (OSError,ValueError): return {}


def match_place_ids(cache,path=IDS):
    if not configured(): return {'status':'disabled','matches':0}
    current=load_ids(path)
    client=GooglePlaces()
    venues={c['venue_id']:c for c in cache['records'].values()}
    # Deliberately bounded; invoking this option may incur billing.
    for vid,venue in list(sorted(venues.items()))[:50]:
        if vid not in current:
            pid=client.match(venue)
            if pid: current[vid]=pid
    atomic_json(path,current)
    return {'status':'complete','matches':len(current)}


def render_view(context):
    import streamlit as st
    st.subheader('Venue photos from Google Maps')
    st.caption('Venue photos may not show the toilet. This separate view contains no OpenStreetMap map.')
    urls=policy_urls()
    if not configured() or not urls:
        st.info('Google photos are not enabled. Available Wikimedia photos remain in the facility details.')
        return
    st.link_button('Privacy policy',urls[0])
    st.link_button('Terms of use',urls[1])
    pid=load_ids().get(context['venue_id']) if context else None
    if not pid:
        st.info('No unambiguous Google place match is available for this venue.')
        return
    st.write(context['venue_name'])
    if st.button('Load venue photo',type='primary'):
        photo=GooglePlaces().photo(pid)
        if not photo:
            st.info('A Google photo could not be loaded. You can still use the venue context and directions.')
            return
        with st.container(border=True):
            st.image(photo['url'],caption='Venue photo · not necessarily a photo of the toilet',width='stretch')
            st.markdown('<span class="google-attribution" translate="no">Google Maps</span>',unsafe_allow_html=True)
            for author in photo['authors']:
                avatar=author.get('photoUri','')
                if safe_url(avatar,{'lh3.googleusercontent.com','lh4.googleusercontent.com','lh5.googleusercontent.com','lh6.googleusercontent.com'}): st.image(avatar,width=32)
                st.link_button('Photo: '+author['displayName'],author['uri'])
            st.link_button('View original photo on Google Maps ↗',photo['source_url'])
