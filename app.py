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

# HEADER UTENTE
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

try:
    clienti = load_clienti(credentials)
    articoli = load_articoli(credentials)
except Exception as e:
    st.error("❌ Errore nel leggere dati")
    st.error(e)
    st.stop()

if not clienti or not articoli:
    st.warning("⚠️ Nessun cliente o articolo trovato")
    st.stop()

# ===============================
# CLIENTE
cliente_scelto = st.selectbox("Seleziona cliente", [c["Nome"] for c in clienti])
st.divider()

# ===============================
# ORDINE
if "ordine" not in st.session_state:
    st.session_state["ordine"] = []

if st.button("➕ Aggiungi articolo", use_container_width=True):
    st.session_state["ordine"].append({"id": str(uuid.uuid4()), "articolo": None, "qty": 1})

# ===============================
# COMPONENTE RIGA ARTICOLO
def articolo_row(item, articoli, mobile=False):
    """
    Ritorna articolo selezionato, qty e se eliminare.
    Layout:
        Desktop: 1 riga → descrizione + qty + elimina
        Mobile: 2 righe → descrizione / (qty + elimina)
    """
    if not mobile:
        # Desktop: 1 riga
        cols = st.columns([4, 1, 1])
        articolo = cols[0].selectbox(
            "Articolo",
            [a["Descrizione"] for a in articoli],
            index=[a["Descrizione"] for a in articoli].index(item["articolo"]) if item["articolo"] else 0,
            key=f"art-{item['id']}",
            label_visibility="collapsed"
        )
        qty = cols[1].number_input(
            "Qtà",
            min_value=0,
            value=item["qty"],
            step=1,
            key=f"qty-{item['id']}",
            label_visibility="collapsed"
        )
        elimina = cols[2].button("🗑️", key=f"del-{item['id']}")
    else:
        # Mobile: 2 righe massime
        # Riga 1: descrizione
        articolo = st.selectbox(
            "Articolo",
            [a["Descrizione"] for a in articoli],
            index=[a["Descrizione"] for a in articoli].index(item["articolo"]) if item["articolo"] else 0,
            key=f"art-{item['id']}"
        )
        # Riga 2: qty + elimina sulla stessa riga
        col_qty, col_del = st.columns([1, 1])
        qty = col_qty.number_input("Qtà", min_value=0, value=item["qty"], step=1, key=f"qty-{item['id']}")
        elimina = col_del.button("🗑️", key=f"del-{item['id']}")
    return articolo, qty, elimina

# ===============================
# Determina layout mobile/desktop
# Facile e sicuro: mobile se larghezza schermo stimata < 600px
mobile = st.session_state.get("mobile_mode", False)

# Render ordine
nuovo_ordine = []
for item in st.session_state["ordine"]:
    art, qty, elimina = articolo_row(item, articoli, mobile)
    if not elimina:
        nuovo_ordine.append({"id": item["id"], "articolo": art, "qty": qty})

st.session_state["ordine"] = nuovo_ordine

# ===============================
# RIEPILOGO
ordine_finale = []
for item in st.session_state["ordine"]:
    if item["articolo"] and item["qty"] > 0:
        art_obj = next(a for a in articoli if a["Descrizione"] == item["articolo"])
        ordine_finale.append({
            "IdArticolo": art_obj["IdArticolo"],
            "Descrizione": art_obj["Descrizione"],
            "Quantita": item["qty"]
        })

if ordine_finale:
    st.subheader("🧾 Riepilogo ordine")
    for o in ordine_finale:
        st.write(f"• **{o['Descrizione']}** × {o['Quantita']}")
    st.write(f"**Totale articoli:** {sum(i['Quantita'] for i in ordine_finale)}")

# ===============================
# INVIO ORDINE
st.divider()
if st.button("📧 Invia ordine", type="primary", use_container_width=True, disabled=not ordine_finale):
    try:
        with st.spinner("Invio ordine in corso..."):
            id_ordine = crea_ordine(credentials, email, cliente_scelto, ordine_finale)
            corpo_email = f"Ordine #{id_ordine}\nUtente: {email}\nCliente: {cliente_scelto}\n\n"
            for i in ordine_finale:
                corpo_email += f"{i['Descrizione']} x {i['Quantita']}\n"
            send_email(credentials, "lucamantini2009@gmail.com", f"Nuovo ordine #{id_ordine}", corpo_email)
        st.success(f"✅ Ordine #{id_ordine} inviato con successo!")
        st.session_state["ordine"] = []
    except Exception as e:
        st.error("❌ Errore durante l'invio")
        st.error(e)
