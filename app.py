# app.py - Integra robô de download, extração de exames e envio ao Google Sheets

import streamlit as st
import os
from datetime import datetime

from robo_fmabc import executar_robo_fmabc
from extrator import executar_extrator_tabelado
from escrivao import enviar_para_google_sheets

st.set_page_config(page_title="tablab", layout="wide")
st.title("🧪 tablab abc")

# Menu lateral
aba = st.sidebar.radio("Escolha a funcionalidade:", [
    "⬇️ Baixar PDFs",
    "📊 Extrair exames dos PDFs",
    "📤 Enviar exames para o Censo",
    "🤖 Rodar tudo (automático)"
])

# Funcionalidades separadas
if aba == "⬇️ Baixar PDFs":
    executar_robo_fmabc()

elif aba == "📊 Extrair exames dos PDFs":
    executar_extrator_tabelado()

elif aba == "📤 Enviar exames para o Censo":
    if "df_exames" in st.session_state:
        url = st.text_input("📎 Cole aqui o link da planilha do Google Sheets:")
        datas_unicas = sorted(st.session_state["df_exames"]["Data"].dropna().unique())
        datas_selecionadas = st.multiselect("📆 Selecione as datas a enviar:", options=datas_unicas)

        if st.button("🚀 Enviar para o Censo"):
            progresso = st.progress(0)
            with st.spinner("⏳ Enviando dados para o Censo..."):
                sucesso = enviar_para_google_sheets(
                    st.session_state["df_exames"],
                    url,
                    datas_filtradas=datas_selecionadas,
                    barra_progresso=progresso
                )
            if sucesso:
                st.success("✅ Dados enviados com sucesso!")
            else:
                st.error("❌ Falha ao enviar os dados. Verifique o link e tente novamente.")
    else:
        st.warning("Nenhum exame extraído ainda. Por favor, realize a extração primeiro.")

# Execução automatizada
elif aba == "🤖 Rodar tudo (automático)":
    st.markdown("")

    nomes = st.text_area("📋 Cole aqui os nomes dos pacientes (um por linha):")
    data_escolhida = st.date_input("📆 Data que será enviada ao Censo:")
    url = st.text_input("📎 Cole o link da planilha do Google Sheets:")

    if st.button("🚀 executar"):
        progresso = st.progress(0)

        try:
            # 1. Baixar PDFs
            with st.spinner("🔽 Passo 1: Baixando PDFs de todos os exames disponíveis..."):
                lista_nomes = nomes.strip().splitlines()
                executar_robo_fmabc(nomes_pacientes=lista_nomes)
            progresso.progress(0.33)

            # 2. Identificar última pasta e extrair exames
            with st.spinner("📄 Passo 2: Extraindo exames da pasta mais recente..."):
                pasta_base = os.path.join(os.path.dirname(__file__), "pdfs_abc")
                subpastas = sorted(
                    [f for f in os.listdir(pasta_base) if os.path.isdir(os.path.join(pasta_base, f))],
                    reverse=True
                )
                if not subpastas:
                    st.error("❌ Nenhuma pasta encontrada com PDFs.")
                    st.stop()

                ultima_pasta = os.path.join(pasta_base, subpastas[0])
                df_exames = executar_extrator_tabelado(pasta_manual=ultima_pasta)
                st.session_state["df_exames"] = df_exames
            progresso.progress(0.66)

            # 3. Enviar ao Google Sheets apenas a data escolhida
            with st.spinner("📤 Passo 3: Enviando exames filtrados por data ao Google Sheets..."):
                sucesso = enviar_para_google_sheets(
                    df_exames,
                    url,
                    datas_filtradas=[data_escolhida],
                    barra_progresso=progresso
                )
            progresso.progress(1.0)

            if sucesso:
                st.success("✅ Processo automatizado finalizado com sucesso!")
            else:
                st.error("❌ Falha ao enviar os dados ao Google Sheets.")

        except Exception as e:
            st.error(f"❌ Erro durante execução: {e}")
