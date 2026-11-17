"""Consumer journeys on the real cache; submissions use a temporary database."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


def widget(items, label):
    return next(item for item in items if item.label == label)


def app():
    return AppTest.from_file(str(ROOT / 'app.py'), default_timeout=30).run()


NEAREST_TOILET = 'node/14140086914'
PHOTO_TOILET = 'node/13447233704'


def select(at, facility_id):
    at.session_state['selected_id'] = facility_id
    return at.run()


def test_app_launch_categories_empty_results_and_location():
    at = app()
    assert not at.exception
    assert at.session_state['category'] == 'Toilets'
    # Plaza Indonesia is closer than any mapped toilet and is labelled as a likely toilet.
    assert at.session_state['selected_id'] == 'tagged:way/538319726'
    assert any('biasanya ada toilet' in m.value for m in at.markdown)
    assert not at.metric and not at.radio and not at.dataframe
    assert not at.sidebar.children
    for label, category in (('Tempat ibadah', 'Prayer spaces'), ('Air minum', 'Drinking water'), ('Toilet', 'Toilets')):
        widget(at.button, label).click().run()
        assert not at.exception and at.session_state['category'] == category
    widget(at.text_input, 'Nama atau jalan').set_value('nonexistent-facility-qa-xyz')
    widget(at.button, 'Terapkan').click().run()
    assert not at.exception and at.session_state['selected_id'] is None
    assert any('Belum ada yang cocok' in m.value for m in at.markdown)
    at.button(key='empty_clear').click().run()
    assert not at.exception and at.session_state['selected_id']
    widget(at.selectbox, 'Titik awal').set_value('Pilih di peta').run()
    widget(at.number_input, 'Latitude').set_value(0.0)
    widget(at.button, 'Pakai koordinat ini').click().run()
    assert any('luar Jakarta' in item.value for item in at.warning)
    assert at.session_state['origin'][0] == 0.0
    widget(at.checkbox, 'Gratis').check()
    widget(at.checkbox, 'Ramah kursi roda').check()
    widget(at.button, 'Terapkan').click().run()
    assert not at.exception
    assert at.session_state['free'] and at.session_state['wheelchair']


def test_choosing_map_mode_without_a_tap_does_not_crash_or_move_start():
    at = app()
    origin = at.session_state['origin']
    widget(at.selectbox, 'Titik awal').set_value('Pilih di peta').run()
    widget(at.button, 'Ketuk di peta').click().run()
    assert not at.exception and at.session_state['pick_on_map']
    assert at.session_state['origin'] == origin
    widget(at.button, 'Batal').click().run()
    assert not at.exception and not at.session_state['pick_on_map']


def test_preferences_leave_out_unchecked_venues():
    at = app()
    widget(at.checkbox, 'Gratis').check()
    widget(at.button, 'Terapkan').click().run()
    assert not at.exception
    assert not at.session_state['selected_id'].startswith('venue:')


def test_card_selection_and_nearest_reset():
    at = app()
    nearest = at.session_state['selected_id']
    option = next(b for b in at.button if b.label == 'Pilih nomor 3 →')
    fid = option.key.removeprefix('choose_')
    option.click().run()
    assert not at.exception and at.session_state['selected_id'] == fid
    assert any('Pilihanmu' in m.value for m in at.markdown)
    widget(at.button, 'Kembali ke yang terdekat').click().run()
    assert at.session_state['selected_id'] == nearest
    widget(at.button, 'Tampilkan lebih banyak').click().run()
    assert at.session_state['shown'] == 10
    widget(at.selectbox, 'Titik awal').set_value('Monas').run()
    widget(at.button, 'Gunakan lokasi ini').click().run()
    assert at.session_state['location'] == 'Monas'
    assert at.session_state['selected_id'] != nearest
    assert at.session_state['shown'] == 5


def test_evidence_navigation_retains_consumer_preferences():
    at = app()
    widget(at.checkbox, 'Gratis').check()
    widget(at.button, 'Terapkan').click().run()
    selected = at.session_state['selected_id']
    widget(at.button, 'Data').click().run()
    assert not at.exception and at.dataframe
    widget(at.button, 'Tentang').click().run()
    assert not at.exception and not at.dataframe
    widget(at.button, '← Kembali').click().run()
    assert at.session_state['free'] and at.session_state['selected_id'] == selected
    assert widget(at.checkbox, 'Gratis').value


def test_local_observation_ui_isolated_from_real_database(tmp_path, monkeypatch):
    import facility_finder.community as community
    real_add, real_list = community.add_report, community.list_reports
    db = tmp_path / 'test-reports.sqlite3'
    monkeypatch.setattr(community, 'add_report', lambda *args, **kwargs: real_add(*args, **kwargs, path=db))
    monkeypatch.setattr(community, 'list_reports', lambda *args, **kwargs: real_list(*args, **kwargs, path=db))
    at = select(app(), NEAREST_TOILET)
    widget(at.button, 'Detail').click().run()
    assert not at.exception
    widget(at.button, 'Simpan laporan').click().run()
    assert any('Isi laporan' in w.value for w in at.warning)
    widget(at.selectbox, 'Apakah toiletnya bisa dipakai?').set_value('Ya')
    widget(at.text_area, 'Apa yang perlu diketahui orang lain?').set_value('TEST ONLY: isolated temporary database')
    widget(at.button, 'Simpan laporan').click().run()
    assert not at.exception
    assert any('menunggu ditinjau' in item.value for item in at.success)
    rows = real_list(at.session_state['selected_id'], path=db)
    assert len(rows) == 1 and rows[0]['moderation_status'] == 'pending'
    assert rows[0]['available'] == 'yes' and rows[0]['cleanliness'] is None


def test_venue_details_offer_directions_but_no_reports():
    at = app()
    widget(at.button, 'Detail').click().run()
    assert not at.exception
    assert not any(b.label == 'Simpan laporan' for b in at.button)
    assert any('tanyakan ke petugas' in m.value for m in at.markdown)
    # Plaza Indonesia has a Wikimedia photo; it shows on the card and in details.
    assert any('Wikimedia Commons' in m.value for m in at.markdown)


def test_accuracy_confirmation_does_not_infer_availability(tmp_path, monkeypatch):
    import facility_finder.community as community
    real_add, real_list = community.add_report, community.list_reports
    db = tmp_path / 'confirmation.sqlite3'
    monkeypatch.setattr(community, 'add_report', lambda *args, **kwargs: real_add(*args, **kwargs, path=db))
    monkeypatch.setattr(community, 'list_reports', lambda *args, **kwargs: real_list(*args, **kwargs, path=db))
    at = select(app(), NEAREST_TOILET)
    widget(at.button, 'Detail').click().run()
    widget(at.button, 'Ya, infonya akurat').click().run()
    assert not at.exception
    rows = real_list(at.session_state['selected_id'], path=db)
    assert len(rows) == 1 and rows[0]['available'] == 'unknown'
    assert rows[0]['reviewed_at'] is None and rows[0]['moderation_status'] == 'pending'


def test_product_feedback_and_private_summary(tmp_path,monkeypatch):
    from facility_finder.feedback import summary
    db=tmp_path/'feedback.sqlite3'
    monkeypatch.setenv('LOKITO_FEEDBACK_DB',str(db))
    monkeypatch.setenv('LOKITO_OWNER_PASSWORD','synthetic-owner-test-pässword')
    at=select(app(),NEAREST_TOILET)
    widget(at.button,'Bantu kembangkan Lokito').click().run()
    widget(at.button,'Send feedback').click().run()
    assert at.warning and not db.exists()
    widget(at.selectbox,'Was it easy to find a suitable toilet?').set_value('Partly')
    widget(at.selectbox,'Did you understand where the toilet was located?').set_value('Yes')
    widget(at.selectbox,'Was the venue information useful?').set_value('Yes')
    widget(at.text_area,'What was confusing or missing?').set_value('TEST ONLY: PRIVATE COMMENT')
    widget(at.button,'Send feedback').click().run()
    assert not at.exception and at.success and summary(db)['total']==1
    at.run(); assert summary(db)['total']==1
    widget(at.button,'Data').click().run()
    assert not any('PRIVATE COMMENT' in t.value for t in at.text)
    widget(at.text_input,'Owner password').set_value('synthetic-owner-test-pässword')
    widget(at.button,'Unlock results').click().run()
    assert not at.exception and any('PRIVATE COMMENT' in t.value for t in at.text)
    from facility_finder.feedback import export_csv
    assert b'PRIVATE COMMENT' in export_csv(db,'product_feedback')
    widget(at.button,'Lock results').click().run()
    assert not any('PRIVATE COMMENT' in t.value for t in at.text)


def test_real_photo_context_and_missing_cache_ui(monkeypatch):
    import facility_finder.enrichment as en
    at=select(app(),PHOTO_TOILET)
    assert not at.exception and any('Wikimedia Commons' in m.value for m in at.markdown)
    monkeypatch.setattr(en,'load_cache',lambda *a,**k:{'schema_version':1,'records':{}})
    import streamlit as st
    st.cache_data.clear()
    at=app()
    assert not at.exception and at.session_state['discovery_context']['venue_shown'] is False
    assert not at.session_state['discovery_context']['photo_shown']
    at=select(at,NEAREST_TOILET)
    widget(at.button,'Detail').click().run()
    assert any('Belum ada keterangan lokasi' in c.value for c in at.caption)
    st.cache_data.clear()
