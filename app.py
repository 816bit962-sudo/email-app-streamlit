import streamlit as st
from auth import google_login, get_credentials, logout
from gmail import send_email
from sheets import get_clienti, get_articoli, crea_ordine
import uuid

# ===============================
# CONFIG
st.set_page_config(
    page_title="Ordini Aziendali",
    page_icon="📦",
    layout="centered"
)

st.title("📦 Ordini Aziendali")

# ===============================
# LOGIN
email = google_login()
credentials = get_credentials()

# HEADER UTENTE (compatto)
col1, col2 = st.columns([1, 5])
with col1:
    if "picture" in st.session_state:
        st.image(st.session_state["picture"], width=40)
with col2:
    st.caption(f"👤 {email}")

with st.expander("⚙️ Account"):
    if st.button("🚪 Logout"):
        logout()

st.divider()

# ===============================
# CACHE GOOGLE SHEETS
@st.cache_data(ttl=300)
def load_clienti(_credentials):
    return get_clienti(_credentials)

@st.cache_data(ttl=300)
def load_articoli(_credentials):
    return get_articoli(_credentials)

# ===============================
# CLIENTE
st.subheader("👥 Cliente")

try:
    clienti = load_clienti(credentials)
except Exception as e:
    st.error("❌ Errore nel leggere i clienti")
    st.error(e)
    st.stop()

if not clienti:
    st.warning("⚠️ Nessun cliente trovato")
    st.stop()

cliente_scelto = st.selectbox(
    "Seleziona cliente",
    [c["Nome"] for c in clienti]
)

st.divider()

# ===============================
# ARTICOLI
st.subheader("🧾 Articoli ordine")

try:
    articoli = load_articoli(credentials)
except Exception as e:
    st.error("❌ Errore nel leggere gli articoli")
    st.error(e)
    st.stop()

if not articoli:
    st.warning("⚠️ Nessun articolo trovato")
    st.stop()

if "ordine_articoli" not in st.session_state:
    st.session_state["ordine_articoli"] = []

# Pulsante aggiunta articolo
if st.button("➕ Aggiungi articolo", use_container_width=True):
    st.session_state["ordine_articoli"].append({
        "id": str(uuid.uuid4()),
        "articolo": None,
        "qty": 1
    })

# Righe articolo (card)
nuovo_ordine_articoli = []

for item in st.session_state["ordine_articoli"]:
    with st.container(border=True):

        col1, col2, col3 = st.columns([6, 2, 1])

        with col1:
            articolo_scelto = st.selectbox(
                "Articolo",
                [a["Descrizione"] for a in articoli],
                index=[a["Descrizione"] for a in articoli].index(item["articolo"])
                if item["articolo"] else 0,
                label_visibility="collapsed",
                key=f"art-{item['id']}"
            )

        with col2:
            qty = st.number_input(
                "Qtà",
                min_value=0,
                step=1,
                value=item["qty"],
                format="%d",
                label_visibility="collapsed",
                key=f"qty-{item['id']}"
            )

        with col3:
            remove = st.button("❌", key=f"del-{item['id']}")

        if remove:
            continue

        nuovo_ordine_articoli.append({
            "id": item["id"],
            "articolo": articolo_scelto,
            "qty": int(qty)
        })


st.session_state["ordine_articoli"] = nuovo_ordine_articoli

# ===============================
# RIEPILOGO
ordine = []

for item in st.session_state["ordine_articoli"]:
    if item["articolo"] and item["qty"] > 0:
        art = next(a for a in articoli if a["Descrizione"] == item["articolo"])
        ordine.append({
            "IdArticolo": art["IdArticolo"],
            "Descrizione": art["Descrizione"],
            "Quantita": item["qty"]
        })

if ordine:
    st.subheader("🧾 Riepilogo ordine")
    with st.container(border=True):
        for item in ordine:
            st.write(f"• **{item['Descrizione']}** × {item['Quantita']}")
        st.divider()
        st.write(f"**Totale articoli:** {sum(i['Quantita'] for i in ordine)}")

# ===============================
# INVIO ORDINE
st.divider()

if st.button(
    "📧 Invia ordine",
    type="primary",
    use_container_width=True,
    disabled=not ordine
):
    try:
        with st.spinner("Invio ordine in corso..."):
            id_ordine = crea_ordine(
                credentials,
                email,
                cliente_scelto,
                ordine
            )

            destinatario = "lucamantini2009@gmail.com"
            corpo_email = (
                f"Ordine #{id_ordine}\n"
                f"Utente: {email}\n"
                f"Cliente: {cliente_scelto}\n\n"
            )

            for item in ordine:
                corpo_email += f"{item['Descrizione']} x {item['Quantita']}\n"

            send_email(
                credentials,
                destinatario,
                f"Nuovo ordine #{id_ordine}",
                corpo_email
            )

        st.success(f"✅ Ordine #{id_ordine} inviato con successo!")
        st.session_state["ordine_articoli"] = []

    except Exception as e:
        st.error("❌ Errore durante l'invio dell'ordine")
        st.error(e)
