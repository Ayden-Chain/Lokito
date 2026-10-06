"""Consumer journeys on the real cache; submissions use a temporary database."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


def widget(items, label):
    return next(item for item in items if item.label == label)


def app():
    return AppTest.from_file(str(ROOT / 'app.py'), default_timeout=30).run()


def test_app_launch_categories_empty_results_and_location():
    at = app()
    assert not at.exception
    assert at.session_state['category'] == 'Toilets'
    assert at.session_state['selected_id'] == 'node/14140086914'
    assert not at.metric and not at.radio and not at.dataframe
    assert not at.sidebar.children
    for category in ('Prayer spaces', 'Drinking water', 'Toilets'):
        widget(at.button, category).click().run()
        assert not at.exception and at.session_state['category'] == category
    widget(at.text_input, 'Name or street').set_value('nonexistent-facility-qa-xyz')
    widget(at.button, 'Apply preferences').click().run()
    assert not at.exception and at.session_state['selected_id'] is None
    assert any('No matches just yet' in m.value for m in at.markdown)
    at.button(key='empty_clear').click().run()
    assert not at.exception and at.session_state['selected_id']
    widget(at.selectbox, 'Starting point').set_value('Custom point').run()
    widget(at.number_input, 'Latitude').set_value(0.0)
    widget(at.button, 'Use this location').click().run()
    assert any('outside' in item.value for item in at.warning)
    assert at.session_state['origin'][0] == 0.0
    widget(at.checkbox, 'Free to use').check()
    widget(at.checkbox, 'Wheelchair accessible').check()
    widget(at.button, 'Apply preferences').click().run()
    assert not at.exception
    assert at.session_state['free'] and at.session_state['wheelchair']


def test_card_selection_and_nearest_reset():
    at = app()
    nearest = at.session_state['selected_id']
    option = next(b for b in at.button if b.label == 'Show option 3 on map →')
    fid = option.key.removeprefix('choose_')
    option.click().run()
    assert not at.exception and at.session_state['selected_id'] == fid
    assert any('Your selected option' in m.value for m in at.markdown)
    widget(at.button, 'Back to nearest option').click().run()
    assert at.session_state['selected_id'] == nearest
    widget(at.button, 'Show more nearby').click().run()
    assert at.session_state['shown'] == 10
    widget(at.selectbox, 'Starting point').set_value('Monas').run()
    widget(at.button, 'Use this location').click().run()
    assert at.session_state['location'] == 'Monas'
    assert at.session_state['selected_id'] != nearest
    assert at.session_state['shown'] == 5


def test_evidence_navigation_retains_consumer_preferences():
    at = app()
    widget(at.checkbox, 'Free to use').check()
    widget(at.button, 'Apply preferences').click().run()
    selected = at.session_state['selected_id']
    widget(at.button, 'Data & trust').click().run()
    assert not at.exception and at.dataframe
    widget(at.button, 'About').click().run()
    assert not at.exception and not at.dataframe
    widget(at.button, '← Back to nearby').click().run()
    assert at.session_state['free'] and at.session_state['selected_id'] == selected
    assert widget(at.checkbox, 'Free to use').value


def test_local_observation_ui_isolated_from_real_database(tmp_path, monkeypatch):
    import facility_finder.community as community
    real_add, real_list = community.add_report, community.list_reports
    db = tmp_path / 'test-reports.sqlite3'
    monkeypatch.setattr(community, 'add_report', lambda *args, **kwargs: real_add(*args, **kwargs, path=db))
    monkeypatch.setattr(community, 'list_reports', lambda *args, **kwargs: real_list(*args, **kwargs, path=db))
    at = app()
    widget(at.button, 'View details').click().run()
    assert not at.exception
    widget(at.button, 'Save observation').click().run()
    assert any('Add an observation' in w.value for w in at.warning)
    widget(at.selectbox, 'Could you use the facility?').set_value('Yes')
    widget(at.text_area, 'What should others know?').set_value('TEST ONLY: isolated temporary database')
    widget(at.button, 'Save observation').click().run()
    assert not at.exception
    assert any('awaiting review' in item.value for item in at.success)
    rows = real_list(at.session_state['selected_id'], path=db)
    assert len(rows) == 1 and rows[0]['moderation_status'] == 'pending'
    assert rows[0]['available'] == 'yes' and rows[0]['cleanliness'] is None


def test_accuracy_confirmation_does_not_infer_availability(tmp_path, monkeypatch):
    import facility_finder.community as community
    real_add, real_list = community.add_report, community.list_reports
    db = tmp_path / 'confirmation.sqlite3'
    monkeypatch.setattr(community, 'add_report', lambda *args, **kwargs: real_add(*args, **kwargs, path=db))
    monkeypatch.setattr(community, 'list_reports', lambda *args, **kwargs: real_list(*args, **kwargs, path=db))
    at = app()
    widget(at.button, 'View details').click().run()
    widget(at.button, 'Yes, details were accurate').click().run()
    assert not at.exception
    rows = real_list(at.session_state['selected_id'], path=db)
    assert len(rows) == 1 and rows[0]['available'] == 'unknown'
    assert rows[0]['reviewed_at'] is None and rows[0]['moderation_status'] == 'pending'


def test_product_feedback_and_private_summary(tmp_path,monkeypatch):
    from facility_finder.feedback import summary
    db=tmp_path/'feedback.sqlite3'
    monkeypatch.setenv('LOKITO_FEEDBACK_DB',str(db))
    monkeypatch.setenv('LOKITO_OWNER_PASSWORD','synthetic-owner-test-pässword')
    at=app()
    widget(at.button,'Help improve Lokito').click().run()
    widget(at.button,'Send feedback').click().run()
    assert at.warning and not db.exists()
    widget(at.selectbox,'Was it easy to find a suitable toilet?').set_value('Partly')
    widget(at.selectbox,'Did you understand where the toilet was located?').set_value('Yes')
    widget(at.selectbox,'Was the venue information useful?').set_value('Yes')
    widget(at.text_area,'What was confusing or missing?').set_value('TEST ONLY: PRIVATE COMMENT')
    widget(at.button,'Send feedback').click().run()
    assert not at.exception and at.success and summary(db)['total']==1
    at.run(); assert summary(db)['total']==1
    widget(at.button,'Data & trust').click().run()
    assert not any('PRIVATE COMMENT' in t.value for t in at.text)
    widget(at.text_input,'Owner password').set_value('synthetic-owner-test-pässword')
    widget(at.button,'Unlock results').click().run()
    assert not at.exception and any('PRIVATE COMMENT' in t.value for t in at.text)
    widget(at.button,'Lock results').click().run()
    assert not any('PRIVATE COMMENT' in t.value for t in at.text)


def test_real_photo_context_and_missing_cache_ui(monkeypatch):
    import facility_finder.enrichment as en
    at=app()
    widget(at.button,'Show option 4 on map →').click().run()
    assert not at.exception and any('Wikimedia Commons' in m.value for m in at.markdown)
    monkeypatch.setattr(en,'load_cache',lambda *a,**k:{'schema_version':1,'records':{}})
    import streamlit as st
    st.cache_data.clear()
    at=app()
    assert not at.exception and at.session_state['discovery_context']['venue_shown'] is False
    assert not at.session_state['discovery_context']['photo_shown']
    widget(at.button,'View details').click().run()
    assert any('No reliable venue association' in c.value for c in at.caption)
    st.cache_data.clear()
