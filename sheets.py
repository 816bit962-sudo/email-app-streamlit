import gspread
from datetime import datetime

SHEET_KEY = "1YHWrkehjx5qAuAWuNbNJye8zUO0vgjFahzPQS-FxaiM"

# ===============================
# CLIENTI
def get_clienti(credentials):
    gc = gspread.authorize(credentials)
    sh = gc.open_by_key(SHEET_KEY)
    return sh.worksheet("clienti").get_all_records()

# ===============================
# ARTICOLI
def get_articoli(credentials):
    gc = gspread.authorize(credentials)
    sh = gc.open_by_key(SHEET_KEY)
    return sh.worksheet("articoli").get_all_records()

# ===============================
# DESTINATARI
def get_destinatari(credentials):
    gc = gspread.authorize(credentials)
    sh = gc.open_by_key(SHEET_KEY)
    return sh.worksheet("destinatari").get_all_records()

# ===============================
# CREA ORDINE
def crea_ordine(credentials, dipendente_email, cliente_nome, articoli_ordine, note="", stato="inviato"):
    gc = gspread.authorize(credentials)
    sh = gc.open_by_key(SHEET_KEY)
    
    # CLIENTE
    ws_clienti = sh.worksheet("clienti")
    clienti = ws_clienti.get_all_records()
    cliente = next(c for c in clienti if c["Nome"] == cliente_nome)
    id_cliente = cliente["IdCliente"]
    
    # ORDINI
    ws_ordini = sh.worksheet("ordini")
    ordini = ws_ordini.get_all_records()
    id_ordine = max([o["IdOrdine"] for o in ordini], default=0) + 1
    
    ws_ordini.append_row([
        id_ordine,
        id_cliente,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        note,
        dipendente_email,
        stato  # Nuovo campo: "bozza" o "inviato"
    ])
    
    # ORDINE ARTICOLI
    ws_oa = sh.worksheet("ordineArticoli")
    righe = ws_oa.get_all_records()
    next_id = max([r["IdOrdineArticolo"] for r in righe], default=0) + 1
    
    for item in articoli_ordine:
        # Gestisci IdArticolo vuoto o non valido
        id_articolo_str = str(item.get("IdArticolo", "")).strip()
        if not id_articolo_str:
            continue  # Salta articoli senza IdArticolo valido
        
        try:
            id_articolo = int(id_articolo_str)
        except ValueError:
            continue  # Salta se non è convertibile a int
        
        ws_oa.append_row([
            next_id,
            id_ordine,
            id_articolo,
            int(item["Qtà"])
        ])
        next_id += 1
    
    return id_ordine

# ===============================
# ORDINI STORICI
def get_ordini(credentials):
    gc = gspread.authorize(credentials)
    sh = gc.open_by_key(SHEET_KEY)
    
    ws_ordini = sh.worksheet("ordini")
    ws_oa = sh.worksheet("ordineArticoli")
    ws_clienti = sh.worksheet("clienti")
    ws_articoli = sh.worksheet("articoli")
    
    ordini = ws_ordini.get_all_records()
    ordini_articoli = ws_oa.get_all_records()
    clienti = ws_clienti.get_all_records()
    articoli = ws_articoli.get_all_records()
    
    # Map clienti e articoli con conversione sicura
    clienti_map = {}
    for c in clienti:
        try:
            clienti_map[int(c["IdCliente"])] = c["Nome"]
        except (ValueError, KeyError):
            continue
    
    articoli_map = {}
    for a in articoli:
        try:
            articoli_map[int(a["IdArticolo"])] = {
                "Codice": a["Codice"],
                "Descrizione": a["Descrizione"],
                "UnitaMisura": a.get("UnitaMisura", "")
            }
        except (ValueError, KeyError):
            continue
    
    risultati = []
    for ordine in ordini:
        id_ordine = str(ordine["IdOrdine"])
        
        try:
            id_cliente = int(ordine["IdCliente"])
        except (ValueError, KeyError):
            id_cliente = 0
        
        data_str = ordine.get("Data", "")
        
        try:
            data_dt = datetime.strptime(data_str, "%Y-%m-%d %H:%M:%S")
        except:
            data_dt = datetime.min
        
        articoli_ordine = []
        for oa in ordini_articoli:
            if str(oa["IdOrdine"]) == id_ordine:
                try:
                    id_articolo = int(oa["IdArticolo"])
                    art = articoli_map.get(id_articolo)
                    if art:
                        articoli_ordine.append({
                            "Codice": art["Codice"],
                            "Descrizione": art["Descrizione"],
                            "Qtà": oa["Qtà"],
                            "UnitaMisura": art.get("UnitaMisura", "")
                        })
                except (ValueError, KeyError):
                    continue
        
        risultati.append({
            "IdOrdine": id_ordine,
            "Cliente": clienti_map.get(id_cliente, "Sconosciuto"),
            "IdCliente": id_cliente,
            "Data": data_str,
            "Data_dt": data_dt,
            "Note": ordine.get("Note", ""),
            "DipendenteEmail": ordine.get("DipendenteEmail", ""),
            "Stato": ordine.get("Stato", "inviato"),  # Default "inviato" per vecchi ordini
            "Articoli": articoli_ordine
        })
    
    # Ordina dal più recente al più vecchio
    risultati.sort(key=lambda x: x["Data_dt"], reverse=True)
    
    return risultati

