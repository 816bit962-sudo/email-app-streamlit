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
    get_ordini,
    aggiorna_ordine
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
if "codice_temp" not in st.session_state:
    st.session_state["codice_temp"] = None
if "qty_temp" not in st.session_state:
    st.session_state["qty_temp"] = 1
if "note" not in st.session_state:
    st.session_state["note"] = ""
if "ordine_inviato" not in st.session_state:
    st.session_state["ordine_inviato"] = False

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
tab_ordine, tab_riepilogo, tab_bozze, tab_storico = st.tabs(
    ["🧾 Articoli Ordine", "📧 Riepilogo & Invio", "📝 Bozze", "📚 Ordini Storici"]
)

# ======================================================
# TAB 1 — INSERIMENTO ORDINE
# ======================================================
with tab_ordine:
    st.markdown("<b>Seleziona articolo</b>", unsafe_allow_html=True)
    
    # Callback per sincronizzare codice -> descrizione
    def sync_codice_to_descrizione():
        codice_selezionato = st.session_state["codice_temp"]
        if codice_selezionato:
            articolo_trovato = next(
                (a for a in articoli if a["Codice"] == codice_selezionato),
                None
            )
            if articolo_trovato:
                st.session_state["articolo_temp"] = articolo_trovato["Descrizione"]
    
    # Crea un dizionario per mappare codice -> descrizione
    codice_descrizione_map = {a["Codice"]: a["Descrizione"] for a in articoli}
    
    col1, col2 = st.columns([4, 1], gap="small")
    
    # Campo codice con descrizione affiancata
    with col1:
        st.selectbox(
            "Codice",
            options=[a["Codice"] for a in articoli],
            key="codice_temp",
            on_change=sync_codice_to_descrizione,
            label_visibility="collapsed",
            placeholder="Codice - Descrizione",
            format_func=lambda codice: f"{codice} - {codice_descrizione_map.get(codice, '')}"
        )
    
    # Campo quantità
    with col2:
        st.number_input(
            "",
            min_value=1,
            step=1,
            key="qty_temp",
            label_visibility="collapsed",
            format="%d"
        )
    
    # Funzione per aggiungere articolo alla lista
    def aggiungi_articolo():
        if not st.session_state["codice_temp"]:
            return
        
        art = next(
            (a for a in articoli if a["Codice"] == st.session_state["codice_temp"]),
            None
        )
        
        if art and art.get("IdArticolo"):
            st.session_state["ordine_articoli"].append({
                "IdArticolo": int(art["IdArticolo"]),
                "Codice": str(art["Codice"]),
                "Descrizione": str(art["Descrizione"]),
                "Qtà": int(st.session_state["qty_temp"])
            })
            st.session_state["qty_temp"] = 1
            st.session_state["codice_temp"] = None
            st.session_state["articolo_temp"] = None
    
    st.button(
        "➕ Aggiungi articolo",
        use_container_width=True,
        on_click=aggiungi_articolo,
        disabled=not st.session_state["codice_temp"],
        key="btn_aggiungi_articolo"
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
        # BUTTON SALVA BOZZA
        # ===============================
        def salva_bozza():
            with st.spinner("Salvataggio bozza in corso..."):
                id_ordine = crea_ordine(
                    credentials,
                    email,
                    st.session_state["cliente_scelto"],
                    st.session_state["ordine_articoli"],
                    st.session_state["note"],
                    stato="bozza"
                )
                
                # Invalida la cache degli ordini
                load_ordini.clear()
                
                st.session_state["ordine_articoli"] = []
                st.session_state["note"] = ""
                st.session_state["bozza_salvata"] = True
                st.session_state["ultimo_id_bozza"] = id_ordine
        
        # ===============================
        # BUTTON INVIA ORDINE
        # ===============================
        def invio_completato():
            with st.spinner("Invio ordine in corso..."):
                # Crea ordine con stato "inviato"
                id_ordine = crea_ordine(
                    credentials,
                    email,
                    st.session_state["cliente_scelto"],
                    st.session_state["ordine_articoli"],
                    st.session_state["note"],
                    stato="inviato"
                )
                
                # Prepara email
                rows_html = "".join([
                    f"""
                    <tr>
                        <td>{art['Codice']}</td>
                        <td>{art['Descrizione']}</td>
                        <td style="text-align:center;">{art['Qtà']}</td>
                    </tr>
                    """
                    for art in st.session_state["ordine_articoli"]
                ])
                
                corpo_html = f"""
                <html><body>
                <h3>Cliente: {st.session_state["cliente_scelto"]}</h3>
                <table border="1" cellpadding="6" cellspacing="0">
                    <tr>
                        <th>Codice</th><th>Descrizione</th><th>Qtà</th>
                    </tr>
                    {rows_html}
                </table>
                <p style="font-size:12px;">Ordine inserito da {email}</p>
                </body></html>
                """
                
                # Crea oggetto con note se presenti
                oggetto = f"Ordine #{id_ordine}"
                if st.session_state["note"].strip():
                    oggetto += f" - {st.session_state['note']}"
                
                # Invia email
                send_email(
                    credentials,
                    st.session_state["destinatario_scelto"],
                    oggetto,
                    corpo_html,
                    html=True
                )
                
                # Invalida la cache degli ordini
                load_ordini.clear()
                
                # Reset stato
                st.session_state["ordine_articoli"] = []
                st.session_state["note"] = ""
                st.session_state["ordine_inviato"] = True
                st.session_state["ultimo_id_ordine"] = id_ordine
        
        col1, col2 = st.columns(2, gap="small")
        
        with col1:
            st.button(
                "💾 Salva bozza",
                type="secondary",
                use_container_width=True,
                on_click=salva_bozza,
                key="btn_salva_bozza_riepilogo"
            )
        
        with col2:
            st.button(
                "📧 Invia ordine",
                type="primary",
                use_container_width=True,
                on_click=invio_completato,
                key="btn_invia_ordine_riepilogo"
            )
        
        # Mostra messaggio di successo bozza
        if st.session_state.get("bozza_salvata", False):
            st.success(f"✅ Bozza #{st.session_state['ultimo_id_bozza']} salvata!")
            st.session_state["bozza_salvata"] = False
        
        # Mostra messaggio di successo invio
        if st.session_state.get("ordine_inviato", False):
            st.success(f"✅ Ordine #{st.session_state['ultimo_id_ordine']} inviato!")
            st.session_state["ordine_inviato"] = False

# ======================================================
# TAB 3 — BOZZE
# ======================================================
with tab_bozze:
    # Filtra solo le bozze dell'utente corrente
    bozze_utente = [
        o for o in ordini 
        if o.get("DipendenteEmail", "").lower() == email.lower() 
        and o.get("Stato", "inviato") == "bozza"
    ]
    
    if not bozze_utente:
        st.info("🛈 Nessuna bozza salvata")
    else:
        # Ordina dal più recente
        bozze_sorted = sorted(bozze_utente, key=lambda x: int(x["IdOrdine"]), reverse=True)
        
        st.markdown("<b>Seleziona bozza</b>", unsafe_allow_html=True)
        bozza_selezionata = st.selectbox(
            "Bozza",
            bozze_sorted,
            format_func=lambda o: f"#{o['IdOrdine']} – {o['Cliente']} – {o['Data']}",
            label_visibility="collapsed",
            key="bozza_select"
        )
        
        st.divider()
        
        # ===============================
        # AGGIUNGI ARTICOLO ALLA BOZZA
        # ===============================
        st.markdown("<b>Aggiungi articolo</b>", unsafe_allow_html=True)
        
        col1, col2 = st.columns([4, 1], gap="small")
        
        with col1:
            st.selectbox(
                "Codice bozza",
                options=[a["Codice"] for a in articoli],
                key="codice_temp_bozza",
                label_visibility="collapsed",
                placeholder="Codice - Descrizione",
                format_func=lambda codice: f"{codice} - {codice_descrizione_map.get(codice, '')}"
            )
        
        with col2:
            st.number_input(
                "Quantità bozza",
                min_value=1,
                step=1,
                key="qty_temp_bozza",
                label_visibility="collapsed",
                format="%d"
            )
        
        def aggiungi_articolo_bozza():
            if not st.session_state["codice_temp_bozza"]:
                return
            
            art = next(
                (a for a in articoli if a["Codice"] == st.session_state["codice_temp_bozza"]),
                None
            )
            
            if art and art.get("IdArticolo"):
                # Aggiungi l'articolo alla bozza esistente
                nuovo_articolo = {
                    "IdArticolo": int(art["IdArticolo"]),
                    "Codice": str(art["Codice"]),
                    "Descrizione": str(art["Descrizione"]),
                    "Qtà": int(st.session_state["qty_temp_bozza"])
                }
                
                # Ottieni gli articoli correnti dalla bozza
                articoli_correnti = bozza_selezionata["Articoli"].copy()
                
                # Trova l'IdArticolo completo
                for art_bozza in articoli_correnti:
                    art_completo = next(
                        (a for a in articoli if a["Codice"] == art_bozza["Codice"]),
                        None
                    )
                    if art_completo:
                        art_bozza["IdArticolo"] = int(art_completo["IdArticolo"])
                
                # Aggiungi il nuovo articolo
                articoli_correnti.append(nuovo_articolo)
                
                # Aggiorna la bozza
                with st.spinner("Aggiunta articolo in corso..."):
                    aggiorna_ordine(
                        credentials,
                        bozza_selezionata["IdOrdine"],
                        bozza_selezionata["Cliente"],
                        articoli_correnti,
                        bozza_selezionata.get("Note", ""),
                        stato="bozza"
                    )
                    
                    load_ordini.clear()
                    st.session_state["articolo_aggiunto_bozza"] = True
                    st.session_state["qty_temp_bozza"] = 1
                    st.session_state["codice_temp_bozza"] = None
        
        st.button(
            "➕ Aggiungi articolo",
            use_container_width=True,
            on_click=aggiungi_articolo_bozza,
            disabled=not st.session_state.get("codice_temp_bozza"),
            key="btn_aggiungi_articolo_bozza"
        )
        
        if st.session_state.get("articolo_aggiunto_bozza", False):
            st.success("✅ Articolo aggiunto alla bozza!")
            st.session_state["articolo_aggiunto_bozza"] = False
            st.rerun()
        
        st.divider()
        
        # Mostra articoli della bozza
        st.markdown("<b>Articoli</b>", unsafe_allow_html=True)
        df_bozza = pd.DataFrame(bozza_selezionata["Articoli"])
        
        articoli_modificati = st.data_editor(
            df_bozza[["Codice", "Descrizione", "Qtà"]],
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            column_config={
                "Codice": st.column_config.TextColumn(
                    "Codice",
                    disabled=True,
                    width="small"
                ),
                "Descrizione": st.column_config.TextColumn(
                    "Descrizione",
                    disabled=True,
                    width="medium"
                ),
                "Qtà": st.column_config.NumberColumn(
                    "Qtà",
                    min_value=1,
                    step=1,
                    width="small"
                )
            },
            key="editor_bozza"
        )
        
        st.divider()
        
        # Cliente modificabile
        st.markdown("<b>Cliente</b>", unsafe_allow_html=True)
        cliente_bozza = st.selectbox(
            "Cliente bozza",
            options=[c["Nome"] for c in clienti],
            index=[c["Nome"] for c in clienti].index(bozza_selezionata["Cliente"]) 
                  if bozza_selezionata["Cliente"] in [c["Nome"] for c in clienti] else 0,
            key="cliente_bozza",
            label_visibility="collapsed"
        )
        
        st.divider()
        
        # Note modificabili
        st.markdown("<b>Note</b>", unsafe_allow_html=True)
        note_bozza = st.text_area(
            "Note bozza",
            value=bozza_selezionata.get("Note", ""),
            placeholder="Inserisci eventuali note per l'ordine...",
            key="note_bozza",
            height=100,
            label_visibility="collapsed"
        )
        
        st.divider()
        
        # Destinatario
        st.markdown("<b>Destinatario email</b>", unsafe_allow_html=True)
        destinatario_bozza = st.selectbox(
            "Destinatario bozza",
            options=[d["Destinatario"] for d in destinatari],
            key="dest_bozza",
            label_visibility="collapsed"
        )
        
        st.divider()
        
        # Funzioni per aggiornare e inviare bozza
        def aggiorna_bozza():
            with st.spinner("Aggiornamento bozza in corso..."):
                # Converti dataframe modificato in lista di articoli
                articoli_aggiornati = []
                for _, row in articoli_modificati.iterrows():
                    # Trova l'IdArticolo dal foglio articoli
                    art_completo = next(
                        (a for a in articoli if a["Codice"] == row["Codice"]),
                        None
                    )
                    if art_completo:
                        articoli_aggiornati.append({
                            "IdArticolo": int(art_completo["IdArticolo"]),
                            "Codice": row["Codice"],
                            "Descrizione": row["Descrizione"],
                            "Qtà": int(row["Qtà"])
                        })
                
                aggiorna_ordine(
                    credentials,
                    bozza_selezionata["IdOrdine"],
                    cliente_bozza,
                    articoli_aggiornati,
                    note_bozza,
                    stato="bozza"
                )
                
                load_ordini.clear()
                st.session_state["bozza_aggiornata"] = True
        
        def invia_bozza():
            with st.spinner("Invio ordine in corso..."):
                # Converti dataframe modificato in lista di articoli
                articoli_aggiornati = []
                for _, row in articoli_modificati.iterrows():
                    art_completo = next(
                        (a for a in articoli if a["Codice"] == row["Codice"]),
                        None
                    )
                    if art_completo:
                        articoli_aggiornati.append({
                            "IdArticolo": int(art_completo["IdArticolo"]),
                            "Codice": row["Codice"],
                            "Descrizione": row["Descrizione"],
                            "Qtà": int(row["Qtà"])
                        })
                
                # Aggiorna ordine a stato "inviato"
                aggiorna_ordine(
                    credentials,
                    bozza_selezionata["IdOrdine"],
                    cliente_bozza,
                    articoli_aggiornati,
                    note_bozza,
                    stato="inviato"
                )
                
                # Invia email
                rows_html = "".join([
                    f"""
                    <tr>
                        <td>{row['Codice']}</td>
                        <td>{row['Descrizione']}</td>
                        <td style="text-align:center;">{row['Qtà']}</td>
                    </tr>
                    """
                    for _, row in articoli_modificati.iterrows()
                ])
                
                corpo_html = f"""
                <html><body>
                <h3>Cliente: {cliente_bozza}</h3>
                <table border="1" cellpadding="6" cellspacing="0">
                    <tr>
                        <th>Codice</th><th>Descrizione</th><th>Qtà</th>
                    </tr>
                    {rows_html}
                </table>
                <p style="font-size:12px;">Ordine inserito da {email}</p>
                </body></html>
                """
                
                oggetto = f"Ordine #{bozza_selezionata['IdOrdine']}"
                if note_bozza.strip():
                    oggetto += f" - {note_bozza}"
                
                send_email(
                    credentials,
                    destinatario_bozza,
                    oggetto,
                    corpo_html,
                    html=True
                )
                
                load_ordini.clear()
                st.session_state["bozza_inviata"] = True
                st.session_state["id_bozza_inviata"] = bozza_selezionata['IdOrdine']
        
        col1, col2 = st.columns(2, gap="small")
        
        with col1:
            st.button(
                "💾 Aggiorna bozza",
                type="secondary",
                use_container_width=True,
                on_click=aggiorna_bozza,
                key="btn_aggiorna_bozza"
            )
        
        with col2:
            st.button(
                "📧 Invia ordine",
                type="primary",
                use_container_width=True,
                on_click=invia_bozza,
                key="btn_invia_bozza"
            )
        
        # Messaggi di successo
        if st.session_state.get("bozza_aggiornata", False):
            st.success("✅ Bozza aggiornata con successo!")
            st.session_state["bozza_aggiornata"] = False
        
        if st.session_state.get("bozza_inviata", False):
            st.success(f"✅ Ordine #{st.session_state['id_bozza_inviata']} inviato!")
            st.session_state["bozza_inviata"] = False

# ======================================================
# TAB 4 — ORDINI STORICI
# ======================================================
with tab_storico:
    # Filtra solo gli ordini inviati dall'utente corrente
    ordini_utente = [
        o for o in ordini 
        if o.get("DipendenteEmail", "").lower() == email.lower()
        and o.get("Stato", "inviato") == "inviato"
    ]
    
    if not ordini_utente:
        st.info("🛈 Nessun ordine presente")
    else:
        # Ordina dal più recente al più vecchio basandosi su IdOrdine
        ordini_sorted = sorted(ordini_utente, key=lambda x: int(x["IdOrdine"]), reverse=True)
        
        clienti_ordini = sorted({o["Cliente"] for o in ordini_sorted})
        
        st.markdown("<b>Cliente</b>", unsafe_allow_html=True)
        cliente = st.selectbox(
            "Cliente",
            clienti_ordini,
            label_visibility="collapsed",
            key="cliente_storico"
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
            label_visibility="collapsed",
            key="ordine_storico"
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
            
            # Crea oggetto con note se presenti
            oggetto = f"Ordine #{ordine_scelto['IdOrdine']}"
            if ordine_scelto.get("Note", "").strip():
                oggetto += f" - {ordine_scelto['Note']}"
            
            send_email(
                credentials,
                destinatario,
                oggetto,
                corpo_html,
                html=True
            )
            
            st.success("✅ Ordine reinviato!")
        
        st.button(
            "📧 Reinvia ordine",
            use_container_width=True,
            on_click=reinvia_ordine,
            key="btn_reinvia_ordine"
        )