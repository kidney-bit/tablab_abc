# escrivao.py - Envia dados para o Google Sheets com base em B1 de cada aba, consolidando exames por paciente e por data

import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import math
import unicodedata
import time
import re

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

CAMINHO_CREDENCIAIS = "/Users/kwayla/myp/tablab_abc/tablab_abc/tablab-abc-dd3a8b70d927.json"

ABAS_IGNORADAS = ["CENSO AUTOMÁTICO", "Modelo - Evoluções", "Modelo"]

COLUNAS_GOOGLE = [
    "Data", "Creatinina", "Ureia", "Bicarbonato", "Sódio", "Potássio", "Magnésio",
    "Cálcio", "Fósforo", "Hemoglobina", "Plaquetas", "Proteína C Reativa"
]

COLUNAS_PLANILHA = ["A"] + list("HIJKLMNOPQRST")  # Total de 13 colunas

def conectar_google_sheets():
    try:
        creds = Credentials.from_service_account_file(CAMINHO_CREDENCIAIS, scopes=SCOPES)
        return gspread.authorize(creds)
    except Exception as e:
        print(f"Erro na autenticação: {e}")
        return None

def abrir_planilha_por_url(gc, url):
    try:
        return gc.open_by_url(url)
    except Exception as e:
        print(f"Erro ao abrir a planilha: {e}")
        return None

def normalizar_nome(nome):
    return unicodedata.normalize("NFKD", nome).encode("ASCII", "ignore").decode("utf-8").lower().strip()

def enviar_para_google_sheets(df, url, datas_filtradas=None, barra_progresso=None):
    gc = conectar_google_sheets()
    if not gc:
        return False

    planilha = abrir_planilha_por_url(gc, url)
    if not planilha:
        return False

    df["Data"] = pd.to_datetime(df["Data"], errors="coerce").dt.date
    if datas_filtradas:
        datas_filtradas_set = {pd.to_datetime(d).date() for d in datas_filtradas}
        df = df[df["Data"].isin(datas_filtradas_set)]

    df_grouped = df.groupby(["Paciente", "Data"])[COLUNAS_GOOGLE[1:]].agg(
        lambda x: pd.to_numeric(x, errors='coerce').max(skipna=True)).reset_index()
    df_grouped["Data"] = df_grouped["Data"].apply(lambda d: d.strftime("%d/%m/%Y"))

    nomes_df = df_grouped["Paciente"].dropna().tolist()
    nomes_normalizados = {normalizar_nome(n): n for n in nomes_df}

    total_preenchido = 0
    total_abas = 0

    todas_abas = []
    for i in range(1, 71):
        aba_nome = f"{i:02d}"
        try:
            aba = planilha.worksheet(aba_nome)
            todas_abas.append(aba)
        except gspread.exceptions.WorksheetNotFound:
            print(f"❌ Aba {aba_nome} não encontrada.")
            continue

    total_aba_count = len(todas_abas)

    for idx_aba, aba in enumerate(todas_abas):
        print(f"🔁 Iniciando processamento da aba {aba.title}")
        try:
            nome_aba = aba.title
            if nome_aba in ABAS_IGNORADAS:
                print(f"⏩ Aba ignorada: {nome_aba}")
                continue

            try:
                faixa_nome = aba.batch_get(["B1:D1"])[0][0]
                time.sleep(1)  # ⚠️ pausa após leitura
                b1_value = faixa_nome if isinstance(faixa_nome, str) else next((cel for cel in faixa_nome if cel), None)
                if not b1_value:
                    print(f"⚠️ Nenhum nome encontrado na faixa B1:D1 na aba {nome_aba}")
                    continue
                nome_paciente_b1 = b1_value.strip().title()
            except Exception as e:
                print(f"⚠️ Erro ao acessar B1:D1 na aba {nome_aba}: {e}")
                continue

            print(f"\n🧪 Verificando aba: {nome_aba} (B1 = {nome_paciente_b1})")
            nome_b1_normalizado = normalizar_nome(nome_paciente_b1)

            if nome_b1_normalizado in nomes_normalizados:
                nome_correto = nomes_normalizados[nome_b1_normalizado]
                print(f"✅ Nome exato encontrado: {nome_correto}")
            else:
                print(f"⚠️ Nome não encontrado: {nome_paciente_b1}")
                continue

            dados_paciente = df_grouped[df_grouped["Paciente"] == nome_correto]
            if dados_paciente.empty:
                print(f"⚠️ Dados agrupados estão vazios para: {nome_correto}")
                continue

            dados_paciente = dados_paciente[COLUNAS_GOOGLE]
            print(f"🔎 Linhas a escrever: {len(dados_paciente)}")

            valores_aba = aba.get_all_values()
            time.sleep(0.6)  # ⚠️ leitura também conta no limite
            linha_destino = len(valores_aba) + 1

            for _, linha in dados_paciente.iterrows():
                valores_formatados = []
                for col in COLUNAS_GOOGLE:
                    valor = linha.get(col, "")
                    if pd.isna(valor) or valor in [float("inf"), float("-inf")] or (isinstance(valor, str) and valor.lower() == "nan"):
                        valores_formatados.append("")
                    else:
                        valores_formatados.append(str(valor))

                valores_formatados = (valores_formatados + [""] * 13)[:13]

                try:
                    aba.update_acell(f"A{linha_destino}", valores_formatados[0])
                    time.sleep(0.6)  # ⚠️ pausa após escrita

                    range_escreve = f"H{linha_destino}:T{linha_destino}"
                    valores_exames = [valores_formatados[1:13]]
                    aba.update(range_escreve, valores_exames)
                    time.sleep(0.6)  # ⚠️ pausa após escrita

                    total_preenchido += 1
                    linha_destino += 1
                except Exception as e:
                    print(f"❌ Erro ao atualizar aba {nome_aba}: {e}")
                    continue

            total_abas += 1
            progresso = int((total_abas / total_aba_count) * 100)
            print(f"📊 Progresso: {progresso}%")
            if barra_progresso:
                barra_progresso.progress(progresso / 100)

            time.sleep(1.2)  # ⚠️ pausa entre abas

        except Exception as e:
            print(f"❌ Erro inesperado ao processar a aba {aba.title}: {e}")
            continue

    print(f"\n📄 Total de abas processadas: {total_abas}")
    print(f"✔️ Total de linhas preenchidas: {total_preenchido}")
    return True

__all__ = ["enviar_para_google_sheets"]
