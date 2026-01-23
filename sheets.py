import gspread
from datetime import datetime

SHEET_KEY = "1YHWrkehjx5qAuAWuNbNJye8zUO0vgjFahzPQS-FxaiM"

# ===============================
# CLIENTI
def get_clienti(credentials):
    gc = gspread.authorize(credentials)
    sh = gc.open_by_key(SHEET_KEY)
    ws = sh.worksheet("clienti")
    return ws.get_all_records()

# ===============================
# ARTICOLI
def get_articoli(credentials):
    gc = gspread.authorize(credentials)
    sh = gc.open_by_key(SHEET_KEY)
    ws = sh.worksheet("articoli")
    return ws.get_all_records()

# ===============================
# DESTINATARI
def get_destinatari(credentials):
    gc = gspread.authorize(credentials)
    sh = gc.open_by_key(SHEET_KEY)
    ws = sh.worksheet("destinatari")
    records = ws.get_all_records()
    return [r["Destinatario"] for r in records if r.get("Destinatario")]

# ===============================
# CREA ORDINE
def crea_ordine(credentials, dipendente_email, cliente_nome, articoli_ordine, note=""):
    gc = gspread.authorize(credentials)
    sh = gc.open_by_key(SHEET_KEY)

    # Cliente
    ws_clienti = sh.worksheet("clienti")
    clienti = ws_clienti.get_all_records()
    cliente = next(c for c in clienti if c["Nome"] == cliente_nome)
    id_cliente = cliente["IdCliente"]

    # Ordine
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

    # OrdineArticoli
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
