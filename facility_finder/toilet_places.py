"""Places OSM records as having a toilet (toilets=yes) plus MRT stations.

Run from the project root: python -m facility_finder.toilet_places
Writes data/processed/toilet_places.json; the app works without it.
"""
from facility_finder.data import valid_coordinates
from facility_finder.ingest import RAW_DIR, ROOT, atomic_json, request_query

OUTPUT = ROOT / 'data' / 'processed' / 'toilet_places.json'
QUERY = '''[out:json][timeout:120];
area["ISO3166-2"="ID-JK"]["boundary"="administrative"]->.jakarta;
.jakarta out tags;
(nwr["toilets"="yes"]["amenity"!="toilets"](area.jakarta);
 nwr["railway"="station"]["station"="subway"](area.jakarta);
 nwr["railway"="station"]["network"~"MRT",i](area.jakarta););
out meta center;'''


def records(elements):
    """One row per named place; MRT stations are kept even without a toilets tag (Perda DKI requires toilets)."""
    rows = {}
    for element in elements:
        tags = element.get('tags', {})
        point = element if element.get('type') == 'node' else element.get('center', {})
        lat, lon = point.get('lat'), point.get('lon')
        name = (tags.get('name') or '').strip()
        if element.get('type') == 'area' or not name or not valid_coordinates(lat, lon):
            continue
        mrt = tags.get('station') == 'subway' or 'mrt' in tags.get('network', '').lower()
        access = tags.get('toilets:access', 'unknown')
        kind = 'mrt' if mrt else {'yes': 'tagged_open', 'permissive': 'tagged_open', 'customers': 'tagged_customers'}.get(access, 'tagged')
        place_id = f"{element['type']}/{element['id']}"
        rows[place_id] = {'place_id': place_id, 'name': name, 'latitude': lat, 'longitude': lon,
                          'kind': kind, 'access': access,
                          'wheelchair': tags.get('toilets:wheelchair', 'unknown'),
                          'fee': tags.get('toilets:fee', 'unknown'),
                          'level': tags.get('level', 'unknown'),
                          'source_url': f'https://www.openstreetmap.org/{place_id}'}
    return sorted(rows.values(), key=lambda r: r['place_id'])


def main():
    snapshot, name = request_query(QUERY, raw_dir=RAW_DIR / 'toilet-places')
    rows = records(snapshot['payload']['elements'])
    if not rows:
        raise SystemExit('No places returned; keeping the previous file.')
    atomic_json(OUTPUT, {'fetched_at': snapshot['fetched_at'], 'raw_snapshot': name, 'places': rows})
    print(f'{len(rows)} places written to {OUTPUT.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
