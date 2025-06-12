# extrator.py

import fitz  # PyMuPDF
import re
import pandas as pd
import os

definir_padroes():
    return {
        "Creatinina": r"CREATININA.*?\n.*?([\d,\.]+)",
        "Ureia": r"UREIA.*?\n.*?([\d,\.]+)",
        "Bicarbonato": r"BICARBONATO.*?\n.*?([\d,\.]+)",
        "Sódio": r"S[ÓO]DIO.*?\n.*?([\d,\.]+)",
        "Potássio": r"POT[ÁA]SSIO.*?\n.*?([\d,\.]+)",
        "Magnésio": r"MAGN[ÉE]SIO.*?RESULTADO\s*:? *([\d,\.]+)",
        "Cálcio": r"C[ÁA]LCIO\s*(?!IONICO|I[ÔO]NICO).*?RESULTADO\s*:? *([\d,\.]+)",
        "Cálcio Iônico": r"C[ÁA]LCIO I[ÔO]NICO.*?RESULTADO\s*:? *([\d,\.]+)",
        "Fósforo": r"F[ÓO]SFORO.*?\n.*?([\d,\.]+)",
        "Hemoglobina": r"HEMOGLOBINA\s*:\s*([\d,\.]+)",
        "Plaquetas": r"PLAQUETAS.*?:\s*([\d,\.]+)",
        "Proteína C Reativa": r"PROTE[ÍI]NA C REATIVA.*?([\d,\.]+)",
    }

def extrair_texto_pdf(filepath):
    with fitz.open(filepath) as doc:
        return "\n".join(page.get_text() for page in doc)

def extrair_nome(texto):
    match = re.search(r"^\s*([A-Z\s]+)\nNome\s*:", texto, flags=re.MULTILINE)
    return match.group(1).strip().title() if match else "Paciente Desconhecido"

def extrair_data_amostra(texto):
    match = re.search(r"Amostra recebida em:\s*(\d{2}/\d{2}/\d{4})", texto)
    return match.group(1) if match else ""

def extrair_valores(texto, padroes):
    resultados = {}
    for exame, padrao in padroes.items():
        match = re.search(padrao, texto, re.IGNORECASE | re.DOTALL)
        resultados[exame] = match.group(1).replace(",", ".") if match else ""
    return resultados

def extrair_exames_dos_pdfs(pasta):
    padroes = definir_padroes()
    registros = []
    for arquivo in os.listdir(pasta):
        if arquivo.lower().endswith(".pdf"):
            try:
                filepath = os.path.join(pasta, arquivo)
                texto = extrair_texto_pdf(filepath)
                nome = extrair_nome(texto)
                data = extrair_data_amostra(texto)
                valores = extrair_valores(texto, padroes)
                registros.append({"Paciente": nome, "Data": data, **valores})
            except Exception:
                continue
    return pd.DataFrame(registros)
