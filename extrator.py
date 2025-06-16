# extrator.py - Versão híbrida para uso em Streamlit e via chamada externa

import fitz  # PyMuPDF
import re
import pandas as pd
import os
import streamlit as st
from datetime import datetime, timedelta

definir_padroes = lambda: {
    "Creatinina": r"CREATININA.*?\n.*?([\d,\.]+)",
    "Ureia": r"UR[ÉE]IA.*?\n.*?([\d,\.]+)",
    "Bicarbonato": r"BICARBONATO.*?\n.*?([\d,\.]+)",
    "Sódio": r"S[ÓO]DIO.*?\n.*?([\d,\.]+)",
    "Potássio": r"POT[ÁA]SSIO.*?\n.*?([\d,\.]+)",
    "Magnésio": r"MAGN[ÉE]SIO.*?RESULTADO\s*:?.*?([\d,\.]+)",
    "Cálcio": r"C[ÁA]LCIO\s*(?!IONICO|I[ÔO]NICO).*?RESULTADO\s*:?[\s\n]*([\d,\.]+)",
    "Cálcio Iônico": r"C[ÁA]LCIO I[ÔO]NICO.*?RESULTADO\s*:?.*?([\d,\.]+)",
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
    match = re.search(r"Amostra recebida em:\s*(\d{2}/\d{2}/\d{4})\s+as\s+(\d{2})h\s+(\d{2})min", texto)
    if match:
        data_str = match.group(1)
        hora = match.group(2)
        minuto = match.group(3)
        try:
            return datetime.strptime(f"{data_str} {hora}:{minuto}", "%d/%m/%Y %H:%M")
        except ValueError:
            return None
    return None

def extrair_valores(texto, padroes):
    resultados = {}
    for exame, padrao in padroes.items():
        match = re.search(padrao, texto, re.IGNORECASE | re.DOTALL)
        resultados[exame] = match.group(1).replace(",", ".") if match else ""

    if resultados.get("Cálcio Iônico"):
        resultados["Cálcio"] = resultados["Cálcio Iônico"]
    elif resultados.get("Cálcio"):
        resultados["Cálcio"] = resultados["Cálcio"] + " (t)"
    resultados.pop("Cálcio Iônico", None)
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
    df = pd.DataFrame(registros)
    df = df[df["Data"].notna()]
    return df

def executar_extrator_tabelado(pasta_manual=None):
    st.subheader("📊 Extração de exames")

    pasta_padrao = "/home/karolinewac/tablab_abc/pdfs_abc"

    if pasta_manual:
        df = extrair_exames_dos_pdfs(pasta_manual)
        if not df.empty:
            st.session_state["df_exames"] = df
        return df

    subpastas = sorted([f.name for f in os.scandir(pasta_padrao) if f.is_dir()], reverse=True)

    if not subpastas:
        st.warning("Nenhuma subpasta encontrada com PDFs.")
        return

    escolha = st.selectbox("Escolha a subpasta com os PDFs:", subpastas)

    if st.button("🔍 Processar PDFs dessa pasta"):
        caminho_pdfs = os.path.join(pasta_padrao, escolha)
        df = extrair_exames_dos_pdfs(caminho_pdfs)

        if df.empty:
            st.warning("Nenhum exame foi extraído dos PDFs.")
            return

        st.session_state["df_exames"] = df
        st.session_state["filtros_ativos"] = True
        st.success("✅ Extração concluída com sucesso.")

    if "df_exames" in st.session_state:
        df = st.session_state["df_exames"]

        st.markdown("---")
        st.markdown("### 🔍 Filtros")

        hoje = pd.to_datetime(datetime.now().date())
        ontem = hoje - timedelta(days=1)

        if "datas_escolhidas" not in st.session_state:
            st.session_state["datas_escolhidas"] = (ontem.date(), hoje.date())

        datas_escolhidas = st.date_input(
            "Filtrar por intervalo de datas:",
            value=st.session_state["datas_escolhidas"]
        )

        if isinstance(datas_escolhidas, tuple):
            data_hoje = pd.to_datetime(datas_escolhidas[1])
            data_ontem = data_hoje - timedelta(days=1)
            inicio_ontem = pd.to_datetime(f"{data_ontem.date()} 11:30")
            fim_hoje = pd.to_datetime(f"{data_hoje.date()} 23:59")

            df = df[(df["Data"] >= inicio_ontem) & (df["Data"] <= fim_hoje)]
            st.session_state["datas_escolhidas"] = datas_escolhidas

        nomes = sorted(df["Paciente"].dropna().unique())
        filtro_nome = st.multiselect("Filtrar por nome do paciente:", nomes)
        if filtro_nome:
            df = df[df["Paciente"].isin(filtro_nome)]

        if st.button("🔁 Limpar filtros"):
            st.session_state["datas_escolhidas"] = (ontem.date(), hoje.date())
            filtro_nome.clear()
            st.rerun()

        st.dataframe(df, use_container_width=True)

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Baixar CSV", data=csv, file_name="exames_filtrados.csv", mime="text/csv")
