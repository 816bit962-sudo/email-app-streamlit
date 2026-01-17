import gspread
from google.oauth2.credentials import Credentials
import streamlit as st

def get_user_rows():
    creds = st.session_state["credentials"]

    credentials = Credentials(
        token=creds.token,
        refresh_token=creds.refresh_token,
        token_uri=creds.token_uri,
        client_id=creds.client_id,
        client_secret=creds.client_secret,
        scopes=creds.scopes,
    )

    gc = gspread.authorize(credentials)
    sh = gc.open_by_key("1YHWrkehjx5qAuAWuNbNJye8zUO0vgjFahzPQS-FxaiM")

    worksheet = sh.sheet1

    rows = worksheet.get_all_records()
    user_email = st.session_state["email"]

    return [r for r in rows if r["owner_email"] == user_email]
