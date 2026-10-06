"""Deterministic, conservative venue context. No network or source-record writes."""
import json
import math
import re
from collections import defaultdict
from pathlib import Path

from facility_finder.data import haversine_km, valid_coordinates

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / 'data/enrichment/places.json'
LIMITS = {'mall': 180, 'fuel': 70, 'station': 120, 'park': 100, 'market': 100,
          'hospital': 100, 'university': 120, 'attraction': 100, 'public_building': 70}
LABELS = {'mall': 'Mall', 'fuel': 'Fuel station', 'station': 'Transit station', 'park': 'Park',
          'market': 'Market', 'hospital': 'Hospital', 'university': 'University',
          'attraction': 'Tourist attraction', 'public_building': 'Public building'}
ID = re.compile(r'^(node|way|relation)/[1-9][0-9]*$')


def normalized_name(value):
    return re.sub(r'[^\w]+', ' ', str(value).casefold()).strip()


def category(tags):
    if tags.get('shop') == 'mall': return 'mall'
    if tags.get('amenity') == 'fuel': return 'fuel'
    if tags.get('railway') == 'station' or tags.get('public_transport') == 'station' or tags.get('amenity') == 'bus_station': return 'station'
    if tags.get('leisure') == 'park': return 'park'
    if tags.get('amenity') == 'marketplace': return 'market'
    if tags.get('amenity') == 'hospital': return 'hospital'
    if tags.get('amenity') in ('university', 'college'): return 'university'
    if tags.get('tourism') == 'attraction': return 'attraction'
    if tags.get('office') == 'government' or tags.get('amenity') == 'townhall': return 'public_building'
    return None


def ring(geometry):
    if not isinstance(geometry, list) or len(geometry) < 4: return None
    if any(not isinstance(p, dict) or not valid_coordinates(p.get('lat'), p.get('lon')) for p in geometry): return None
    points = [(float(p['lon']), float(p['lat'])) for p in geometry]
    if points[0] != points[-1] or len(set(points[:-1])) != len(points)-1: return None
    # Reject self-intersections and degenerate rings before claiming containment.
    def orient(a,b,c): return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    edges=list(zip(points,points[1:]))
    for i,(a,b) in enumerate(edges):
        for j,(c,d) in enumerate(edges[i+2:],i+2):
            if i==0 and j==len(edges)-1: continue
            if (max(a[0],b[0]) < min(c[0],d[0]) or max(c[0],d[0]) < min(a[0],b[0]) or
                max(a[1],b[1]) < min(c[1],d[1]) or max(c[1],d[1]) < min(a[1],b[1])): continue
            if orient(a,b,c)*orient(a,b,d)<=0 and orient(c,d,a)*orient(c,d,b)<=0: return None
    return points if abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in edges))>1e-12 else None


def inside_ring(point, points, boundary=False):
    """Ray casting; boundary points deliberately do not establish containment."""
    x, y = point
    contained = False
    for (ax, ay), (bx, by) in zip(points, points[1:]):
        cross = (x-ax)*(by-ay)-(y-ay)*(bx-ax)
        if abs(cross) < 1e-12 and min(ax,bx) <= x <= max(ax,bx) and min(ay,by) <= y <= max(ay,by):
            return boundary
        if (ay > y) != (by > y) and x < (bx-ax)*(y-ay)/(by-ay)+ax:
            contained = not contained
    return contained


def polygons(element):
    if element['type'] == 'way':
        points = ring(element.get('geometry'))
        return ([points], []) if points and element.get('tags', {}).get('area') != 'no' else ([], [])
    if element.get('tags', {}).get('type') != 'multipolygon': return [], []
    # Only complete closed rings are accepted. Split/incomplete member ways are
    # intentionally proximity-only until a full polygon assembler is available.
    outer, holes = [], []
    for member in element.get('members', []):
        if member.get('role') not in ('outer', 'inner'): continue
        points = ring(member.get('geometry'))
        if not points: return [], []
        (outer if member['role'] == 'outer' else holes).append(points)
    return outer, holes


def normalize_venues(elements):
    venues = []
    for element in elements:
        tags = element.get('tags') or {}
        cat = category(tags)
        name = tags.get('name') or tags.get('name:id') or tags.get('name:en')
        vid = f"{element.get('type')}/{element.get('id')}"
        point = element if element.get('type') == 'node' else element.get('center', {})
        if not point and element.get('type') != 'node':
            geometry=element.get('geometry',[]) or [p for m in element.get('members',[]) for p in m.get('geometry',[])]
            coords=[p for p in geometry if isinstance(p,dict) and valid_coordinates(p.get('lat'),p.get('lon'))]
            if coords:
                point={'lat':(min(p['lat'] for p in coords)+max(p['lat'] for p in coords))/2,
                       'lon':(min(p['lon'] for p in coords)+max(p['lon'] for p in coords))/2}
        if not cat or not isinstance(name, str) or normalized_name(name) in ('', 'unknown') or not ID.fullmatch(vid): continue
        if not valid_coordinates(point.get('lat'), point.get('lon')): continue
        outer, holes = polygons(element)
        venues.append({'venue_id': vid, 'venue_name': name.strip(), 'venue_category': cat,
                       'latitude': float(point['lat']), 'longitude': float(point['lon']),
                       'tags': tags, 'outer': outer, 'holes': holes,
                       'source': 'OpenStreetMap', 'source_url': f'https://www.openstreetmap.org/{vid}'})
    # Collapse a duplicate node/polygon only when category and identity agree,
    # the centres are within 30m, and a single physical venue is plausible.
    unique, identities = [], defaultdict(list)
    for venue in sorted(venues, key=lambda v: (not bool(v['outer']), v['venue_id'])):
        duplicate = False
        keys=[(venue['venue_category'],'name',normalized_name(venue['venue_name']))]
        if venue['tags'].get('wikidata'): keys.append((venue['venue_category'],'qid',venue['tags']['wikidata']))
        for other in (o for key in keys for o in identities[key]):
            same = (venue['tags'].get('wikidata') and venue['tags'].get('wikidata') == other['tags'].get('wikidata')) or normalized_name(venue['venue_name']) == normalized_name(other['venue_name'])
            if same and venue['venue_category'] == other['venue_category'] and abs(venue['latitude']-other['latitude']) < .001 and haversine_km(venue['latitude'],venue['longitude'],other['latitude'],other['longitude']) <= .03:
                duplicate = True
                break
        if not duplicate:
            unique.append(venue)
            for key in keys: identities[key].append(venue)
    return sorted(unique, key=lambda v: v['venue_id'])


