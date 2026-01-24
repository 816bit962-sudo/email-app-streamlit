import streamlit as st
import pandas as pd
from datetime import datetime
from auth import google_login, get_credentials
from gmail import send_email
from sheets import (
    get_clienti,
    get_articoli,
    get_destinatari,
    crea_ordine,
    get_ordini
)

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

@st.cache_data(ttl=300)
def load_ordini(_credentials):
    return get_ordini(_credentials)

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
# LOAD DATA GLOBALE
clienti = load_clienti(credentials)
articoli = load_articoli(credentials)
destinatari = load_destinatari(credentials)
ordini = load_ordini(credentials)

if not clienti or not articoli or not destinatari or ordini is None:
    st.error("Dati mancanti nei fogli Google Sheets")
    st.stop()

# ===============================
# TABS
tab_ordine, tab_riepilogo, tab_storico = st.tabs(
    ["🧾 Articoli Ordine", "📧 Riepilogo & Invio", "📚 Ordini Storici"]
)

# ======================================================
# TAB 1 — INSERIMENTO ORDINE
# ======================================================
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
        art = next(
            a for a in articoli 
            if a["Descrizione"] == st.session_state["articolo_temp"]
        )
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

# ======================================================
# TAB 2 — RIEPILOGO & INVIO
# ======================================================
with tab_riepilogo:
    ordine = st.session_state["ordine_articoli"]
    
    if not ordine:
        st.info("🛈 Nessun articolo inserito. Vai alla tab 'Articoli Ordine' per aggiungere articoli.")
    else:
        df = pd.DataFrame(ordine)
        
        event = st.data_editor(
            df[["Descrizione", "Qtà"]],
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            column_config={
                "Descrizione": st.column_config.TextColumn(
                    "Descrizione",
                    disabled=True,
                    width="medium"
                ),
                "Qtà": st.column_config.NumberColumn(
                    "Qtà",
                    min_value=1,
                    step=1
                )
            },
            key="editor_riepilogo"
        )
        
        # Aggiorna articoli basandosi sul data_editor
        nuovi_articoli = []
        for i in range(len(event)):
            if i < len(ordine):
                nuovi_articoli.append({
                    "IdArticolo": ordine[i]["IdArticolo"],
                    "Codice": ordine[i]["Codice"],
                    "Descrizione": event.iloc[i]["Descrizione"],
                    "Qtà": int(event.iloc[i]["Qtà"])
                })
        
        st.session_state["ordine_articoli"] = nuovi_articoli
        
        st.divider()
        
        st.markdown("<b>Destinatario email</b>", unsafe_allow_html=True)
        st.selectbox(
            "Destinatario",
            options=[d["Destinatario"] for d in destinatari],
            key="destinatario_scelto",
            label_visibility="collapsed"
        )
        
        st.divider()
        
        st.markdown("<b>Note</b>", unsafe_allow_html=True)
        st.text_area(
            "Note ordine",
            placeholder="Inserisci eventuali note per l'ordine...",
            key="note",
            height=100,
            label_visibility="collapsed",
            value=st.session_state.get("note", "")
        )
        
        st.divider()
        
        # ===============================
        # BUTTON INVIO ORDINE CON CALLBACK
        # ===============================
        def invio_completato():
            with st.spinner("Invio ordine in corso..."):
                id_ordine = crea_ordine(
                    credentials,
                    email,
                    st.session_state["cliente_scelto"],
                    st.session_state["ordine_articoli"],
                    st.session_state["note"]
                )
                
                # Invalida la cache degli ordini per ricaricare i dati aggiornati
                load_ordini.clear()
                
                rows_html = "".join([
                    f"""
                    <tr>
                        <td>{a['Codice']}</td>
                        <td>{a['Descrizione']}</td>
                        <td style="text-align:center;">{a['Qtà']}</td>
                    </tr>
                    """
                    for a in st.session_state["ordine_articoli"]
                ])
                
                corpo_html = f"""
                <html><body>
                <h3>Cliente: {st.session_state['cliente_scelto']}</h3>
                <table border="1" cellpadding="6" cellspacing="0">
                    <tr>
                        <th>Codice</th><th>Descrizione</th><th>Qtà</th>
                    </tr>
                    {rows_html}
                </table>
                <p style="font-size:12px;">Ordine inserito da {email}</p>
                </body></html>
                """
                
                oggetto = f"Ordine #{id_ordine}"
                if st.session_state["note"].strip():
                    oggetto += f" - {st.session_state['note']}"
                
                send_email(
                    credentials,
                    st.session_state["destinatario_scelto"],
                    oggetto,
                    corpo_html,
                    html=True
                )
                
                st.success(f"✅ Ordine #{id_ordine} inviato!")
                st.session_state["ordine_articoli"] = []
                st.session_state["note"] = ""
        
        st.button(
            "📧 Invia ordine",
            type="primary",
            use_container_width=True,
            on_click=invio_completato
        )

