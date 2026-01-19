import streamlit as st
import requests
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

def google_login():
    # ✅ già loggato
    if "credentials" in st.session_state and "email" in st.session_state:
        return st.session_state["email"]

    query_params = st.query_params

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": st.secrets["google"]["client_id"],
                "client_secret": st.secrets["google"]["client_secret"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [st.secrets["google"]["redirect_uri"]],
            }
        },
        scopes=SCOPES,
        redirect_uri=st.secrets["google"]["redirect_uri"],
    )

    # 🔐 bottone login
    if "code" not in query_params:
        auth_url, _ = flow.authorization_url(
            access_type="offline",
            prompt="consent select_account",
        )
        st.link_button("🔐 Accedi con Google", auth_url)
        st.stop()

    # 🔁 code → token
    flow.fetch_token(code=query_params["code"])
    creds = flow.credentials

    # 👤 user info
    userinfo = requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {creds.token}"},
    ).json()

    # ✅ salva SOLO dati serializzabili
    st.session_state["credentials"] = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": creds.scopes,
    }
    st.session_state["email"] = userinfo["email"]
    st.session_state["picture"] = userinfo.get("picture")

    st.query_params.clear()
    st.rerun()

def get_credentials():
    if "credentials" not in st.session_state:
        return None

    data = st.session_state["credentials"]

    creds = Credentials(
        token=data["token"],
        refresh_token=data["refresh_token"],
        token_uri=data["token_uri"],
        client_id=data["client_id"],
        client_secret=data["client_secret"],
        scopes=data["scopes"],
    )

    # 🔄 refresh automatico
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        st.session_state["credentials"]["token"] = creds.token

    return creds

def logout():
    st.session_state.clear()
    st.rerun()
