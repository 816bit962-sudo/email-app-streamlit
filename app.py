import streamlit as st
import pandas as pd
from auth import google_login, get_credentials
from gmail import send_email
from sheets import (
    get_clienti,
    get_articoli,
    crea_ordine,
    get_destinatari,
    aggiungi_destinatario
)
import streamlit.components.v1 as components

# ===============================
# CONFIG
st.set_page_config(
    page_title="Ordini Aziendali",
    page_icon="📦",
    layout="centered"
)

# ===============================
# LOGIN
email = google_login()
credentials = get_credentials()

# ===============================
# CACHE
@st.cache_data(ttl=300)
def load_clienti(_credentials):
    return get_clienti(_credentials)

@st.cache_data(ttl=300)
def load_articoli(_credentials):
    return get_articoli(_credentials)

@st.cache_data(ttl=300)
def load_destinatari(_credentials):
    return get_destinatari(_credentials)

# ===============================
# SESSION STATE
if "ordine_articoli" not in st.session_state:
    st.session_state["ordine_articoli"] = []

if "articolo_temp" not in st.session_state:
    st.session_state["articolo_temp"] = None

if "qty_temp" not in st.session_state:
    st.session_state["qty_temp"] = 1

if "note" not in st.session_state:
    st.session_state["note"] = ""

if "destinatario" not in st.session_state:
    st.session_state["destinatario"] = ""

# ===============================
# LOAD DATA
clienti = load_clienti(credentials)
articoli = load_articoli(credentials)
destinatari = load_destinatari(credentials)

if not clienti or not articoli:
    st.error("Dati mancanti")
    st.stop()

# ===============================
# TABS
tab_ordine, tab_riepilogo = st.tabs(["🧾 Articoli Ordine", "📧 Riepilogo & Invio"])

# ===============================
# TAB 1 — INSERIMENTO
with tab_ordine:
    col1, col2 = st.columns([4, 1], gap="small")

    with col1:
        st.markdown("<b>Seleziona articolo</b>", unsafe_allow_html=True)
        st.selectbox(
            "Articolo",
            options=[a["Descrizione"] for a in articoli],
            key="articolo_temp",
            label_visibility="collapsed"
        )

    with col2:
        st.markdown("<b>Qtà</b>", unsafe_allow_html=True)
        st.number_input(
            "Qtà",
            min_value=1,
            step=1,
            key="qty_temp",
            label_visibility="collapsed"
        )

    def aggiungi_articolo():
        art = next(a for a in articoli if a["Descrizione"] == st.session_state["articolo_temp"])
        st.session_state["ordine_articoli"].append({
            "IdArticolo": str(art["IdArticolo"]),
            "Codice": art["Codice"],
            "Descrizione": art["Descrizione"],
            "Qtà": int(st.session_state["qty_temp"])
        })
        st.session_state["qty_temp"] = 1
        st.session_state["articolo_temp"] = None

    st.button(
        "➕ Aggiungi articolo",
        use_container_width=True,
        on_click=aggiungi_articolo,
        disabled=not st.session_state["articolo_temp"]
    )

    st.divider()
    st.markdown("<b>Seleziona cliente</b>", unsafe_allow_html=True)
    st.selectbox(
        "Cliente",
        options=[c["Nome"] for c in clienti],
        key="cliente_scelto",
        label_visibility="collapsed"
    )

# ===============================
# TAB 2 — RIEPILOGO
with tab_riepilogo:
    ordine = st.session_state["ordine_articoli"]

    if not ordine:
        st.info("🛈 Nessun articolo inserito")
        st.stop()

    df = pd.DataFrame(ordine)

    edited_df = st.data_editor(
        df[["Descrizione", "Qtà"]],
        use_container_width=True,
        hide_index=True
    )

    nuovi_articoli = []
    for _, row in edited_df.iterrows():
        art = next(a for a in ordine if a["Descrizione"] == row["Descrizione"])
        nuovi_articoli.append({
            "IdArticolo": art["IdArticolo"],
            "Codice": art["Codice"],
            "Descrizione": row["Descrizione"],
            "Qtà": int(row["Qtà"])
        })

    st.session_state["ordine_articoli"] = nuovi_articoli
    st.divider()

    # ===============================
    # DESTINATARIO — HTML + autocomplete moderno
    st.markdown("<b>Destinatario email</b>", unsafe_allow_html=True)
    options_html = "".join(f"<option value='{o}'></option>" for o in destinatari)

    html_code = f"""
    <input list="dest_list" id="dest_input" placeholder="Scrivi o seleziona un indirizzo email"
        style="width:100%; padding:8px; font-size:14px; margin-top:4px; border-radius:6px; border:1px solid #ccc;"
        onchange="document.dispatchEvent(new CustomEvent('updateDestinatario', {{detail:this.value}}))">
    <datalist id="dest_list">{options_html}</datalist>
    """

    components.html(html_code, height=60)

    # ===============================
    # usa st.query_params moderno
    if "destinatario" not in st.session_state:
        st.session_state["destinatario"] = ""

    query_params = st.query_params
    destinatario = query_params.get("destinatario", [""])[0]
    st.session_state["destinatario"] = destinatario

    st.divider()
    st.markdown("<b>Note</b>", unsafe_allow_html=True)
    st.text_area(
        "Note ordine",
        key="note",
        height=100,
        label_visibility="collapsed"
    )

    st.divider()

    # ===============================
    # INVIO ORDINE
    if st.button("📧 Invia ordine", type="primary", use_container_width=True):
        destinatario = st.session_state.get("destinatario", "").strip()
        if not destinatario:
            st.error("Inserisci un destinatario email")
            st.stop()

        # salva se nuovo
        if destinatario not in destinatari:
            aggiungi_destinatario(credentials, destinatario)
            st.cache_data.clear()

        # crea ordine e invia email
        id_ordine = crea_ordine(
            credentials,
            email,
            st.session_state["cliente_scelto"],
            nuovi_articoli,
            st.session_state.get("note", "")
        )

        subject = f"Ordine #{id_ordine}"

        send_email(
            credentials,
            destinatario,
            subject,
            "<b>Ordine inviato</b>",
            html=True
        )

        st.success(f"✅ Ordine #{id_ordine} inviato!")
        st.session_state.clear()
        st.rerun()
