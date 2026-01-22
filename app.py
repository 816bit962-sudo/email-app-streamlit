import streamlit as st
import pandas as pd
from auth import google_login, get_credentials
from gmail import send_email
from sheets import get_clienti, get_articoli, crea_ordine

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

# ===============================
# LOAD DATA
clienti = load_clienti(credentials)
articoli = load_articoli(credentials)

if not clienti or not articoli:
    st.error("Dati mancanti")
    st.stop()

# ===============================
# TABS
tab_ordine, tab_riepilogo = st.tabs(
    ["🧾 Articoli Ordine", "📧 Riepilogo & Invio"]
)

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
        hide_index=True,
        column_config={
            "Descrizione": st.column_config.TextColumn("Descrizione", disabled=True),
            "Qtà": st.column_config.NumberColumn("Qtà", min_value=1, step=1)
        }
    )

    nuovi_articoli = []
    for _, row in edited_df.iterrows():
        art = next(a for a in ordine if a["Descrizione"] == row["Descrizione"])
        nuovi_articoli.append({
            "IdArticolo": art["IdArticolo"],
            "Descrizione": row["Descrizione"],
            "Qtà": int(row["Qtà"])
        })

    st.session_state["ordine_articoli"] = nuovi_articoli

    st.divider()

    # 📝 NOTE
    st.markdown("<b>Note</b>", unsafe_allow_html=True)
    st.text_area(
        "Note ordine",
        placeholder="Inserisci eventuali note per l’ordine...",
        key="note",
        height=100,
        label_visibility="collapsed"
    )

    st.divider()

    if st.button(
        "📧 Invia ordine",
        type="primary",
        use_container_width=True,
        disabled=not nuovi_articoli
    ):
        with st.spinner("Invio ordine in corso..."):
            id_ordine = crea_ordine(
                credentials,
                email,
                st.session_state["cliente_scelto"],
                nuovi_articoli,
                st.session_state["note"]
            )

            corpo = (
                f"Ordine #{id_ordine}\n"
                f"Utente: {email}\n"
                f"Cliente: {st.session_state['cliente_scelto']}\n\n"
                f"NOTE:\n{st.session_state['note']}\n\n"
            )

            for item in nuovi_articoli:
                corpo += f"{item['Descrizione']} x {item['Qtà']}\n"

            send_email(
                credentials,
                "lucamantini2009@gmail.com",
                f"Nuovo ordine #{id_ordine}",
                corpo
            )

        st.success(f"✅ Ordine #{id_ordine} inviato!")
        st.session_state["ordine_articoli"] = []

        if "note" in st.session_state:
            del st.session_state["note"]

        st.rerun()

