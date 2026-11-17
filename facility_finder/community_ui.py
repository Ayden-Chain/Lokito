"""Public structured observations only; private notes and identities stay private."""
import sqlite3
from html import escape

import streamlit as st

from facility_finder import community


def render_report_preview(facility_id, quiet=False):
    """quiet=True shows nothing unless there are reports, keeping result cards short."""
    try:
        reports = community.preview_reports(facility_id)
    except (OSError, sqlite3.Error):
        if not quiet:
            st.caption('Laporan pengunjung sedang tidak tersedia.')
        return
    if not reports:
        if not quiet:
            st.markdown('**Laporan pengunjung**')
            st.caption('Belum ada laporan pengunjung. Kamu bisa menambahkannya di bagian bawah detail ini.')
        return
    st.markdown('**Laporan pengunjung**')
    labels = {'yes': 'Pengunjung bisa memakai toiletnya', 'no': 'Pengunjung tidak bisa memakai toiletnya',
              'unknown': 'Ketersediaan tidak dicek'}
    for report in reports:
        status = 'Sudah ditinjau' if report['moderation_status'] == 'accepted' else 'Menunggu tinjauan'
        cleanliness = report['cleanliness']
        rating = f'Kebersihan: {cleanliness}/5' if cleanliness is not None else 'Kebersihan tidak dinilai'
        st.markdown(f'<div class="report-note"><small>{escape(report["submitted_at"][:10])} · {status}</small>'
                    f'<p>{labels.get(report["available"], labels["unknown"])}</p><small>{rating}</small></div>',
                    unsafe_allow_html=True)
    st.caption('Laporan pengunjung sebelumnya, bukan ketersediaan saat ini atau verifikasi Lokito. Catatan tertulis tetap privat untuk ditinjau.')
