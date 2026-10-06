"""Explicit OSM venue + Wikimedia enrichment, preserving the original facility cache."""
import argparse
import hashlib
import json
import logging
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import requests

from facility_finder.data import load_facilities, PROCESSED
from facility_finder.enrichment import CACHE, LIMITS, normalize_venues, match_venue, load_cache, validate_cache
from facility_finder.ingest import atomic_json, request_query, validate_response
from facility_finder.media import Wikimedia, valid_photo

LOG = logging.getLogger(__name__)


def query():
    return ('[out:json][timeout:60];area["ISO3166-2"="ID-JK"]["boundary"="administrative"]->.jakarta;'
            '.jakarta out tags;('
            'nwr["shop"="mall"](area.jakarta);'
            'nwr["amenity"~"^(fuel|bus_station|marketplace|hospital|university|college|townhall)$"](area.jakarta);'
            'nwr["railway"="station"](area.jakarta);nwr["public_transport"="station"](area.jakarta);'
            'nwr["leisure"="park"](area.jakarta);nwr["tourism"="attraction"](area.jakarta);'
            'nwr["office"="government"](area.jakarta););out meta geom;')


def build(snapshot, rows, resolver=None, previous=None, photo_limit=60):
    validate_response(snapshot['payload'])
    venues = normalize_venues(snapshot['payload']['elements'])
    if not venues: raise ValueError('No usable venues; refusing empty refresh')
    if set(LIMITS)-{v['venue_category'] for v in venues}: raise ValueError('Incomplete venue categories; refusing refresh')
    timestamp = datetime.now(timezone.utc).isoformat()
    records = {}
    for row in rows:
        context = match_venue(row, venues, timestamp)
        if context: records[row['facility_id']]=context
    if not records: raise ValueError('No associations; refusing empty refresh')
    venue_by_id = {v['venue_id']:v for v in venues}
    photos={c['venue_id']:c['photo'] for c in (previous or {}).get('records',{}).values()
            if valid_photo(c.get('photo'))}
    errors = []
    toilet_venues={records[r['facility_id']]['venue_id'] for r in rows if r['facility_category']=='toilets' and r['facility_id'] in records}
    media_candidates=sorted({c['venue_id'] for c in records.values()}, key=lambda v:(v not in toilet_venues,v))
    media_candidates=[v for v in media_candidates if any(venue_by_id[v]['tags'].get(k) for k in ('wikidata','wikipedia','wikimedia_commons','image'))]
    if resolver:
        for vid in media_candidates[:photo_limit]:
            venue = venue_by_id[vid]
            if not any(venue['tags'].get(k) for k in ('wikidata','wikipedia','wikimedia_commons','image')): continue
            try:
                photo = resolver(venue)
                photos[vid]=photo if valid_photo(photo) else None
            except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
                errors.append(vid)
                LOG.warning('Photo source failed for %s (%s); no image invented.',vid,type(exc).__name__)
            time.sleep(.15)
    if errors and previous and previous.get('records'):
        raise ValueError('Incomplete media refresh; retaining entire previous cache')
    for c in records.values(): c['photo']=photos.get(c['venue_id'])
    counts = Counter(c['relationship_type'] for c in records.values())
    by_category = Counter(c['venue_category'] for c in records.values())
    result = {'schema_version':1, 'records':records, 'metadata':{
        'generated_at':timestamp, 'venue_snapshot_at':snapshot['fetched_at'],
        'venue_osm_base':snapshot['payload'].get('osm3s',{}).get('timestamp_osm_base'),
        'source_endpoint':snapshot['endpoint'], 'source_query':snapshot['query'],
        'source_facilities_sha256':hashlib.sha256((PROCESSED/'facilities.json').read_bytes()).hexdigest(),
        'venues':len(venues), 'facilities_enriched':len(records), 'relationships':dict(counts),
        'venue_categories':dict(by_category), 'wikimedia_photos':sum(bool(c['photo']) for c in records.values()),
        'unique_photos':len({c['photo']['page_url'] for c in records.values() if c['photo']}),
        'media_failures':errors, 'media_candidates':len(media_candidates), 'media_attempt_limit':photo_limit,
        'media_deferred':max(0,len(media_candidates)-photo_limit), 'thresholds_metres':LIMITS,
        'status':'context_complete_media_partial' if errors or len(media_candidates)>photo_limit else 'complete'}}
    return validate_cache(result)


def commit(result, path=CACHE, previous=None):
    validate_cache(result)
    if not result['records']: raise ValueError('Refusing empty cache replacement')
    if previous and len(result['records']) < len(previous['records'])*.7:
        raise ValueError('Association count dropped by more than 30%; inspect source before replacement')
    atomic_json(path,result)  # One authoritative atomic bundle, including metadata.


def refresh(path=CACHE, snapshot=None, fetcher=request_query, resolver=None, photo_limit=60):
    previous = load_cache(path)
    try:
        if snapshot is None: snapshot,_ = fetcher(query(),raw_dir=Path(path).parent/'raw')
        result = build(snapshot, load_facilities().to_dict('records'), resolver or Wikimedia().photo, previous, photo_limit)
        commit(result,path,previous)
        return result, 'refreshed'
    except (requests.RequestException, ValueError, RuntimeError, KeyError, TypeError, OSError):
        if previous['records']:
            LOG.warning('Refresh failed; previous enrichment cache is unchanged.')
            return previous, 'cache_fallback'
        raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh', action='store_true')
    parser.add_argument('--snapshot',type=Path,help='Use a saved complete venue snapshot; still resolves media explicitly')
    parser.add_argument('--google-map-ids',action='store_true',help='Explicit optional billable matching; saves only Place IDs')
    parser.add_argument('--photo-limit',type=int,default=60,help='Maximum venue media lookups; toilets first (default 60)')
    args=parser.parse_args()
    logging.basicConfig(level=logging.INFO,format='%(levelname)s: %(message)s')
    cached=load_cache()
    if cached['records'] and not args.refresh and not args.snapshot: result,mode=cached,'cache'
    else:
        snapshot=json.loads(args.snapshot.read_text()) if args.snapshot else None
        try: result,mode=refresh(snapshot=snapshot, photo_limit=max(0,args.photo_limit))
        except Exception as exc:
            LOG.error('Enrichment could not be completed (%s). Original data were not changed.',type(exc).__name__)
            raise SystemExit(1)
    if args.google_map_ids:
        from facility_finder.google_places import match_place_ids
        print(json.dumps({'google_places':match_place_ids(result)}))
    print(json.dumps({'mode':mode,**result.get('metadata',{})},indent=2))


if __name__ == '__main__': main()
