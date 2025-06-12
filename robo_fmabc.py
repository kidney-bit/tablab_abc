import streamlit as st
import fitz  # PyMuPDF
import re
import pandas as pd
import tempfile

st.set_page_config(layout="wide")
st.title("🧪 Conversor de PDF + Extrator de Exames (modo local)")

# Lista de exames-alvo e padrões associados
EXAMES_PADROES = {
    "Creatinina": r"CREATININA.*?\n.*?([\d,\.]+)",
    "Ureia": r"UREIA.*?\n.*?([\d,\.]+)",
    "Bicarbonato": r"BICARBONATO.*?\n.*?([\d,\.]+)",
    "Sódio": r"S[ÓO]DIO.*?\n.*?([\d,\.]+)",
    "Potássio": r"POT[ÁA]SSIO.*?\n.*?([\d,\.]+)",
    "Magnésio": r"MAGN[ÉE]SIO.*?RESULTADO\s*:?\s*([\d,\.]+)",
    "Cálcio": r"C[ÁA]LCIO\s*(?!IONICO|I[ÔO]NICO).*?RESULTADO\s*:?\s*([\d,\.]+)",
    "Cálcio Iônico": r"C[ÁA]LCIO I[ÔO]NICO.*?RESULTADO\s*:?\s*([\d,\.]+)",
    "Fósforo": r"F[ÓO]SFORO.*?\n.*?([\d,\.]+)",
    "Hemoglobina": r"HEMOGLOBINA\s*:\s*([\d,\.]+)",
    "Plaquetas": r"PLAQUETAS.*?:\s*([\d,\.]+)",
    "Proteína C Reativa": r"PROTE[ÍI]NA C REATIVA.*?([\d,\.]+)",
}

def extrair_texto_pdf(file_bytes):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(file_bytes.read())
        tmp_path = tmp_file.name

    with fitz.open(tmp_path) as doc:
        texto = "\n".join(page.get_text() for page in doc)
    return texto

def extrair_nome(texto):
    match = re.search(r"^\s*([A-Z\s]+)\nNome\s*:", texto, flags=re.MULTILINE)
    return match.group(1).strip().title() if match else "Paciente Desconhecido"

def extrair_data_amostra(texto):
    match = re.search(r"Amostra recebida em:\s*(\d{2}/\d{2}/\d{4})", texto)
    return match.group(1) if match else ""

def extrair_valores(texto):
    resultados = {}
    for exame, padrao in EXAMES_PADROES.items():
        match = re.search(padrao, texto, re.IGNORECASE | re.DOTALL)
        resultados[exame] = match.group(1).replace(",", ".") if match else ""
    return resultados

uploaded_files = st.file_uploader("📎 Arraste e solte seus PDFs laboratoriais aqui", type="pdf", accept_multiple_files=True)

if uploaded_files and st.button("🔍 Processar PDFs"):
    tabela = []

    for pdf in uploaded_files:
        try:
            texto = extrair_texto_pdf(pdf)
            nome = extrair_nome(texto)
            data = extrair_data_amostra(texto)
            valores = extrair_valores(texto)
            linha = {"Paciente": nome, "Data": data, **valores}
            tabela.append(linha)
        except Exception as e:
            st.error(f"Erro ao processar {pdf.name}: {e}")

    if tabela:
        df = pd.DataFrame(tabela)
        st.success("✅ Extração concluída com sucesso.")
        st.dataframe(df)

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Baixar CSV", data=csv, file_name="exames_extraidos.csv", mime="text/csv")
