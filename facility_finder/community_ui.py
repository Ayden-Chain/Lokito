"""Public structured observations only; private notes and identities stay private."""
import sqlite3
from html import escape

import streamlit as st

from facility_finder import community


def render_report_preview(facility_id):
    st.markdown('**Visitor reports**')
    try:
        reports = community.preview_reports(facility_id)
    except (OSError, sqlite3.Error):
        st.caption('Visitor reports are temporarily unavailable.')
        return
    if not reports:
        st.caption('No visitor reports yet. You can add an observation in facility details.')
        return
    labels = {'yes': 'Visitor could use the facility', 'no': 'Visitor could not use the facility',
              'unknown': 'Availability was not checked'}
    for report in reports:
        status = 'Reviewed report' if report['moderation_status'] == 'accepted' else 'Awaiting review'
        cleanliness = report['cleanliness']
        rating = f'Reported cleanliness: {cleanliness}/5' if cleanliness is not None else 'Cleanliness not assessed'
        st.markdown(f'<div class="report-note"><small>{escape(report["submitted_at"][:10])} · {status}</small>'
                    f'<p>{labels.get(report["available"], labels["unknown"])}</p><small>{rating}</small></div>',
                    unsafe_allow_html=True)
    st.caption('Past visitor observations, not current availability or Lokito verification. Written notes remain private for review.')
