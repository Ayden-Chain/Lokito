"""A "use my location" button: the browser asks for permission, Python gets the point."""
import streamlit as st

CSS = """
button{width:100%;min-height:46px;border:0;border-radius:10px;background:#A6422A;color:#fff;
  font:700 15px/1.2 "Source Sans Pro","Source Sans 3",system-ui,sans-serif;cursor:pointer;display:flex;
  align-items:center;justify-content:center;gap:8px}
button:hover{background:#84331F}
button:focus-visible{outline:3px solid #6B432E;outline-offset:3px}
button[disabled]{opacity:.75;cursor:progress}
"""

JS = """
export default function(component) {
  const { parentElement, setTriggerValue, data } = component;
  let button = parentElement.querySelector('button');
  if (!button) {
    button = document.createElement('button');
    button.type = 'button';
    parentElement.appendChild(button);
  }
  const label = (data && data.label) || 'Pakai lokasiku';
  const icon = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="7"/><circle cx="12" cy="12" r="2.5" fill="currentColor"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3"/></svg>';
  const idle = () => { button.innerHTML = icon + '<span></span>'; button.lastChild.textContent = label; };
  if (!button.disabled) idle();
  button.onclick = () => {
    if (!navigator.geolocation) { setTriggerValue('error', 'unsupported'); return; }
    button.disabled = true;
    button.textContent = 'Mencari lokasimu…';
    const done = () => { button.disabled = false; idle(); };
    navigator.geolocation.getCurrentPosition(
      (p) => { done(); setTriggerValue('position', {lat: p.coords.latitude, lon: p.coords.longitude, accuracy: p.coords.accuracy}); },
      (e) => { done(); setTriggerValue('error', e.code === 1 ? 'denied' : 'unavailable'); },
      {enableHighAccuracy: true, timeout: 12000, maximumAge: 60000});
  };
}
"""



def _register():
    return st.components.v2.component('lokito_locate', css=CSS, js=JS)


_button = _register()

ERRORS = {'denied': 'Izin lokasi ditolak. Aktifkan izin lokasi di browser, atau pilih titik awal secara manual.',
          'unavailable': 'Lokasimu belum bisa ditemukan. Coba lagi, atau pilih titik awal secara manual.',
          'unsupported': 'Browser ini tidak mendukung lokasi. Pilih titik awal secara manual.'}


def locate_button(label='Pakai lokasiku'):
    """Return (lat, lon) once the browser shares a position, else None."""
    global _button
    mount = dict(data={'label': label}, key='locate_me', on_position_change=lambda: None, on_error_change=lambda: None)
    try:
        result = _button(**mount)
    except st.errors.StreamlitAPIException:
        # Each Streamlit runtime keeps its own registry (e.g. a restarted server).
        _button = _register()
        result = _button(**mount)
    if result is None:
        return None
    error = getattr(result, 'error', None)
    if error:
        st.toast(ERRORS.get(error, ERRORS['unavailable']), icon=':material/location_off:')
    position = getattr(result, 'position', None)
    if isinstance(position, dict) and position.get('lat') is not None and position.get('lon') is not None:
        return float(position['lat']), float(position['lon'])
    return None
