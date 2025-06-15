# app.py - Versão final corrigida para a VM

import streamlit as st
import os
from datetime import datetime

# Importações permanecem as mesmas
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

# Funcionalidades separadas (sem alterações aqui)
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

# ✅ SEÇÃO DE EXECUÇÃO AUTOMATIZADA CORRIGIDA
elif aba == "🤖 Rodar tudo (automático)":
    st.markdown("### 🤖 Execução Automatizada Completa")
    st.info("Esta opção executa todo o fluxo: download → extração → envio.")

    nomes = st.text_area("📋 Cole aqui os nomes dos pacientes (um por linha):")
    data_escolhida = st.date_input("📆 Data que será enviada ao Censo:")
    url = st.text_input("📎 Cole o link da planilha do Google Sheets:")

    if st.button("🚀 Executar Fluxo Completo"):
        # Validações
        if not nomes.strip() or not url.strip():
            st.error("❌ Por favor, preencha a lista de pacientes e o link da planilha.")
            st.stop()

        progresso = st.progress(0)

        try:
            # 1. Baixar PDFs
            with st.spinner("🔽 Passo 1: Baixando PDFs..."):
                lista_nomes = [n.strip() for n in nomes.strip().splitlines() if n.strip()]
                
                # ✅ Chama a função e CAPTURA O CAMINHO DE RETORNO
                pasta_downloads = executar_robo_fmabc(nomes_pacientes=lista_nomes)

                if not pasta_downloads:
                    st.error("❌ Falha no download dos PDFs. O robô não retornou uma pasta.")
                    st.stop()
            progresso.progress(0.33)

            # 2. Extrair exames da pasta retornada pelo robô
            with st.spinner("📄 Passo 2: Extraindo exames..."):
                # ✅ Usa a variável 'pasta_downloads' em vez de um caminho fixo
                df_exames = executar_extrator_tabelado(pasta_manual=pasta_downloads)
                
                if df_exames is None or df_exames.empty:
                    st.error("❌ Nenhum exame foi extraído dos PDFs.")
                    st.stop()
                
                st.session_state["df_exames"] = df_exames
            progresso.progress(0.66)

            # 3. Enviar ao Google Sheets
            with st.spinner("📤 Passo 3: Enviando para o Google Sheets..."):
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
            st.exception(e) # Mostra o erro detalhado para depuração