# ===============================
# AGGIORNA ORDINE
def aggiorna_ordine(credentials, id_ordine, cliente_nome, articoli_ordine, note="", stato="bozza"):
    gc = gspread.authorize(credentials)
    sh = gc.open_by_key(SHEET_KEY)
    
    # CLIENTE
    ws_clienti = sh.worksheet("clienti")
    clienti = ws_clienti.get_all_records()
    cliente = next(c for c in clienti if c["Nome"] == cliente_nome)
    id_cliente = cliente["IdCliente"]
    
    # AGGIORNA ORDINE
    ws_ordini = sh.worksheet("ordini")
    ordini = ws_ordini.get_all_records()
    
    # Trova la riga dell'ordine (header + 1 + indice)
    riga_ordine = None
    for idx, ordine in enumerate(ordini, start=2):  # start=2 perché row 1 è l'header
        if str(ordine["IdOrdine"]) == str(id_ordine):
            riga_ordine = idx
            break
    
    if riga_ordine:
        # Aggiorna i campi dell'ordine (colonne: IdOrdine, IdCliente, Data, Note, DipendenteEmail, Stato)
        ws_ordini.update(f"B{riga_ordine}:F{riga_ordine}", [[
            id_cliente,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            note,
            ordini[riga_ordine-2]["DipendenteEmail"],  # Mantieni l'email originale
            stato
        ]])
    
    # ELIMINA VECCHI ARTICOLI
    ws_oa = sh.worksheet("ordineArticoli")
    righe_oa = ws_oa.get_all_records()
    
    # Trova tutte le righe da eliminare (in ordine inverso per non sballare gli indici)
    righe_da_eliminare = []
    for idx, oa in enumerate(righe_oa, start=2):
        if str(oa["IdOrdine"]) == str(id_ordine):
            righe_da_eliminare.append(idx)
    
    # Elimina dal basso verso l'alto
    for riga in sorted(righe_da_eliminare, reverse=True):
        ws_oa.delete_rows(riga)
    
    # AGGIUNGI NUOVI ARTICOLI
    righe_oa_aggiornate = ws_oa.get_all_records()
    next_id = max([r["IdOrdineArticolo"] for r in righe_oa_aggiornate], default=0) + 1
    
    for item in articoli_ordine:
        id_articolo_str = str(item.get("IdArticolo", "")).strip()
        if not id_articolo_str:
            continue
        
        try:
            id_articolo = int(id_articolo_str)
        except ValueError:
            continue
        
        ws_oa.append_row([
            next_id,
            id_ordine,
            id_articolo,
            int(item["Qtà"])
        ])
        next_id += 1
    
    return id_ordine