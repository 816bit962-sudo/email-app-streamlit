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
tab_ordine, tab_riepilogo, tab_storico = st.tabs(
    ["🧾 Articoli Ordine", "📧 Riepilogo & Invio", "📚 Ordini Storici"]
)

# ======================================================
# TAB 1 — INSERIMENTO ORDINE
# ======================================================
with tab_ordine:
    # Bottone per aprire/chiudere scanner barcode
    if "mostra_scanner" not in st.session_state:
        st.session_state["mostra_scanner"] = False
    
    def toggle_scanner():
        st.session_state["mostra_scanner"] = not st.session_state["mostra_scanner"]
    
    st.button(
        "📷 Scansiona Barcode" if not st.session_state["mostra_scanner"] else "❌ Chiudi Scanner",
        use_container_width=True,
        on_click=toggle_scanner,
        type="secondary"
    )
    
    # Bottone per aprire/chiudere scanner barcode
    if "mostra_scanner" not in st.session_state:
        st.session_state["mostra_scanner"] = False
    
    def toggle_scanner():
        st.session_state["mostra_scanner"] = not st.session_state["mostra_scanner"]
    
    st.button(
        "📷 Scansiona Barcode" if not st.session_state["mostra_scanner"] else "❌ Chiudi Scanner",
        use_container_width=True,
        on_click=toggle_scanner,
        type="secondary"
    )
    
    # Sezione scanner (visibile solo se attivata)
    if st.session_state["mostra_scanner"]:
        st.markdown("---")
        
        # Tabs per scegliere il metodo
        tab_manual, tab_photo = st.tabs(["✍️ Manuale", "📸 Foto"])
        
        with tab_manual:
            st.markdown("**Inserisci il codice barcode:**")
            
            col_input, col_search = st.columns([3, 1])
            
            with col_input:
                codice_manuale = st.text_input(
                    "Codice barcode", 
                    key="codice_manuale_input", 
                    label_visibility="collapsed",
                    placeholder="Scrivi il codice..."
                )
            
            with col_search:
                cerca_btn = st.button("🔍", use_container_width=True, key="cerca_manuale")
            
            if cerca_btn and codice_manuale:
                # Cerca articolo (case insensitive)
                articolo_trovato = next(
                    (a for a in articoli if str(a.get("Codice", "")).strip().upper() == str(codice_manuale).strip().upper()),
                    None
                )
                
                if articolo_trovato:
                    st.session_state["articolo_temp"] = articolo_trovato["Descrizione"]
                    st.session_state["mostra_scanner"] = False
                    st.success(f"✅ Articolo trovato: {articolo_trovato['Descrizione']}")
                    st.rerun()
                else:
                    st.error(f"❌ Codice `{codice_manuale}` non trovato")
                    st.write("📋 Esempi di codici nel database:")
                    for a in articoli[:8]:
                        st.write(f"• `{a.get('Codice', 'N/A')}` → {a['Descrizione'][:35]}")
        
        with tab_photo:
            st.markdown("**Carica o scatta una foto del barcode:**")
            
            # File uploader che supporta sia fotocamera che galleria
            barcode_file = st.file_uploader(
                "Scegli foto",
                type=['png', 'jpg', 'jpeg'],
                key="barcode_uploader",
                label_visibility="collapsed"
            )
            
            if barcode_file is not None:
                try:
                    from pyzbar import pyzbar
                    from PIL import Image, ImageEnhance
                    import io
                    
                    # Leggi immagine
                    image = Image.open(barcode_file)
                    st.image(image, caption="Foto caricata", width=300)
                    
                    with st.spinner("🔍 Analisi in corso..."):
                        # Prova diverse elaborazioni
                        results = []
                        
                        # 1. Immagine originale
                        results.extend(pyzbar.decode(image))
                        
                        # 2. Scala di grigi
                        gray = image.convert('L')
                        results.extend(pyzbar.decode(gray))
                        
                        # 3. Alto contrasto
                        enhancer = ImageEnhance.Contrast(gray)
                        high_contrast = enhancer.enhance(3.0)
                        results.extend(pyzbar.decode(high_contrast))
                        
                        # 4. Ridimensionata
                        w, h = image.size
                        resized = image.resize((w*2, h*2), Image.Resampling.LANCZOS)
                        results.extend(pyzbar.decode(resized))
                    
                    # Rimuovi duplicati
                    unique_codes = {}
                    for r in results:
                        code = r.data.decode('utf-8')
                        if code not in unique_codes:
                            unique_codes[code] = r.type
                    
                    if unique_codes:
                        st.success(f"✅ Trovati {len(unique_codes)} codici!")
                        
                        for code, barcode_type in unique_codes.items():
                            st.info(f"📊 {barcode_type}: **{code}**")
                            
                            # Cerca nell'inventario
                            articolo = next(
                                (a for a in articoli if str(a.get("Codice", "")).strip().upper() == code.strip().upper()),
                                None
                            )
                            
                            if articolo:
                                if st.button(f"✅ Usa: {articolo['Descrizione']}", key=f"use_{code}"):
                                    st.session_state["articolo_temp"] = articolo["Descrizione"]
                                    st.session_state["mostra_scanner"] = False
                                    st.rerun()
                            else:
                                st.warning(f"⚠️ Codice non trovato nel database")
                    else:
                        st.error("❌ Nessun barcode rilevato")
                        st.info("💡 Suggerimenti:\n- Assicurati che il barcode sia ben visibile\n- Buona illuminazione\n- Foto nitida e a fuoco\n- Prova con un'altra foto")
                
                except ImportError:
                    st.error("📦 Libreria pyzbar non disponibile")
                    st.info("Usa il metodo manuale nella tab '✍️ Manuale'")
                except Exception as e:
                    st.error(f"❌ Errore: {str(e)}")
        
        st.markdown("---")
        st.markdown("**Oppure usa lo scanner automatico:**")
        
        # Scanner HTML5 con QuaggaJS (supporto migliorato per alfanumerici)
        scanner_html = """
        <div id="scanner-container" style="width: 100%; max-width: 640px; margin: 0 auto;">
            <div id="interactive" class="viewport" style="width: 100%; height: 300px; border: 2px solid #4CAF50; border-radius: 8px; overflow: hidden; background: black;"></div>
            <div id="result" style="margin-top: 10px; padding: 10px; background: #f0f0f0; border-radius: 5px; text-align: center; font-size: 16px; font-weight: bold;">
                <span id="barcode-result">📸 Inquadra il barcode...</span>
            </div>
            <button id="stop-btn" style="margin-top: 10px; padding: 10px 20px; background: #f44336; color: white; border: none; border-radius: 5px; width: 100%; cursor: pointer;">
                ⏹️ Ferma Scanner
            </button>
        </div>
        
        <script src="https://cdn.jsdelivr.net/npm/@ericblade/quagga2/dist/quagga.min.js"></script>
        <script>
            let quaggaRunning = false;
            
            if (typeof Quagga !== 'undefined' && !quaggaRunning) {
                quaggaRunning = true;
                
                Quagga.init({
                    inputStream: {
                        name: "Live",
                        type: "LiveStream",
                        target: document.querySelector('#interactive'),
                        constraints: {
                            width: 640,
                            height: 480,
                            facingMode: "environment"
                        },
                    },
                    decoder: {
                        readers: [
                            "code_128_reader",  // Supporta alfanumerici
                            "code_39_reader",   // Supporta alfanumerici
                            "code_39_vin_reader",
                            "codabar_reader",
                            "ean_reader",
                            "ean_8_reader",
                            "upc_reader",
                            "upc_e_reader",
                            "i2of5_reader",
                            "2of5_reader"
                        ],
                        multiple: false
                    },
                    locate: true,
                    locator: {
                        halfSample: true,
                        patchSize: "medium"
                    },
                    numOfWorkers: 4,
                    frequency: 10
                }, function(err) {
                    if (err) {
                        console.log(err);
                        document.getElementById('barcode-result').innerHTML = "❌ Errore fotocamera";
                        return;
                    }
                    Quagga.start();
                    console.log("Scanner started");
                });

                let detectionCount = {};
                
                Quagga.onDetected(function(result) {
                    const code = result.codeResult.code;
                    const format = result.codeResult.format;
                    
                    // Conta rilevamenti per validazione
                    if (!detectionCount[code]) {
                        detectionCount[code] = 0;
                    }
                    detectionCount[code]++;
                    
                    // Mostra il codice rilevato
                    document.getElementById('barcode-result').innerHTML = 
                        "🔍 " + format + ": <strong>" + code + "</strong> (" + detectionCount[code] + "x)";
                    
                    // Conferma dopo 2 rilevamenti dello stesso codice
                    if (detectionCount[code] >= 2) {
                        document.getElementById('barcode-result').innerHTML = 
                            "✅ Codice confermato: <strong>" + code + "</strong>";
                        
                        // Feedback
                        if (navigator.vibrate) {
                            navigator.vibrate([100, 50, 100]);
                        }
                        
                        // Reset counter
                        detectionCount = {};
                    }
                });
                
                // Stop button
                document.getElementById('stop-btn').addEventListener('click', function() {
                    Quagga.stop();
                    quaggaRunning = false;
                    document.getElementById('barcode-result').innerHTML = "⏹️ Scanner fermato";
                });
            }
        </script>
        """
        
        import streamlit.components.v1 as components
        components.html(scanner_html, height=450)
        
        st.markdown("---")
    
    # Selezione manuale
    st.markdown("<b>Seleziona articolo</b>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([4, 1], gap="small")
    
    with col1:
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
                
                st.session_state["ordine_articoli"] = []
                st.session_state["note"] = ""
                st.session_state["ordine_inviato"] = True
                st.session_state["ultimo_id_ordine"] = id_ordine
        
        st.button(
            "📧 Invia ordine",
            type="primary",
            use_container_width=True,
            on_click=invio_completato
        )
        
        # Mostra messaggio di successo solo una volta
        if st.session_state.get("ordine_inviato", False):
            st.success(f"✅ Ordine #{st.session_state['ultimo_id_ordine']} inviato!")
            st.session_state["ordine_inviato"] = False

# ======================================================
# TAB 3 — ORDINI STORICI
# ======================================================
with tab_storico:
    # Filtra solo gli ordini creati dall'utente corrente
    ordini_utente = [o for o in ordini if o.get("DipendenteEmail", "").lower() == email.lower()]
    
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
            on_click=reinvia_ordine
        )