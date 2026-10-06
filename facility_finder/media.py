"""Official Wikimedia media resolution. Only called by the enrichment command."""
import re
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urlsplit, quote

import requests

HEADERS = {'User-Agent': 'LokitoAcademicPrototype/0.2 (Jakarta facility research)'}


class PlainText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
    def handle_data(self, data): self.parts.append(data)


def plain(value):
    parser = PlainText()
    parser.feed(str(value or ''))
    return ' '.join(' '.join(parser.parts).split())[:600]


def safe_url(value, hosts):
    if not isinstance(value, str) or any(ord(c) < 32 for c in value) or '\\' in value: return False
    try:
        url = urlsplit(value)
        return (url.scheme == 'https' and url.hostname in hosts and not url.username and not url.password
                and url.port in (None,443))
    except ValueError: return False


def valid_photo(photo):
    if not isinstance(photo, dict) or photo.get('provider') != 'Wikimedia Commons': return False
    fields = ('filename','author','licence','licence_url','page_url','thumbnail_url','retrieved_at','alt')
    if any(not isinstance(photo.get(k),str) or not photo[k].strip() for k in fields): return False
    if not re.search(r'\.(jpg|jpeg|png|webp)$', photo['filename'], re.I): return False
    if re.search(r'\b(logo|logotype|coat of arms|flag|map)\b',photo['filename'],re.I): return False
    if not safe_url(photo['thumbnail_url'], {'upload.wikimedia.org','thumb.wikimedia.org'}): return False
    if not urlsplit(photo['thumbnail_url']).path.startswith('/wikipedia/commons/'): return False
    if not safe_url(photo['page_url'], {'commons.wikimedia.org'}) or not urlsplit(photo['page_url']).path.startswith('/wiki/File:'): return False
    if not safe_url(photo['licence_url'], {'creativecommons.org'}): return False
    license_path = urlsplit(photo['licence_url']).path
    return bool(re.fullmatch(r'/(?:licenses/(?:by|by-sa)/[1234]\.0|publicdomain/(?:zero/1\.0|mark/1\.0))/?', license_path))


def parse_imageinfo(payload, venue_name):
    if not isinstance(payload,dict) or payload.get('error'): raise ValueError('Wikimedia returned an API error')
    query=payload.get('query',{})
    if not isinstance(query,dict) or not isinstance(query.get('pages',{}),dict): raise ValueError('Invalid Wikimedia pages')
    pages = query.get('pages', {})
    for page in pages.values():
        if not isinstance(page,dict) or not isinstance(page.get('imageinfo',[]),list): raise ValueError('Invalid Wikimedia image metadata')
        info = (page.get('imageinfo') or [None])[0]
        if not info: continue
        if not isinstance(info,dict) or not isinstance(info.get('extmetadata',{}),dict): raise ValueError('Invalid Wikimedia licence metadata')
        meta = info.get('extmetadata', {})
        if any(not isinstance(v,dict) for v in meta.values()): raise ValueError('Invalid Wikimedia metadata field')
        value = lambda key: plain(meta.get(key, {}).get('value', ''))
        if value('Restrictions') or value('NonFree'): continue
        photo = {'provider':'Wikimedia Commons', 'filename':page.get('title',''),
                 'thumbnail_url':info.get('thumburl',''), 'page_url':info.get('descriptionurl',''),
                 'author':value('Artist'), 'credit':value('Credit'), 'licence':value('LicenseShortName'),
                 'licence_url':value('LicenseUrl'), 'retrieved_at':datetime.now(timezone.utc).isoformat(),
                 'source_identifier':page.get('title',''), 'alt':f'Venue photograph of {venue_name}',
                 'subject':'venue', 'description':value('ImageDescription')}
        if photo['licence_url'].startswith('//'): photo['licence_url']='https:'+photo['licence_url']
        if valid_photo(photo): return photo
    return None


class Wikimedia:
    def __init__(self, session=None):
        self.session = session or requests.Session()
        self.entities = {}

    def get(self, url, **kwargs):
        response = self.session.get(url, headers=HEADERS, timeout=(10,25), allow_redirects=False, **kwargs)
        if response.status_code in (429,503):
            retry = response.headers.get('Retry-After','8')
            # Never disregard a server-directed backoff longer than our budget.
            if retry.isdigit() and int(retry)<=30:
                time.sleep(max(8,int(retry)))
                response = self.session.get(url, headers=HEADERS, timeout=(10,25), allow_redirects=False, **kwargs)
        if response.status_code != 200: raise ValueError(f'Media source unavailable (HTTP {response.status_code})')
        payload = response.json()
        if not isinstance(payload,dict) or payload.get('error'): raise ValueError('Invalid media response')
        return payload

    def filename(self, tags):
        direct = tags.get('wikimedia_commons') or tags.get('image', '')
        if direct.startswith('File:'): return direct
        qid = tags.get('wikidata','')
        if not re.fullmatch(r'Q[1-9][0-9]*',qid):
            wiki = tags.get('wikipedia','')
            if ':' not in wiki: return None
            language, title = wiki.split(':',1)
            if not re.fullmatch(r'[a-z-]{2,12}', language): return None
            payload = self.get('https://www.wikidata.org/w/api.php', params={
                'action':'wbgetentities','sites':language.replace('-','_')+'wiki','titles':title,'props':'claims','format':'json'})
            entities = payload.get('entities',{})
        else:
            if qid not in self.entities:
                self.entities[qid] = self.get(f'https://www.wikidata.org/wiki/Special:EntityData/{qid}.json')
            entities = self.entities[qid].get('entities',{})
        for entity in entities.values():
            for claim in entity.get('claims',{}).get('P18',[]):
                if claim.get('rank') == 'deprecated': continue
                name = claim.get('mainsnak',{}).get('datavalue',{}).get('value')
                if isinstance(name,str): return 'File:'+name
        return None

    def photo(self, venue):
        filename = self.filename(venue['tags'])
        if not filename: return None
        payload = self.get('https://commons.wikimedia.org/w/api.php', params={
            'action':'query','format':'json','titles':filename,'prop':'imageinfo',
            'iiprop':'url|extmetadata','iiurlwidth':640})
        return parse_imageinfo(payload,venue['venue_name'])
