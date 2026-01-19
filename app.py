import streamlit as st
from auth import google_login, get_credentials, logout
from gmail import send_email
from sheets import get_clienti, get_articoli, crea_ordine
from datetime import datetime

st.set_page_config(page_title="Ordini Aziendali", page_icon="📦")
st.title("📦 Sistema Ordini Aziendali")

# --- Login ---
email = google_login()
credentials = get_credentials()

# 👤 header utente
col1, col2 = st.columns([1, 4])
with col1:
    if "picture" in st.session_state:
        st.image(st.session_state["picture"], width=64)
with col2:
    st.success(f"Loggato come {email}")
    if st.button("🚪 Logout"):
        logout()

st.divider()

# ===============================
# 1️⃣ Selezione cliente
clienti = get_clienti(credentials)
cliente_scelto = st.selectbox("Seleziona cliente", [c["Nome"] for c in clienti])

# ===============================
# 2️⃣ Aggiunta articoli
articoli = get_articoli(credentials)
ordine = []

st.subheader("Aggiungi articoli all'ordine")
num_righe = st.number_input("Quanti articoli vuoi aggiungere?", min_value=1, max_value=20, value=3)
for i in range(num_righe):
    col1, col2 = st.columns([3,1])
    with col1:
        articolo = st.selectbox(f"Articolo {i+1}", [a["Descrizione"] for a in articoli], key=f"art{i}")
    with col2:
        qty = st.number_input(f"Quantità {i+1}", min_value=0, key=f"qty{i}")
    if qty > 0:
        art = next(a for a in articoli if a["Descrizione"] == articolo)
        ordine.append({"IdArticolo": art["IdArticolo"], "Descrizione": articolo, "Quantita": qty})

# ===============================
# 3️⃣ Riepilogo ordine
if ordine:
    st.subheader("Riepilogo ordine")
    for item in ordine:
        st.write(f"{item['Descrizione']} x {item['Quantita']}")
    totale_articoli = sum([item['Quantita'] for item in ordine])
    st.write(f"**Totale articoli:** {totale_articoli}")

# ===============================
# 4️⃣ Invia ordine
if st.button("📧 Invia ordine"):
    if not ordine:
        st.warning("Devi aggiungere almeno un articolo!")
    else:
        # crea ordine su Google Sheets
        id_ordine = crea_ordine(credentials, email, cliente_scelto, ordine)

        # invia email a destinatario predefinito
        destinatario = "lucamantini2009@gmail.com"
        corpo_email = f"Ordine #{id_ordine} di {email} per cliente {cliente_scelto}:\n\n"
        for item in ordine:
            corpo_email += f"{item['Descrizione']} x {item['Quantita']}\n"

        send_email(credentials, destinatario, f"Nuovo ordine #{id_ordine}", corpo_email)

        st.success(f"Ordine #{id_ordine} inviato correttamente a {destinatario}!")
