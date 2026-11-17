"""Consumer-facing formatting and selection. Source records are never modified."""
import math
import re
from urllib.parse import urlencode

from facility_finder.data import clean_text, valid_coordinates, haversine_km

LABELS = {"toilets": "Toilet", "place_of_worship": "Tempat ibadah", "drinking_water": "Titik air minum"}
PLURALS = {"toilets": "toilet", "place_of_worship": "tempat ibadah", "drinking_water": "titik air minum"}


def known(value):
    return clean_text(value) != "unknown"


def facility_name(row):
    return str(row["name"]) if known(row.get("name")) else LABELS[row["facility_category"]]


def distance_parts(distance):
    """("810", "m") or ("1,2", "km"): Indonesian decimal comma, rounded to 10 m."""
    value = float(distance)
    if not math.isfinite(value) or value < 0:
        raise ValueError("Distance must be finite and nonnegative")
    if value < 1:
        return f"{round(value * 1000 / 10) * 10:.0f}", "m"
    return f"{value:.1f}".replace(".", ","), "km"


def distance_label(distance):
    number, unit = distance_parts(distance)
    return f"{number} {unit}"


def directions_url(row, origin=None):
    """A Google Maps handoff; no route or travel-time claim is made here."""
    lat, lon = row.get("latitude"), row.get("longitude")
    if not valid_coordinates(lat, lon):
        raise ValueError("Cannot make directions for invalid coordinates")
    params = {"api": "1", "destination": f"{float(lat):.7f},{float(lon):.7f}", "travelmode": "walking"}
    if origin is not None:
        if len(origin) != 2 or not valid_coordinates(*origin):
            raise ValueError("Invalid starting point")
        params["origin"] = f"{float(origin[0]):.7f},{float(origin[1]):.7f}"
    return "https://www.google.com/maps/dir/?" + urlencode(params)


def known_details(row):
    """Translate only understood values; retain unusual tags as source wording."""
    definitions = [
        ("access", "Akses", {"yes": "Terbuka untuk umum", "permissive": "Boleh dipakai umum",
          "customers": "Khusus pelanggan", "private": "Akses pribadi", "no": "Tidak untuk umum",
          "permit": "Perlu izin", "members": "Khusus anggota"}),
        ("fee", "Biaya", {"no": "Gratis", "yes": "Berbayar"}),
        ("wheelchair", "Kursi roda", {"yes": "Ramah kursi roda", "designated": "Ada akses kursi roda khusus",
          "limited": "Akses kursi roda terbatas", "no": "Tidak ramah kursi roda"}),
        ("opening_hours", "Jam buka", {}),
    ]
    details = []
    for field, label, values in definitions:
        value = row.get(field)
        if known(value):
            details.append((label, values.get(value, str(value)), field))
    return details


def unknown_summary(row, compact=False):
    fields = (("access", "akses"), ("fee", "biaya")) if compact else (
        ("access", "akses"), ("fee", "biaya"), ("opening_hours", "jam buka"), ("wheelchair", "akses kursi roda"))
    missing = [label for key, label in fields if not known(row.get(key))]
    if not missing:
        return ""
    words = missing[0] if len(missing) == 1 else ", ".join(missing[:-1]) + " dan " + missing[-1]
    return "Info " + words + " belum tersedia."


def selected_facility(ranked, selected_id=None):
    if ranked.empty:
        return None
    if selected_id in set(ranked.facility_id):
        return ranked[ranked.facility_id == selected_id].iloc[0].to_dict()
    return ranked.iloc[0].to_dict()


def map_view_for_selection(origin, row=None):
    """Fit the start and chosen place even in the compact 220px mobile map."""
    if row is None:
        return {"center": origin, "zoom": 15}
    distance = haversine_km(*origin, row['latitude'], row['longitude'])
    center = ((origin[0] + row['latitude']) / 2, (origin[1] + row['longitude']) / 2)
    # Close places get a street-level view; far ones still fit both points.
    zoom = max(2, min(16, 16 - math.ceil(math.log2(max(distance, .25) / .25))))
    return {"center": center, "zoom": zoom}


def marker_selection(event, displayed):
    """Resolve only IDs in the currently displayed results, including co-located objects."""
    if not event or not event.get("last_object_clicked"):
        return None
    # streamlit-folium returns popup text, not its HTML attributes. The visible
    # ordinal in the tooltip distinguishes separate OSM objects at one point.
    tooltip = event.get("last_object_clicked_tooltip") or ""
    if tooltip.strip().startswith('place:') or tooltip.strip() in ('Your starting point', 'Titik awalmu'):
        return None
    number = re.match(r"^(\d+)\. ", tooltip.strip())
    if number and "result_number" in displayed:
        numbered = displayed[displayed.result_number == int(number.group(1))]
        if len(numbered) == 1:
            return numbered.iloc[0].facility_id
    popup = event.get("last_object_clicked_popup") or ""
    if 'data-venue-id=' in popup:
        return None
    match = re.search(r'data-facility-id=[\"\']((?:node|way|relation)/[0-9]+)[\"\']', popup)
    if match and match.group(1) in set(displayed.facility_id):
        return match.group(1)
    # Popup data is not guaranteed by every streamlit-folium version.
    point = event["last_object_clicked"]
    if not valid_coordinates(point.get("lat"), point.get("lng")):
        return None
    matches = displayed[(displayed.latitude - float(point["lat"])).abs().lt(1e-7) &
                        (displayed.longitude - float(point["lng"])).abs().lt(1e-7)]
    return matches.iloc[0].facility_id if len(matches) == 1 else None


def new_click(event, last_stamp):
    """streamlit-folium keeps returning the last pin click; return a stamp only for a new one."""
    point = (event or {}).get("last_object_clicked")
    if not point:
        return None
    stamp = (event.get("last_object_clicked_tooltip"), point.get("lat"), point.get("lng"))
    return None if stamp == last_stamp else stamp
