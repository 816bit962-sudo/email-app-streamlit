import streamlit as st
from auth import google_login, get_credentials, logout
from gmail import send_email
from sheets import get_clienti, get_articoli, crea_ordine
import pandas as pd
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

# Inizializzazione session_state
if "ordine_articoli" not in st.session_state:
    st.session_state["ordine_articoli"] = []

if "articolo_temp" not in st.session_state:
    st.session_state["articolo_temp"] = None

if "qty_temp" not in st.session_state:
    st.session_state["qty_temp"] = 1

try:
    articoli = load_articoli(credentials)
except Exception as e:
    st.error("❌ Errore nel leggere gli articoli")
    st.error(e)
    st.stop()

if not articoli:
    st.warning("⚠️ Nessun articolo trovato")
    st.stop()

# ===============================
# FUNZIONE AGGIUNGI ARTICOLO
def aggiungi_articolo():
    if st.session_state["articolo_temp"] and st.session_state["qty_temp"] > 0:
        art = next(
            a for a in articoli
            if a["Descrizione"] == st.session_state["articolo_temp"]
        )
        st.session_state["ordine_articoli"].append({
            "IdArticolo": str(art["IdArticolo"]),
            "Descrizione": str(art["Descrizione"]),
            "Quantita": int(st.session_state["qty_temp"])
        })

        # Reset campi input
        st.session_state["articolo_temp"] = None
        st.session_state["qty_temp"] = 1

# Bottone aggiungi articolo
st.button("➕ Aggiungi articolo", use_container_width=True, on_click=aggiungi_articolo)

# Campo singolo per aggiungere articolo
with st.container(border=True):
    col1, col2 = st.columns([4, 1])

    with col1:
        articolo_temp = st.selectbox(
            "Articolo",
            [a["Descrizione"] for a in articoli],
            index=(
                [a["Descrizione"] for a in articoli].index(st.session_state["articolo_temp"])
                if st.session_state["articolo_temp"] in [a["Descrizione"] for a in articoli]
                else 0
            ),
            key="articolo_temp"
        )

    with col2:
        qty_temp = st.number_input(
            "Qtà",
            min_value=1,
            step=1,
            format="%d",
            key="qty_temp"
        )

st.divider()

# ===============================
# RIEPILOGO ORDINE - DATA EDITOR
ordine = st.session_state["ordine_articoli"]

if ordine:
    st.subheader("🧾 Riepilogo ordine")

    # DataFrame per data_editor
    df_ordine = pd.DataFrame(ordine)
    df_ordine["Elimina?"] = False

    # Mostra solo le colonne visibili nell'editor
    edited_df = st.data_editor(
        df_ordine[["Descrizione", "Quantita", "Elimina?"]],
        use_container_width=True,
        num_rows="dynamic",
        key="editable_ordine"
    )

    # Aggiorna il carrello con modifiche
    nuovi_articoli = []
    for idx, row in edited_df.iterrows():
        if not row["Elimina?"]:
            original = df_ordine.iloc[idx]  # prendi IdArticolo originale
            nuovi_articoli.append({
                "IdArticolo": str(original["IdArticolo"]),
                "Descrizione": str(row["Descrizione"]),
                "Quantita": int(row["Quantita"])
            })

    st.session_state["ordine_articoli"] = nuovi_articoli

    st.write(f"**Totale articoli:** {sum(i['Quantita'] for i in nuovi_articoli)}")

st.divider()

# ===============================
# INVIO ORDINE
if st.button(
    "📧 Invia ordine",
    type="primary",
    use_container_width=True,
    disabled=not st.session_state["ordine_articoli"]
):
    try:
        with st.spinner("Invio ordine in corso..."):
            # Converte tutto in tipi Python standard per evitare errori JSON
            ordine_finale = [
                {
                    "IdArticolo": str(item["IdArticolo"]),
                    "Descrizione": str(item["Descrizione"]),
                    "Quantita": int(item["Quantita"])
                }
                for item in st.session_state["ordine_articoli"]
            ]

            id_ordine = crea_ordine(
                credentials,
                email,
                cliente_scelto,
                ordine_finale
            )

            destinatario = "lucamantini2009@gmail.com"
            corpo_email = (
                f"Ordine #{id_ordine}\n"
                f"Utente: {email}\n"
                f"Cliente: {cliente_scelto}\n\n"
            )

            for item in ordine_finale:
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