def explicit_association(row, venue):
    tags = row.get('tags') or {}
    name = normalized_name(venue['venue_name'])
    # Generic operator/brand/name tags are not membership evidence.
    if normalized_name(tags.get('located_in', '')) == name: return 'Facility located_in tag names this venue.'
    if tags.get('located_in:wikidata') and tags['located_in:wikidata'] == venue['tags'].get('wikidata'):
        return 'Facility located_in:wikidata identifies this venue.'
    raw_name = normalized_name(row.get('name', ''))
    prefix = re.sub(r'^(toilet umum|toilets|toilet|wc)\s+(?:at\s+|di\s+)?', '', raw_name)
    if prefix != raw_name and prefix == name: return 'The source facility name explicitly names this venue.'
    return None


def match_venue(row, venues, timestamp):
    if not valid_coordinates(row.get('latitude'), row.get('longitude')): return None
    candidates = []
    for venue in venues:
        if row['facility_id'] == venue['venue_id']: continue
        lat, lon = venue['latitude'], venue['longitude']
        if abs(lat-row['latitude']) > .05 or abs(lon-row['longitude']) > .05: continue
        distance = haversine_km(row['latitude'], row['longitude'], lat, lon)*1000
        evidence = explicit_association(row, venue) if distance <= 1000 else None
        point = (row['longitude'], row['latitude'])
        contained = (row.get('osm_type') == 'node' and any(inside_ring(point, p) for p in venue['outer'])
                     and not any(inside_ring(point, p, boundary=True) for p in venue['holes']))
        if evidence: priority, relationship = 0, 'at'
        elif contained:
            priority, relationship, evidence = 1, 'inside', 'The mapped facility node lies within a complete venue boundary, outside mapped holes. This does not locate the entrance or establish public access.'
        elif distance <= LIMITS[venue['venue_category']]:
            priority, relationship, evidence = 2, 'near', 'Nearest unambiguous named venue within the category limit; straight-line distance to its mapped centre. Venue membership and entrance are not established.'
        else: continue
        candidates.append((priority, distance, venue, relationship, evidence))
    if not candidates: return None
    candidates.sort(key=lambda c: (c[0], c[1], c[2]['venue_id']))
    best = candidates[0]
    peers = [c for c in candidates[1:] if c[0] == best[0]]
    if peers and (best[0] < 2 or peers[0][1]-best[1] <= max(30, best[1]*.35)):
        return None
    priority, distance, venue, relationship, evidence = best
    return {k: venue[k] for k in ('venue_id','venue_name','venue_category','latitude','longitude','source','source_url')} | {
        'facility_id': row['facility_id'], 'relationship_type': relationship,
        'relationship_evidence': evidence, 'confidence': ('explicit','geometry','proximity')[priority],
        'distance_metres': round(distance,1), 'enrichment_timestamp': timestamp, 'photo': None}


def validate_cache(payload):
    if not isinstance(payload, dict) or payload.get('schema_version') != 1 or not isinstance(payload.get('records'), dict):
        raise ValueError('Invalid enrichment cache')
    for fid, context in payload['records'].items():
        if not ID.fullmatch(fid) or not isinstance(context, dict) or context.get('facility_id') != fid: raise ValueError('Invalid facility association')
        if context.get('venue_category') not in LIMITS or context.get('relationship_type') not in ('near','at','inside'): raise ValueError('Invalid venue relationship')
        if not isinstance(context.get('venue_name'), str) or not context['venue_name'].strip(): raise ValueError('Unnamed venue')
        if not ID.fullmatch(context.get('venue_id','')) or context.get('source_url') != f"https://www.openstreetmap.org/{context['venue_id']}": raise ValueError('Invalid venue source')
        if not valid_coordinates(context.get('latitude'), context.get('longitude')): raise ValueError('Invalid venue coordinates')
        d = context.get('distance_metres')
        if not isinstance(d,(int,float)) or not math.isfinite(d) or d < 0: raise ValueError('Invalid venue distance')
        if not context.get('relationship_evidence') or not context.get('enrichment_timestamp'): raise ValueError('Missing evidence')
    return payload


def load_cache(path=CACHE):
    try: return validate_cache(json.loads(Path(path).read_text(encoding='utf-8')))
    except (OSError, ValueError, TypeError, KeyError): return {'schema_version':1, 'records':{}, 'status':'unavailable'}


def relationship_label(context):
    return f"{context['relationship_type'].capitalize()} {context['venue_name']}"
