import streamlit as st
from auth import google_login, get_credentials, logout
from gmail import send_email
from sheets import get_clienti, get_articoli, crea_ordine
import uuid
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

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
# ARTICOLI ORDINE - AgGrid
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

# Lista articoli in sessione
if "ordine_articoli" not in st.session_state:
    st.session_state["ordine_articoli"] = []

# Pulsante aggiunta articolo
if st.button("➕ Aggiungi articolo", use_container_width=True):
    st.session_state["ordine_articoli"].append({
        "id": str(uuid.uuid4()),
        "articolo": "",
        "qty": 1
    })

# ===============================
# PREPARO DATAFRAME per AgGrid
df = pd.DataFrame([
    {
        "Id": item["id"],
        "Articolo": item["articolo"] or "",
        "Quantita": item["qty"]
    } for item in st.session_state["ordine_articoli"]
])

# Aggiungo opzione ❌ come colonna separata
df["Elimina"] = "❌"

# Configurazione AgGrid
gb = GridOptionsBuilder.from_dataframe(df)
gb.configure_selection(selection_mode="single", use_checkbox=False)
gb.configure_column("Articolo", editable=True, cellEditor="agSelectCellEditor", cellEditorParams={
    "values": [a["Descrizione"] for a in articoli]
})
gb.configure_column("Quantita", editable=True)
gb.configure_column("Elimina", editable=False, cellRenderer="function(params) {return params.value;}", width=60)
gridOptions = gb.build()

# Mostra la tabella
grid_response = AgGrid(
    df,
    gridOptions=gridOptions,
    update_mode=GridUpdateMode.VALUE_CHANGED,
    fit_columns_on_grid_load=True,
    allow_unsafe_jscode=True
)

# ===============================
# AGGIORNO SESSION_STATE dopo modifiche
ordine_articoli_nuovo = []
for row in grid_response['data'].to_dict('records'):
    if row["Elimina"] == "❌" and row.get("_selectedRow", False):
        # Rimuove selezionando riga ❌
        continue
    ordine_articoli_nuovo.append({
        "id": row["Id"],
        "articolo": row["Articolo"],
        "qty": int(row["Quantita"])
    })

st.session_state["ordine_articoli"] = ordine_articoli_nuovo

# ===============================
# RIEPILOGO ORDINE
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
    with st.container():
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
