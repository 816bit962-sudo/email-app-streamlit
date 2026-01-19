import gspread
from google.oauth2.credentials import Credentials
import streamlit as st
from datetime import datetime

SHEET_KEY = "1YHWrkehjx5qAuAWuNbNJye8zUO0vgjFahzPQS-FxaiM"

def get_clienti(credentials):
    gc = gspread.authorize(credentials)
    sh = gc.open_by_key(SHEET_KEY)
    ws = sh.worksheet("clienti")
    rows = ws.get_all_records()
    return rows

def get_articoli(credentials):
    gc = gspread.authorize(credentials)
    sh = gc.open_by_key(SHEET_KEY)
    ws = sh.worksheet("articoli")
    rows = ws.get_all_records()
    return rows

def crea_ordine(credentials, dipendente_email, cliente_nome, articoli_ordine, cantiere="Sede"):
    gc = gspread.authorize(credentials)
    sh = gc.open_by_key(SHEET_KEY)

    # 1️⃣ Trova IdCliente
    ws_clienti = sh.worksheet("clienti")
    clienti = ws_clienti.get_all_records()
    cliente = next(c for c in clienti if c["Nome"] == cliente_nome)
    id_cliente = cliente["IdCliente"]

    # 2️⃣ Crea IdOrdine
    ws_ordini = sh.worksheet("ordini")
    ordini = ws_ordini.get_all_records()
    id_ordine = max([o["IdOrdine"] for o in ordini], default=0) + 1

    # 3️⃣ Scrive ordine
    ws_ordini.append_row([id_ordine, id_cliente, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), cantiere, dipendente_email])

    # 4️⃣ Scrive ordineArticoli
    ws_ordine_articoli = sh.worksheet("ordineArticoli")
    ordine_articoli_rows = ws_ordine_articoli.get_all_records()
    next_id = max([r["IdOrdineArticolo"] for r in ordine_articoli_rows], default=0) + 1

    for item in articoli_ordine:
        ws_ordine_articoli.append_row([next_id, id_ordine, item["IdArticolo"], item["Quantita"]])
        next_id += 1

    return id_ordine
