"""Extra places with a toilet: OSM toilets=yes, MRT stations, and likely toilets
(malls, SPBU, hospitals, mosques).

These rows widen nearby coverage without claiming that a toilet was checked by
Lokito. Source records are never modified.
"""
import json
import re

import pandas as pd

from facility_finder.data import valid_coordinates
from facility_finder.toilet_places import OUTPUT as TOILET_PLACES

# Station names in the venue cache include TransJakarta stops without toilets,
# and Pertamini/Pertashop/Pommini are fuel kiosks without toilets, so they are left out.
CATEGORIES = ('mall', 'fuel', 'hospital')
EXCLUDED_NAMES = re.compile(r'pertamini|pertashop|pommini', re.I)
# Pertamina SPBU are named "Pertamina" or carry a 31-/34- station code.
PERTAMINA = re.compile(r'pertamina|\b3[14]\s*[-.\s]\s*\d{2}', re.I)
KIND = {'mall': 'Mall · biasanya ada toilet', 'fuel': 'SPBU · biasanya ada toilet',
        'fuel_pertamina': 'SPBU Pertamina · toilet seharusnya gratis', 'hospital': 'Rumah sakit · biasanya ada toilet',
        'mosque': 'Masjid/musala · biasanya ada toilet', 'tagged': 'Tercatat punya toilet',
        'tagged_open': 'Ada toilet · boleh dipakai umum', 'tagged_customers': 'Ada toilet · khusus pelanggan',
        'mrt': 'Stasiun MRT · ada toilet'}
NOTE = {'mosque': 'Masjid dan musala umumnya punya toilet dan tempat wudu yang terbuka. Jaga kebersihan dan lepas alas kaki di area suci.',
        'fuel_pertamina': 'Pertamina menetapkan toilet di SPBU-nya gratis, tapi di lapangan kadang masih ada yang memungut biaya.',
        'tagged': 'Data OpenStreetMap mencatat tempat ini punya toilet. Letak persisnya di dalam belum diketahui.',
        'tagged_open': 'Data OpenStreetMap mencatat tempat ini punya toilet yang boleh dipakai umum. Kalau ragu, minta izin ke kasir atau petugas.',
        'tagged_customers': 'Data OpenStreetMap mencatat toiletnya khusus pelanggan, jadi mungkin perlu membeli sesuatu.',
        'mrt': 'Perda DKI mewajibkan toilet di setiap stasiun MRT. Toiletnya bisa berada di dalam area berbayar, setelah gerbang tiket.'}
DEFAULT_NOTE = 'Mall, SPBU, dan rumah sakit umumnya punya toilet untuk pengunjung.'
FIELDS = ('access', 'fee', 'opening_hours', 'wheelchair', 'operator', 'changing_table', 'religion',
          'denomination', 'wheelchair:description', 'address')


def row(facility_id, category, name, lat, lon, source_url='', photo=None, **known):
    return {'facility_id': facility_id, 'facility_category': 'toilets', 'kind': 'venue',
            'venue_category': category, 'name': name, 'latitude': float(lat), 'longitude': float(lon),
            'source': 'OpenStreetMap', 'source_url': source_url, 'coordinate_method': 'venue',
            'verification_status': 'Not community verified', 'venue_context': None, 'photo': photo,
            **{field: 'unknown' for field in FIELDS}, **known}


def osm_id(facility_id):
    return facility_id.split(':', 1)[1]


def tagged_rows(path=TOILET_PLACES, catalog=None):
    """Places OSM records as having a toilet; empty until `python -m facility_finder.toilet_places` has run.
    Photos come from the venue catalog when the same OSM object is there (e.g. Plaza Indonesia)."""
    photos = {key: place.get('photo') for key, place in (catalog or {}).items()}
    try:
        places = json.loads(path.read_text(encoding='utf-8'))['places']
    except (OSError, ValueError, KeyError):
        return pd.DataFrame()
    return pd.DataFrame([row(f"tagged:{p['place_id']}", p['kind'], p['name'], p['latitude'], p['longitude'],
                             p.get('source_url', ''), photos.get(p['place_id']), wheelchair=p.get('wheelchair', 'unknown'), fee=p.get('fee', 'unknown'),
                             access=p.get('access', 'unknown'))
                         for p in places if valid_coordinates(p.get('latitude'), p.get('longitude'))])


def venue_rows(catalog, skip_venue_ids=()):
    """Return toilet-category rows for venues that usually offer a toilet."""
    skipped = set(skip_venue_ids)
    rows = []
    for place in (catalog or {}).values():
        if place.get('venue_category') not in CATEGORIES or place.get('venue_id') in skipped:
            continue
        name = str(place.get('venue_name') or '').strip()
        if not name or EXCLUDED_NAMES.search(name):
            continue
        if not valid_coordinates(place.get('latitude'), place.get('longitude')):
            continue
        category = 'fuel_pertamina' if place['venue_category'] == 'fuel' and PERTAMINA.search(name) else place['venue_category']
        rows.append(row(f"venue:{place['venue_id']}", category, name, place['latitude'], place['longitude'],
                        place.get('source_url', ''), place.get('photo')))
    return pd.DataFrame(rows)


def mosque_rows(mapped, skip_ids=()):
    """Mosques from the mapped worship data: the most common open toilet in Indonesian neighbourhoods."""
    skipped = set(skip_ids)
    mosques = mapped[(mapped.facility_category == 'place_of_worship') & (mapped.religion == 'muslim')]
    return pd.DataFrame([row(f"mosque:{m.facility_id}", 'mosque', m.name if m.name != 'unknown' else 'Masjid/musala',
                             m.latitude, m.longitude, m.source_url)
                         for m in mosques.itertuples() if m.facility_id not in skipped])


def is_venue(row):
    return row.get('kind') == 'venue'
