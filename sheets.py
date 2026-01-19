import streamlit as st
import gspread
from google.oauth2.credentials import Credentials

def get_user_rows():
    data = st.session_state["credentials"]

    credentials = Credentials(
        token=data["token"],
        refresh_token=data["refresh_token"],
        token_uri=data["token_uri"],
        client_id=data["client_id"],
        client_secret=data["client_secret"],
        scopes=data["scopes"],
    )

    gc = gspread.authorize(credentials)
    sh = gc.open_by_key("1YHWrkehjx5qAuAWuNbNJye8zUO0vgjFahzPQS-FxaiM")
    ws = sh.sheet1

    rows = ws.get_all_records()
    user_email = st.session_state["email"]

    return [r for r in rows if r["owner_email"] == user_email]
