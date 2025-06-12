# app.py

import streamlit as st
from robô_fmabc import executar_robo_fmabc
from extrator import extrair_exames_dos_pdfs

st.set_page_config(layout="wide")
st.title("🧬 Robô FMABC + Tabelador de Exames")

lista_nomes = st.text_area("📋 Cole aqui a lista de nomes dos pacientes (um por linha):")

if st.button("🚀 Iniciar robô e extrair exames"):
    if not lista_nomes.strip():
        st.warning("⚠️ Por favor, cole ao menos um nome.")
    else:
        nomes = lista_nomes.strip().splitlines()
        pasta_pdf = executar_robo_fmabc(nomes)  # <- salva e retorna o caminho final

        st.success(f"✅ PDFs baixados em: `{pasta_pdf}`")

        df = extrair_exames_dos_pdfs(pasta_pdf)

        if not df.empty:
            st.markdown("### 📊 Exames extraídos:")
            st.dataframe(df)
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Baixar CSV", data=csv, file_name="exames_extraidos.csv", mime="text/csv")
        else:
            st.info("Nenhum exame encontrado nos PDFs.")
