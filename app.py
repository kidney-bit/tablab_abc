# app.py - Integra robô de download e extração de exames

import streamlit as st
from robo_fmabc import executar_robo_fmabc
from extrator import executar_extrator_tabelado  # nome correto do módulo

st.set_page_config(page_title="Automação FMABC Completa", layout="wide")
st.title("🧪 Automação Completa: FMABC")

aba = st.sidebar.radio("Escolha a funcionalidade:", [
    "⬇️ Baixar PDFs dos pacientes",
    "📊 Extrair exames dos PDFs salvos"
])

if aba == "⬇️ Baixar PDFs dos pacientes":
    executar_robo_fmabc()

elif aba == "📊 Extrair exames dos PDFs salvos":
    executar_extrator_tabelado()
