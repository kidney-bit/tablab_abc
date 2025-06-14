# app.py - Integra robô de download, extração de exames e envio ao Google Sheets

import streamlit as st
from robo_fmabc import executar_robo_fmabc
from extrator import executar_extrator_tabelado
from escrivao import enviar_para_google_sheets

st.set_page_config(page_title="tablab", layout="wide")
st.title("🧪 tablab")

# Menu lateral
aba = st.sidebar.radio("Escolha a funcionalidade:", [
    "⬇️ Baixar PDFs",
    "📊 Extrair exames dos PDFs",
    "📤 Enviar exames para o Censo"
])

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
