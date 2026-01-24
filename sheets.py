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
def crea_ordine(credentials, dipendente_email, cliente_nome, articoli_ordine, note=""):
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
        dipendente_email
    ])

    # ORDINE ARTICOLI
    ws_oa = sh.worksheet("ordineArticoli")
    righe = ws_oa.get_all_records()
    next_id = max([r["IdOrdineArticolo"] for r in righe], default=0) + 1

    for item in articoli_ordine:
        ws_oa.append_row([
            next_id,
            id_ordine,
            item["IdArticolo"],
            item["Qtà"]
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

    # Map clienti e articoli
    clienti_map = {str(c["IdCliente"]): c["Nome"] for c in clienti}
    articoli_map = {str(a["IdArticolo"]): {
                        "Codice": a["Codice"],
                        "Descrizione": a["Descrizione"],
                        "UnitaMisura": a.get("UnitaMisura", "")
                    } for a in articoli}

    risultati = []

    for ordine in ordini:
        id_ordine = str(ordine["IdOrdine"])
        id_cliente = str(ordine["IdCliente"])
        data_str = ordine.get("Data", "")
        try:
            data_dt = datetime.strptime(data_str, "%Y-%m-%d %H:%M:%S")
        except:
            data_dt = datetime.min

        articoli_ordine = []
        for oa in ordini_articoli:
            if str(oa["IdOrdine"]) == id_ordine:
                art = articoli_map.get(str(oa["IdArticolo"]))
                if art:
                    articoli_ordine.append({
                        "Codice": art["Codice"],
                        "Descrizione": art["Descrizione"],
                        "Qtà": oa["Qtà"],
                        "UnitaMisura": art.get("UnitaMisura", "")
                    })

        risultati.append({
            "IdOrdine": id_ordine,
            "Cliente": clienti_map.get(id_cliente, "Sconosciuto"),
            "Data": data_str,
            "Data_dt": data_dt,  # per ordinamento
            "Note": ordine.get("Note", ""),
            "DipendenteEmail": ordine.get("DipendenteEmail", ""),
            "Articoli": articoli_ordine
        })

    # Ordina dal più recente al più vecchio
    risultati.sort(key=lambda x: x["Data_dt"], reverse=True)
    return risultati