# app.py - Versão final e corrigida

import streamlit as st
import os
from datetime import datetime

# Importa as duas funções necessárias de robo_fmabc
from robo_fmabc import executar_robo_fmabc, executar_downloads_automatico
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

# --- Funcionalidades separadas ---

# A aba "Baixar PDFs" continua usando a função original para renderizar a UI
if aba == "⬇️ Baixar PDFs":
    executar_robo_fmabc()

elif aba == "📊 Extrair exames dos PDFs":
    executar_extrator_tabelado()

elif aba == "📤 Enviar exames para o Censo":
    if "df_exames" in st.session_state:
        url = st.text_input("📎 Cole aqui o link da planilha do Google Sheets:")
        # Garante que a coluna 'Data' exista antes de tentar acessá-la
        if "Data" in st.session_state["df_exames"].columns:
            datas_unicas = sorted(st.session_state["df_exames"]["Data"].dropna().unique())
            datas_selecionadas = st.multiselect("📆 Selecione as datas a enviar:", options=datas_unicas)
        else:
            datas_selecionadas = []
            st.warning("Coluna 'Data' não encontrada nos exames extraídos.")

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

# --- Execução automatizada ---

elif aba == "🤖 Rodar tudo (automático)":
    st.markdown("### 🤖 Execução Automatizada Completa")
    st.info("Esta opção executa todo o fluxo: download → extração → envio ao Google Sheets")

    nomes = st.text_area("📋 Cole aqui os nomes dos pacientes (um por linha):")
    data_escolhida = st.date_input("📆 Data que será enviada ao Censo:")
    url = st.text_input("📎 Cole o link da planilha do Google Sheets:")

    if st.button("🚀 Executar Fluxo Completo"):
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
            
            # ✅ CORREÇÃO: Chamando a função de automação diretamente
            pasta_downloads = executar_downloads_automatico(
                nomes_pacientes=lista_nomes,
                modo_headless=True
            )
            
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
                datas_filtradas=[data_escolhida],
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
            st.exception(e)
