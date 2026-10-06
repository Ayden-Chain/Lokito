"""Interactive map with escaped OSM text and explicit unknown attributes."""
from html import escape

import folium
from folium.plugins import MarkerCluster

from facility_finder.data import CATEGORY_LABELS, display_name

COLORS = {"toilets": "#087F75", "place_of_worship": "#7359C4", "drinking_water": "#267ABF"}


def popup_html(row):
    fields = [("Need", CATEGORY_LABELS[row["facility_category"]]), ("Access", row.get("access", "unknown")),
              ("Fee", row.get("fee", "unknown")), ("Opening hours", row.get("opening_hours", "unknown")),
              ("Wheelchair", row.get("wheelchair", "unknown")), ("Religion", row.get("religion", "unknown")),
              ("Availability now", "Unknown"), ("Community verification", "Not verified"),
              ("Source", "OpenStreetMap")]
    lines = "".join(f'<div style="margin:5px 0"><b>{escape(label)}:</b> {escape(str(value))}</div>' for label, value in fields)
    return (f'<div style="min-width:220px;font-family:system-ui;font-size:13px">'
            f'<h3 style="font-size:16px;margin:0 0 10px">{escape(display_name(row))}</h3>{lines}'
            f'<small>{escape(row["facility_id"])} · OSM tags, not live status</small></div>')


def build_map(df, origin, selected_id=None):
    map_ = folium.Map(location=origin, zoom_start=13, tiles="OpenStreetMap", control_scale=True,
                      prefer_canvas=True)
    folium.Marker(origin, tooltip="Your selected approximate location",
                  icon=folium.Icon(color="darkblue", icon="user")).add_to(map_)
    cluster = MarkerCluster(name="Matching facilities", options={"disableClusteringAtZoom": 17}).add_to(map_)
    for row in df.to_dict("records"):
        selected = row["facility_id"] == selected_id
        folium.CircleMarker(
            [row["latitude"], row["longitude"]], radius=10 if selected else 7,
            color="#172B3A" if selected else COLORS[row["facility_category"]],
            weight=3 if selected else 1, fill=True,
            fill_color=COLORS[row["facility_category"]], fill_opacity=0.9,
            tooltip=escape(display_name(row)), popup=folium.Popup(popup_html(row), max_width=330),
        ).add_to(cluster)
    if len(df):
        bounds = [[float(df.latitude.min()), float(df.longitude.min())],
                  [float(df.latitude.max()), float(df.longitude.max())], list(origin)]
        map_.fit_bounds(bounds, padding=(30, 30), max_zoom=15)
    return map_
