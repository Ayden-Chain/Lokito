from urllib.parse import parse_qs, urlsplit
from unittest.mock import Mock

import pytest

from facility_finder import community, google_map


def test_google_map_coordinates_and_embed_urls():
    point=(-6.1934514,106.8218829)
    url=google_map.map_url(point)
    assert urlsplit(url).netloc=='www.google.com'
    assert parse_qs(urlsplit(url).query)=={'api':['1'],'query':['-6.1934514,106.8218829']}
    embedded=google_map.embed_url(point,'public-test-key')
    assert '/maps/embed/v1/place?' in embedded
    assert parse_qs(urlsplit(embedded).query)['q']==['-6.1934514,106.8218829']
    with pytest.raises(ValueError): google_map.map_url((float('nan'),106.8))


def test_embed_uses_only_dedicated_browser_key_and_keeps_fallback(monkeypatch):
    markdown,link,caption,html=Mock(),Mock(),Mock(),Mock()
    for name,mock in [('markdown',markdown),('link_button',link),('caption',caption)]:
        monkeypatch.setattr(google_map.st,name,mock)
    monkeypatch.setattr(google_map.components,'html',html)
    monkeypatch.setenv('GOOGLE_MAPS_API_KEY','private-server-key-must-never-appear')
    monkeypatch.delenv('GOOGLE_MAPS_EMBED_API_KEY',raising=False)
    google_map.render_map((-6.2,106.8),'Test venue','Venue')
    html.assert_not_called()
    assert link.call_args.args[1]==google_map.map_url((-6.2,106.8))
    monkeypatch.setenv('GOOGLE_MAPS_EMBED_API_KEY','public-browser-key')
    google_map.render_map((-6.2,106.8),'<unsafe>','Venue')
    markup=html.call_args.args[0]
    assert 'public-browser-key' in markup and 'private-server-key' not in markup
    assert '&lt;unsafe&gt;' in markup and 'referrerpolicy="strict-origin-when-cross-origin"' in markup
    assert 'OpenStreetMap' not in markup
    assert link.call_count==2


def test_report_preview_does_not_create_database_or_expose_private_fields(tmp_path):
    db=tmp_path/'reports.sqlite3'
    assert community.preview_reports('node/1',db)==[] and not db.exists()
    community.add_report('node/1',{'node/1'},'yes',4,'PRIVATE phone 081234567890',db)
    community.add_report('node/1',{'node/1'},'no',1,'REJECTED',db)
    with community.connect(db) as conn:
        conn.execute("UPDATE reports SET moderation_status='rejected' WHERE report_id=2")
    preview=community.preview_reports('node/1',db)
    assert len(preview)==1
    assert set(preview[0])=={'submitted_at','available','cleanliness','moderation_status'}
    assert preview[0]['available']=='yes' and preview[0]['moderation_status']=='pending'
    assert 'PRIVATE' not in repr(preview) and '081234567890' not in repr(preview)
    assert community.preview_reports('node/2',db)==[]


def test_inline_preview_visible_without_opening_details(tmp_path,monkeypatch):
    from streamlit.testing.v1 import AppTest
    from pathlib import Path
    db=tmp_path/'preview.sqlite3'
    community.add_report('node/14140086914',{'node/14140086914'},'yes',4,'PRIVATE NOTE',db)
    real=community.preview_reports
    monkeypatch.setattr(community,'preview_reports',lambda fid:real(fid,db))
    at=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py')).run()
    assert not at.exception and at.session_state['detail_id'] is None
    markup=' '.join(m.value for m in at.markdown)
    assert 'Visitor could use the facility' in markup and 'Awaiting review' in markup
    assert 'PRIVATE NOTE' not in markup and 'Opens Google Maps' not in markup
    at.button(key='venue_way/538319726').click().run()
    assert at.session_state['focus_venue_id']=='way/538319726'
    assert not at.exception
    assert any('Plaza Indonesia' in m.value for m in at.markdown)
    assert at.session_state['selected_id']=='node/14140086914'
