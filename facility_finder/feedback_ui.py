"""Research form and owner-gated results. No automatic telemetry."""
import hmac
import os
import secrets
import sqlite3
import time

import streamlit as st

from facility_finder import feedback


def render_form(context, valid_ids):
    st.title('Help improve Lokito')
    st.write('Tell us how finding a toilet felt. This is feedback about the app; report a facility change from its details instead.')
    st.caption('Feedback is stored locally for product testing. Please do not include personal information.')
    st.caption('“Locally” means the computer running Lokito. If you use a hosted version, the owner stores the responses on that server.')
    if st.session_state.get('feedback_saved'):
        st.success('Thank you. Your feedback is saved for the Lokito team.')
        return
    st.session_state.setdefault('feedback_token',secrets.token_hex(16))
    with st.form('product_feedback'):
        ease=st.selectbox('Was it easy to find a suitable toilet?',feedback.ANSWERS,index=None,placeholder='Choose an answer')
        understanding=st.selectbox('Did you understand where the toilet was located?',feedback.ANSWERS,index=None,placeholder='Choose an answer')
        venue=st.selectbox('Was the venue information useful?',feedback.USEFUL,index=None if context.get('venue_shown') else 2,disabled=not context.get('venue_shown'))
        photo=st.selectbox('Was the photo useful?',feedback.USEFUL,index=None if context.get('photo_shown') else 2,disabled=not context.get('photo_shown'))
        comment=st.text_area('What was confusing or missing?',max_chars=1500)
        score=st.selectbox('Overall experience · optional',[1,2,3,4,5],index=None,placeholder='Leave blank or choose 1–5',help='1 = very difficult; 5 = very easy')
        tester=st.selectbox('Tester type',feedback.TESTERS,index=5)
        if st.form_submit_button('Send feedback',type='primary'):
            try:
                feedback.submit({'ease':ease,'location_understanding':understanding,'venue_usefulness':venue,
                                 'photo_usefulness':photo,'comment':comment,'score':score,'tester_type':tester},
                                context,valid_ids,st.session_state.feedback_token)
                st.session_state.feedback_saved=True
                st.rerun()
            except ValueError as exc: st.warning(str(exc))
            except (OSError,sqlite3.Error): st.error('Feedback could not be saved. Please try again.')


def authorized():
    secret=os.environ.get('LOKITO_OWNER_PASSWORD','')
    proof=st.session_state.get('owner_proof','')
    expected=hmac.digest(secret.encode(),b'lokito-owner-results','sha256').hex() if secret else ''
    return bool(secret and proof and hmac.compare_digest(proof,expected))


def render_owner():
    with st.expander('Owner · private feedback results'):
        secret=os.environ.get('LOKITO_OWNER_PASSWORD','')
        if not secret:
            st.caption('Owner access has not been configured. Results remain hidden.')
            return
        if not authorized():
            with st.form('owner_access'):
                password=st.text_input('Owner password',type='password',key='owner_password')
                submitted=st.form_submit_button('Unlock results')
            if submitted:
                if time.monotonic()<st.session_state.get('owner_retry_at',0):
                    st.warning('Please wait a moment before trying again.')
                elif hmac.compare_digest(password,secret):
                    st.session_state.owner_proof=hmac.digest(secret.encode(),b'lokito-owner-results','sha256').hex()
                    st.rerun()
                else:
                    st.session_state.owner_retry_at=time.monotonic()+5
                    st.warning('The password did not match.')
            return
        if st.button('Lock results'):
            st.session_state.pop('owner_proof',None)
            st.session_state.pop('owner_password',None)
            st.rerun()
        try: result=feedback.summary()
        except (OSError,sqlite3.Error):
            st.error('Feedback results could not be loaded.')
            return
        st.write(f"{result['total']} feedback submissions")
        if result['average_score'] is not None: st.write(f"Average optional score: {result['average_score']:.1f}/5 · {result['scored']} scored responses")
        for key,counts in result['distributions'].items():
            st.write(key.replace('_',' ').capitalize())
            st.dataframe([{'Answer':a,'Responses':n} for a,n in counts.items()],hide_index=True)
        if result['comments']:
            st.write('Recent written feedback · owner only')
            for item in result['comments']:
                st.caption(item['submitted_at'][:10])
                st.text(item['comment'])