# ======================================================
# TAB 3 — ORDINI STORICI
# ======================================================
with tab_storico:
    if not ordini:
        st.info("🛈 Nessun ordine presente")
    else:
        # Ordina dal più recente al più vecchio basandosi su IdOrdine
        ordini_sorted = sorted(ordini, key=lambda x: int(x["IdOrdine"]), reverse=True)
        
        clienti_ordini = sorted({o["Cliente"] for o in ordini_sorted})
        
        st.markdown("<b>Cliente</b>", unsafe_allow_html=True)
        cliente = st.selectbox(
            "Cliente",
            clienti_ordini,
            label_visibility="collapsed"
        )
        
        # Filtra ordini del cliente selezionato (già in ordine dal più recente)
        ordini_cliente = [
            o for o in ordini_sorted 
            if o["Cliente"].strip().lower() == cliente.strip().lower()
        ]
        
        st.markdown("<b>Ordine</b>", unsafe_allow_html=True)
        ordine_scelto = st.selectbox(
            "Ordine",
            ordini_cliente,
            format_func=lambda o: f"#{o['IdOrdine']} – {o['Data']}",
            label_visibility="collapsed"
        )
        
        st.divider()
        
        df_art = pd.DataFrame(ordine_scelto["Articoli"])
        st.dataframe(
            df_art,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Codice": st.column_config.TextColumn(
                    "Codice",
                    width="small"
                ),
                "Descrizione": st.column_config.TextColumn(
                    "Descrizione",
                    width="medium"
                ),
                "Qtà": st.column_config.NumberColumn(
                    "Qtà",
                    width="small"
                )
            },
            height=300
        )
        
        st.divider()
        
        st.markdown("<b>Destinatario email</b>", unsafe_allow_html=True)
        destinatario = st.selectbox(
            "Destinatario storico",
            [d["Destinatario"] for d in destinatari],
            key="dest_storico",
            label_visibility="collapsed"
        )
        
        def reinvia_ordine():
            rows_html = "".join([
                f"""
                <tr>
                    <td>{a['Codice']}</td>
                    <td>{a['Descrizione']}</td>
                    <td style="text-align:center;">{a['Qtà']}</td>
                </tr>
                """
                for a in ordine_scelto["Articoli"]
            ])
            
            corpo_html = f"""
            <html><body>
            <h3>Cliente: {ordine_scelto['Cliente']}</h3>
            <table border="1" cellpadding="6" cellspacing="0">
                <tr>
                    <th>Codice</th><th>Descrizione</th><th>Qtà</th>
                </tr>
                {rows_html}
            </table>
            <p style="font-size:12px;">
                Ordine #{ordine_scelto['IdOrdine']} – creato da {ordine_scelto['DipendenteEmail']}
            </p>
            </body></html>
            """
            
            send_email(
                credentials,
                destinatario,
                f"Ordine #{ordine_scelto['IdOrdine']}",
                corpo_html,
                html=True
            )
            
            st.success("✅ Ordine reinviato!")
        
        st.button(
            "📧 Reinvia ordine",
            use_container_width=True,
            on_click=reinvia_ordine
        )