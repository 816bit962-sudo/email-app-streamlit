import streamlit as st
from auth import google_login, get_credentials, logout
from gmail import send_email
from sheets import get_clienti, get_articoli, crea_ordine
from datetime import datetime
import uuid

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
# Caching per evitare troppi accessi a Google Sheets
@st.cache_data(ttl=300)
def load_clienti(_credentials):
    return get_clienti(_credentials)

@st.cache_data(ttl=300)
def load_articoli(_credentials):
    return get_articoli(_credentials)

# ===============================
# 1️⃣ Selezione cliente
try:
    clienti = load_clienti(credentials)
except Exception as e:
    st.error("❌ Errore nel leggere i clienti dal foglio Google Sheets!")
    st.error(f"Dettaglio errore: {e}")
    st.stop()

if not clienti:
    st.warning("⚠️ Nessun cliente trovato!")
    st.stop()

cliente_scelto = st.selectbox("Seleziona cliente", [c["Nome"] for c in clienti])

# ===============================
# 2️⃣ Aggiunta articoli dinamica
try:
    articoli = load_articoli(credentials)
except Exception as e:
    st.error("❌ Errore nel leggere gli articoli dal foglio Google Sheets!")
    st.error(f"Dettaglio errore: {e}")
    st.stop()

if not articoli:
    st.warning("⚠️ Nessun articolo trovato!")
    st.stop()

# inizializza lista articoli nel session_state
if "ordine_articoli" not in st.session_state:
    st.session_state["ordine_articoli"] = []

st.subheader("Aggiungi articoli all'ordine")

# pulsante per aggiungere una nuova riga articolo
if st.button("➕ Aggiungi articolo"):
    # aggiungo un id univoco per ogni articolo
    st.session_state["ordine_articoli"].append({"id": str(uuid.uuid4()), "articolo": None, "qty": 1})

# crea le righe dinamiche con rimozione sicura
nuovo_ordine_articoli = []
for item in st.session_state["ordine_articoli"]:
    col1, col2, col3 = st.columns([4, 2, 1])
    with col1:
        articolo_scelto = st.selectbox(
            "Articolo",
            [a["Descrizione"] for a in articoli],
            index=[a["Descrizione"] for a in articoli].index(item["articolo"]) if item["articolo"] else 0,
            key=f"art-{item['id']}"
        )
        item["articolo"] = articolo_scelto
    with col2:
        qty = st.number_input(
            "Quantità",
            min_value=0, step=1, format="%d",
            value=item["qty"],
            key=f"qty-{item['id']}"
        )
        item["qty"] = int(qty)
    with col3:
        elimina = st.button("❌", key=f"del-{item['id']}")
        if not elimina:
            # mantieni solo gli articoli non eliminati
            nuovo_ordine_articoli.append(item)

# aggiorna la session_state
st.session_state["ordine_articoli"] = nuovo_ordine_articoli

# ===============================
# 3️⃣ Riepilogo ordine in tempo reale
ordine = []
for item in st.session_state["ordine_articoli"]:
    if item["articolo"] and item["qty"] > 0:
        art = next(a for a in articoli if a["Descrizione"] == item["articolo"])
        ordine.append({
            "IdArticolo": art["IdArticolo"],
            "Descrizione": art["Descrizione"],
            "Quantita": int(item["qty"])
        })

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
        st.warning("⚠️ Devi aggiungere almeno un articolo!")
    else:
        try:
            id_ordine = crea_ordine(credentials, email, cliente_scelto, ordine)

            # invia email a destinatario predefinito
            destinatario = "lucamantini2009@gmail.com"
            corpo_email = f"Ordine #{id_ordine} di {email} per cliente {cliente_scelto}:\n\n"
            for item in ordine:
                corpo_email += f"{item['Descrizione']} x {item['Quantita']}\n"

            send_email(credentials, destinatario, f"Nuovo ordine #{id_ordine}", corpo_email)
            st.success(f"✅ Ordine #{id_ordine} inviato correttamente a {destinatario}!")

            # reset della lista articoli dopo invio
            st.session_state["ordine_articoli"] = []

        except Exception as e:
            st.error("❌ Errore durante l'invio dell'ordine!")
            st.error(f"Dettaglio errore: {e}")
