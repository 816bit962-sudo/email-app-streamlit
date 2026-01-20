import streamlit as st
import streamlit.components.v1 as components
from auth import google_login, get_credentials, logout
from gmail import send_email
from sheets import get_clienti, get_articoli, crea_ordine
import uuid
import json

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
# CACHE
@st.cache_data(ttl=300)
def load_clienti(_credentials):
    return get_clienti(_credentials)

@st.cache_data(ttl=300)
def load_articoli(_credentials):
    return get_articoli(_credentials)

# ===============================
# CLIENTE
st.subheader("👥 Cliente")

clienti = load_clienti(credentials)
cliente_scelto = st.selectbox(
    "Seleziona cliente",
    [c["Nome"] for c in clienti]
)

st.divider()

# ===============================
# ARTICOLI
st.subheader("🧾 Articoli ordine")

articoli = load_articoli(credentials)
articoli_map = {a["IdArticolo"]: a["Descrizione"] for a in articoli}

if "ordine_articoli" not in st.session_state:
    st.session_state["ordine_articoli"] = []

if st.button("➕ Aggiungi articolo", use_container_width=True):
    st.session_state["ordine_articoli"].append({
        "id": str(uuid.uuid4()),
        "IdArticolo": list(articoli_map.keys())[0],
        "qty": 1
    })

# ===============================
# RIGHE ARTICOLO HTML (UNA SOLA RIGA GARANTITA)
nuovo_ordine = []

for idx, item in enumerate(st.session_state["ordine_articoli"]):
    key = f"row-{item['id']}"

    html = f"""
    <div style="display:flex; gap:6px; align-items:center;">
      <select id="art-{key}" style="flex:6; height:42px;">
        {''.join(
            f'<option value="{id_}" {"selected" if id_ == item["IdArticolo"] else ""}>{desc}</option>'
            for id_, desc in articoli_map.items()
        )}
      </select>

      <input id="qty-{key}" type="number" value="{item['qty']}"
        min="1"
        style="flex:1; max-width:60px; height:42px;" />

      <button id="del-{key}" style="height:42px;">❌</button>
    </div>

    <script>
    const send = () => {{
      const data = {{
        id: "{item['id']}",
        articolo: document.getElementById("art-{key}").value,
        qty: document.getElementById("qty-{key}").value,
        delete: false
      }};
      window.parent.postMessage(data, "*");
    }}

    document.getElementById("art-{key}").onchange = send;
    document.getElementById("qty-{key}").onchange = send;

    document.getElementById("del-{key}").onclick = () => {{
      window.parent.postMessage({{
        id: "{item['id']}",
        delete: true
      }}, "*");
    }}
    </script>
    """

    components.html(html, height=60)

# ===============================
# LISTENER JS → STREAMLIT
msg = st.session_state.get("_component_msg")

if msg:
    if msg.get("delete"):
        st.session_state["ordine_articoli"] = [
            i for i in st.session_state["ordine_articoli"]
            if i["id"] != msg["id"]
        ]
        st.experimental_rerun()
    else:
        for i in st.session_state["ordine_articoli"]:
            if i["id"] == msg["id"]:
                i["IdArticolo"] = msg["articolo"]
                i["qty"] = int(msg["qty"])

# ===============================
# RIEPILOGO
ordine = []
for i in st.session_state["ordine_articoli"]:
    art = next(a for a in articoli if a["IdArticolo"] == i["IdArticolo"])
    ordine.append({
        "IdArticolo": art["IdArticolo"],
        "Descrizione": art["Descrizione"],
        "Quantita": i["qty"]
    })

if ordine:
    st.subheader("🧾 Riepilogo")
    for i in ordine:
        st.write(f"• **{i['Descrizione']}** × {i['Quantita']}")

# ===============================
# INVIO ORDINE
st.divider()

if st.button("📧 Invia ordine", type="primary", use_container_width=True):
    id_ordine = crea_ordine(credentials, email, cliente_scelto, ordine)

    corpo = f"Ordine #{id_ordine}\nCliente: {cliente_scelto}\n\n"
    for i in ordine:
        corpo += f"{i['Descrizione']} x {i['Quantita']}\n"

    send_email(
        credentials,
        "lucamantini2009@gmail.com",
        f"Nuovo ordine #{id_ordine}",
        corpo
    )

    st.success("✅ Ordine inviato!")
    st.session_state["ordine_articoli"] = []
