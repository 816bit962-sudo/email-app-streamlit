import streamlit as st
from auth import google_login, get_credentials, logout
from gmail import send_email
from sheets import get_clienti, get_articoli, crea_ordine
import pandas as pd

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
# ACCOUNT ICON IN ALTO A DESTRA
with st.container():
    col1, col2 = st.columns([9, 1])
    with col2:
        if st.button("👤"):
            st.session_state["show_account"] = not st.session_state.get("show_account", False)

if st.session_state.get("show_account", False):
    st.info(f"Email: {email}")
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
# INIZIALIZZAZIONE SESSION STATE
if "ordine_articoli" not in st.session_state:
    st.session_state["ordine_articoli"] = []

if "articolo_temp" not in st.session_state:
    st.session_state["articolo_temp"] = None

if "qty_temp" not in st.session_state:
    st.session_state["qty_temp"] = 1

# ===============================
# CARICAMENTO DATI
try:
    clienti = load_clienti(credentials)
except Exception as e:
    st.error("❌ Errore nel leggere i clienti")
    st.error(e)
    st.stop()

try:
    articoli = load_articoli(credentials)
except Exception as e:
    st.error("❌ Errore nel leggere gli articoli")
    st.error(e)
    st.stop()

if not clienti:
    st.warning("⚠️ Nessun cliente trovato")
    st.stop()

if not articoli:
    st.warning("⚠️ Nessun articolo trovato")
    st.stop()

# ===============================
# TABS PRINCIPALI
tab_ordine, tab_riepilogo = st.tabs(["🧾 Articoli Ordine", "📧 Riepilogo & Invio"])

# ===============================
# TAB 1 — INSERIMENTO ARTICOLI (FIXED HEIGHT, NO SCROLL)
with tab_ordine:
    st.subheader("🧾 Articoli Ordine")

    # Inserimento articolo + quantità
    col1, col2 = st.columns([4, 1])
    with col1:
        st.selectbox(
            "Articolo",
            [a["Descrizione"] for a in articoli],
            key="articolo_temp"
        )
    with col2:
        st.number_input(
            "Qtà",
            min_value=1,
            step=1,
            format="%d",
            key="qty_temp"
        )

    # Funzione aggiungi articolo
    def aggiungi_articolo():
        if st.session_state["articolo_temp"]:
            art = next(
                a for a in articoli
                if a["Descrizione"] == st.session_state["articolo_temp"]
            )
            st.session_state["ordine_articoli"].append({
                "IdArticolo": str(art["IdArticolo"]),
                "Descrizione": art["Descrizione"],
                "Quantita": int(st.session_state["qty_temp"])
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

    # Selezione cliente
    st.subheader("👥 Cliente")
    cliente_scelto = st.selectbox(
        "Seleziona cliente",
        [c["Nome"] for c in clienti],
        key="cliente_scelto"
    )

# ===============================
# TAB 2 — RIEPILOGO & INVIO (FIXED HEIGHT, NO SCROLL)
with tab_riepilogo:
    st.subheader("📦 Riepilogo Ordine")

    ordine = st.session_state["ordine_articoli"]

    if not ordine:
        st.info("🛈 Nessun articolo inserito")
        st.stop()

    df_ordine = pd.DataFrame(ordine)
    df_ordine["Elimina?"] = False

    edited_df = st.data_editor(
        df_ordine[["Descrizione", "Quantita", "Elimina?"]],
        use_container_width=True,
        num_rows="fixed"
    )

    nuovi_articoli = []
    for idx, row in edited_df.iterrows():
        if not row["Elimina?"]:
            original = df_ordine.iloc[idx]
            nuovi_articoli.append({
                "IdArticolo": original["IdArticolo"],
                "Descrizione": row["Descrizione"],
                "Quantita": int(row["Quantita"])
            })

    st.session_state["ordine_articoli"] = nuovi_articoli

    st.write(
        f"**Totale articoli:** {sum(i['Quantita'] for i in nuovi_articoli)}"
    )

    st.divider()

    # INVIO ORDINE
    if st.button(
        "📧 Invia ordine",
        type="primary",
        use_container_width=True,
        disabled=not st.session_state["ordine_articoli"]
    ):
        try:
            with st.spinner("Invio ordine in corso..."):
                id_ordine = crea_ordine(
                    credentials,
                    email,
                    st.session_state["cliente_scelto"],
                    nuovi_articoli
                )

                corpo_email = (
                    f"Ordine #{id_ordine}\n"
                    f"Utente: {email}\n"
                    f"Cliente: {st.session_state['cliente_scelto']}\n\n"
                )

                for item in nuovi_articoli:
                    corpo_email += f"{item['Descrizione']} x {item['Quantita']}\n"

                send_email(
                    credentials,
                    "lucamantini2009@gmail.com",
                    f"Nuovo ordine #{id_ordine}",
                    corpo_email
                )

            st.success(f"✅ Ordine #{id_ordine} inviato con successo!")
            st.session_state["ordine_articoli"] = []

        except Exception as e:
            st.error("❌ Errore durante l'invio dell'ordine")
            st.error(e)
