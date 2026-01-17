import streamlit as st
from google_auth_oauthlib.flow import Flow

SHEETS_SCOPE = ["https://www.googleapis.com/auth/spreadsheets"]

def sheets_login():
    if "sheets_credentials" in st.session_state:
        return st.session_state["sheets_credentials"]

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
        scopes=SHEETS_SCOPE,
        redirect_uri=st.secrets["google"]["redirect_uri"],
    )

    if "code" not in query_params:
        auth_url, _ = flow.authorization_url(
            access_type="offline",
            prompt="consent",
        )
        st.warning("Serve autorizzare Google Sheets")
        st.link_button("Autorizza Google Sheets", auth_url)
        st.stop()

    flow.fetch_token(code=query_params["code"])
    creds = flow.credentials

    st.session_state["sheets_credentials"] = creds
    st.query_params.clear()
    st.rerun()
