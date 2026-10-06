"""Lokito's numbered, keyboard-focusable markers and compact consumer popups."""
from html import escape

import folium
from folium.plugins import MarkerCluster

from facility_finder.presentation import facility_name, known_details, unknown_summary, directions_url, map_view_for_selection
from facility_finder.venue_ui import display_title

MAP_CSS = """
<style>
html,body{margin:0!important;padding:0!important;height:100%!important}
.folium-map,.leaflet-container{height:100vh!important;background:#ECE7DF;font-family:system-ui,sans-serif}
.leaflet-tile-pane{filter:saturate(.12) sepia(.12)}
.lokito-marker{background:transparent!important;border:0!important}
.lokito-pin{width:32px;height:32px;border:2px solid #A6422A;border-radius:50% 50% 50% 8px;transform:rotate(-45deg);background:#FFFDFA;box-shadow:0 2px 7px #44302030;display:flex;align-items:center;justify-content:center}
.lokito-pin span{transform:rotate(45deg);font-size:12px;font-weight:750;color:#8C3723}
.lokito-pin.selected{background:#A6422A;border-color:#FFFDFA;outline:2px solid #A6422A;width:38px;height:38px}.lokito-pin.selected span{color:white}
.lokito-origin{width:16px;height:16px;background:#292622;border:3px solid white;border-radius:50%;box-shadow:0 0 0 7px #29262218}
.lokito-cluster{border:1px solid #AA7967;background:#EDE0D3;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:12px;color:#654536;font-weight:700}
.leaflet-marker-icon:focus-visible,.leaflet-control a:focus-visible{outline:3px solid #292622!important;outline-offset:5px}
.leaflet-popup-content-wrapper{border-radius:14px}.leaflet-popup-content{margin:16px 19px;color:#292622;line-height:1.5}
.leaflet-popup-content h3{font-size:17px;margin:0 0 6px;line-height:1.3;overflow-wrap:anywhere}.leaflet-popup-content p{margin:6px 0;font-size:12px}
.leaflet-popup-content a.lokito-directions{display:block;background:#A6422A;color:white;text-decoration:none;text-align:center;padding:11px 12px;margin-top:12px;border-radius:8px;font-weight:600;font-size:13px}
.leaflet-control-zoom{border:1px solid #D5CCBF!important;box-shadow:none!important;border-radius:9px!important;overflow:hidden}
.leaflet-control-zoom a{color:#292622!important;background:#FFFDFA!important;width:44px!important;height:44px!important;line-height:44px!important}
.leaflet-control-attribution{font-size:9px!important;max-width:100%;white-space:normal}
</style>
"""


def popup_html(row, origin=None):
    title = escape(display_title(row))
    details = known_details(row)
    lines = ''.join(f'<p>{escape(value)}</p>' for _, value, _ in details[:3])
    missing = unknown_summary(row, compact=True)
    if missing:
        lines += f'<p style="color:#706458">{escape(missing)}</p>'
    return (f'<div data-facility-id="{escape(row["facility_id"], quote=True)}" style="min-width:180px;max-width:250px">'
            f'<h3>{title}</h3>{lines}<p style="font-size:10px;color:#766D62">Availability unknown · Not verified by Lokito</p>'
            f'<a class="lokito-directions" href="{escape(directions_url(row, origin), quote=True)}" '
            'target="_blank" rel="noopener noreferrer">Open directions ↗</a>'
            '<p style="font-size:10px;color:#766D62;text-align:center">Opens Google Maps</p></div>')


def build_map(df, origin, selected_id=None):
    selected_rows = df[df.facility_id == selected_id] if selected_id else df.iloc[:0]
    initial = map_view_for_selection(origin, selected_rows.iloc[0].to_dict() if len(selected_rows) else None)
    map_ = folium.Map(location=initial['center'], zoom_start=initial['zoom'], tiles="OpenStreetMap", control_scale=False,
                      prefer_canvas=True, scroll_wheel_zoom=True, touch_zoom=True,
                      double_click_zoom=True, zoom_control=True)
    map_.get_root().header.add_child(folium.Element(MAP_CSS))
    folium.Marker(origin, tooltip="Your starting point", title="Your starting point",
                  icon=folium.DivIcon(html='<div class="lokito-origin"></div>', icon_size=(16, 16),
                                      icon_anchor=(8, 8), class_name="lokito-marker")).add_to(map_)
    cluster = MarkerCluster(name="Nearby facilities", options={"disableClusteringAtZoom": 16},
        icon_create_function="""function(cluster){return L.divIcon({html:String(cluster.getChildCount()),className:'lokito-cluster',iconSize:L.point(38,38)});} """).add_to(map_)
    for i, row in enumerate(df.to_dict("records"), 1):
        number = int(row.get("result_number", i))
        selected = row["facility_id"] == selected_id
        label = f'{number}. {display_title(row)}' + (' · Selected' if selected else '')
        icon_html = f'<div class="lokito-pin{" selected" if selected else ""}"><span>{number}</span></div>'
        marker = folium.Marker([row["latitude"], row["longitude"]], title=escape(label),
            tooltip=escape(label), keyboard=True, z_index_offset=1000 if selected else 0,
            icon=folium.DivIcon(html=icon_html, icon_size=(40, 44), icon_anchor=(18, 36), class_name="lokito-marker"),
            popup=folium.Popup(popup_html(row, origin), max_width=280))
        marker.add_to(map_ if selected else cluster)
    return map_
