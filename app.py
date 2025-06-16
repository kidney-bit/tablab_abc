# app.py - Integra robô de download, extração de exames e envio ao Google Sheets

import streamlit as st
import os
from datetime import datetime, date

from robo_fmabc import executar_robo_fmabc
from extrator import executar_extrator_tabelado
from escrivao import enviar_para_google_sheets

st.set_page_config(page_title="tablab", layout="wide")
st.title("🧪 tablab abc")

# Menu lateral
aba = st.sidebar.radio("Escolha a funcionalidade:", [
    "⬇️ Download de exames",
    "📊 Extrair exames dos PDFs",
    "📤 Enviar exames para o Censo",
    "🐯 Tudo de uma vez"
])

# Funcionalidades separadas
if aba == "⬇️ Download de exames":
    executar_robo_fmabc()

elif aba == "📊 Extrair exames dos PDFs":
    executar_extrator_tabelado()

elif aba == "📤 Enviar exames para o Censo":
    if "df_exames" in st.session_state:
        url = st.text_input("📎 Cole aqui o link da planilha do Google Sheets:")

        hoje = date.today()
        if "data_ref" not in st.session_state:
            st.session_state["data_ref"] = hoje

        data_ref = st.date_input("📆 Escolha a data de referência para o envio:", value=st.session_state["data_ref"])
        st.session_state["data_ref"] = data_ref

        if st.button("📤 Enviar dados ao Censo"):
            progresso = st.progress(0)
            with st.spinner("⏳ Enviando dados para o Censo..."):
                sucesso = enviar_para_google_sheets(
                    st.session_state["df_exames"],
                    url,
                    data_referencia=data_ref,
                    barra_progresso=progresso
                )
            if sucesso:
                st.success("✅ Dados enviados com sucesso!")
            else:
                st.error("❌ Falha ao enviar os dados. Verifique o link e tente novamente.")
    else:
        st.warning("Nenhum exame extraído ainda. Por favor, realize a extração primeiro.")

# Execução automatizada
elif aba == "🐯 Tudo de uma vez":
    st.markdown("### 🐯 Execução Completa")
    st.info("Esta opção executa todo o processo: download → extração → envio ao Google Sheets")

    nomes = st.text_area("📋 Cole aqui os nomes dos pacientes (um por linha):")
    data_escolhida = st.date_input("📆 Data que será enviada ao Censo:", value=date.today())
    url = st.text_input("📎 Cole o link da planilha do Google Sheets:")

    if st.button("🚀 Executar Tudo"):
        # Validação dos campos
        if not nomes.strip():
            st.error("❌ Por favor, insira pelo menos um nome de paciente.")
            st.stop()

        if not url.strip():
            st.error("❌ Por favor, insira o link da planilha do Google Sheets.")
            st.stop()

        progresso = st.progress(0)

        try:
            # 1. Baixar PDFs
            st.info("🔽 Passo 1: Baixando PDFs de todos os exames disponíveis...")
            lista_nomes = [nome.strip() for nome in nomes.strip().splitlines() if nome.strip()]

            # Chama a função com a lista de nomes
            pasta_downloads = executar_robo_fmabc(nomes_pacientes=lista_nomes)

            if not pasta_downloads:
                st.error("❌ Falha no download dos PDFs.")
                st.stop()

            progresso.progress(0.33)

            # 2. Extrair exames da pasta criada
            st.info("📄 Passo 2: Extraindo exames da pasta de downloads...")

            df_exames = executar_extrator_tabelado(pasta_manual=pasta_downloads)

            if df_exames is None or df_exames.empty:
                st.error("❌ Nenhum exame foi extraído dos PDFs.")
                st.stop()

            st.session_state["df_exames"] = df_exames
            progresso.progress(0.66)

            # 3. Enviar ao Google Sheets apenas a data escolhida
            st.info("📤 Passo 3: Enviando exames filtrados por data ao Google Sheets...")

            sucesso = enviar_para_google_sheets(
                df_exames,
                url,
                data_referencia=data_escolhida,
                barra_progresso=progresso
            )
            progresso.progress(1.0)

            if sucesso:
                st.success("✅ Processo automatizado finalizado com sucesso!")
                st.info(f"📁 PDFs salvos em: {pasta_downloads}")
                st.info(f"📊 {len(df_exames)} exames processados")
            else:
                st.error("❌ Falha ao enviar os dados ao Google Sheets.")

        except Exception as e:
            st.error(f"❌ Erro durante execução: {e}")
            st.exception(e)  # Para debug, mostra o stack trace completo
