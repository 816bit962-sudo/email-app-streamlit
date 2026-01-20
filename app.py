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

if st.button("➕ Aggiungi articolo", use_container_width=True):
    st.session_state["ordine_articoli"].append({
        "id": str(uuid.uuid4()),
        "articolo": None,
        "qty": 1,
        "elimina": False
    })

# ===============================
# Righe compatte con HTML/CSS flex
nuovo_ordine_articoli = []

for item in st.session_state["ordine_articoli"]:
    # Colore e opacità per eliminazione
    bg_color = "#ffd6d6" if item.get("elimina", False) else "#f9f9f9"
    opacity = 0.5 if item.get("elimina", False) else 1.0

    # HTML flex container per una sola riga compatta
    descrizione_val = item["articolo"] if item["articolo"] else "Seleziona articolo"
    container_html = f"""
    <div style='
        display: flex;
        align-items: center;
        justify-content: space-between;
        background-color: {bg_color};
        opacity: {opacity};
        padding: 5px;
        border-radius: 5px;
        flex-wrap: nowrap;
    '>
    <div style='flex:5; min-width:0;'>
        <select id='select-{item["id"]}' style='width:100%;'>
            {''.join([f"<option value='{a['Descrizione']}' {'selected' if a['Descrizione']==item['articolo'] else ''}>{a['Descrizione']}</option>" for a in articoli])}
        </select>
    </div>
    <div style='flex:1; margin-left:5px;'>
        <input type='number' id='qty-{item["id"]}' value='{item["qty"]}' min='0' style='width:100%;'>
    </div>
    <div style='flex:0.5; margin-left:5px; text-align:center;'>
        <input type='checkbox' id='del-{item["id"]}' {'checked' if item.get("elimina", False) else ''}>
    </div>
    </div>
    """
    st.markdown(container_html, unsafe_allow_html=True)

    # Recupero valori aggiornati tramite session_state con fallback
    nuovo_ordine_articoli.append({
        "id": item["id"],
        "articolo": item["articolo"],
        "qty": item["qty"],
        "elimina": item.get("elimina", False)
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
    for item in ordine:
        st.write(f"• **{item['Descrizione']}** × {item['Quantita']}")
    st.divider()
    st.write(f"**Totale articoli:** {sum(i['Quantita'] for i in ordine)}")

# ===============================
# INVIO ORDINE
st.divider()

if st.button("📧 Invia ordine", type="primary", use_container_width=True, disabled=not ordine):
    try:
        with st.spinner("Invio ordine in corso..."):
            id_ordine = crea_ordine(
                credentials, email, cliente_scelto, ordine
            )
            destinatario = "lucamantini2009@gmail.com"
            corpo_email = f"Ordine #{id_ordine}\nUtente: {email}\nCliente: {cliente_scelto}\n\n"
            for item in ordine:
                corpo_email += f"{item['Descrizione']} x {item['Quantita']}\n"
            send_email(credentials, destinatario, f"Nuovo ordine #{id_ordine}", corpo_email)

        st.success(f"✅ Ordine #{id_ordine} inviato con successo!")
        st.session_state["ordine_articoli"] = []

    except Exception as e:
        st.error("❌ Errore durante l'invio dell'ordine")
        st.error(e)
