import streamlit as st
from auth import google_login, get_credentials, logout
from gmail import send_email

st.set_page_config(page_title="Email App", page_icon="📧")

st.title("📧 Email App")

email = google_login()
credentials = get_credentials()

# 👤 HEADER UTENTE
col1, col2 = st.columns([1, 4])

with col1:
    if "picture" in st.session_state:
        st.image(st.session_state["picture"], width=64)

with col2:
    st.success(f"Loggato come {email}")
    if st.button("Logout"):
        logout()

st.divider()

to = st.text_input("Destinatario")
subject = st.text_input("Oggetto")
body = st.text_area("Messaggio")

if st.button("Invia email"):
    if not to or not subject or not body:
        st.warning("Compila tutti i campi")
    else:
        send_email(credentials, to, subject, body)
        st.success("✅ Email inviata!")
