# escrivao.py - Otimizado para rodar na VM Linux e buscar nomes pela aba "CENSO AUTOMÁTICO" (colunas A e D)

import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import unicodedata
import time
from datetime import datetime, timedelta

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

CAMINHO_CREDENCIAIS = "/home/karolinewac/tablab-abc-dd3a8b70d927.json"

ABAS_IGNORADAS = ["CENSO AUTOMÁTICO", "Modelo - Evoluções", "Modelo"]

COLUNAS_GOOGLE = [
    "Data", "Creatinina", "Ureia", "Bicarbonato", "Sódio", "Potássio", "Magnésio",
    "Cálcio", "Fósforo", "Hemoglobina", "Plaquetas", "Proteína C Reativa"
]

COLUNAS_PLANILHA = ["A"] + list("HIJKLMNOPQRST")

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

def enviar_para_google_sheets(df, url, data_referencia=None, barra_progresso=None):
    gc = conectar_google_sheets()
    if not gc:
        return False

    planilha = abrir_planilha_por_url(gc, url)
    if not planilha:
        return False

    df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
    df = df[df["Data"].notna()]

    if data_referencia:
        data_ref = pd.to_datetime(data_referencia).normalize()
        data_véspera = data_ref - timedelta(days=1)
        hora_corte = pd.to_timedelta("11:30:00")

        df = df[((df["Data"].dt.normalize() == data_ref) |
                 ((df["Data"].dt.normalize() == data_véspera) &
                  (df["Data"].dt.time >= (datetime.min + hora_corte).time())))]

    registros = []
    for (paciente, data), grupo in df.groupby(["Paciente", df["Data"].dt.normalize()]):
        grupo = grupo.sort_values("Data")
        ultimo = grupo.iloc[-1]
        registro = {
            "Paciente": paciente,
            "Data": data.strftime("%d/%m/%Y"),
            "Creatinina": pd.to_numeric(grupo["Creatinina"], errors="coerce").max(),
            "Ureia": pd.to_numeric(grupo["Ureia"], errors="coerce").max(),
            "Bicarbonato": pd.to_numeric(ultimo["Bicarbonato"], errors="coerce"),
            "Sódio": pd.to_numeric(grupo["Sódio"], errors="coerce").max(),
            "Potássio": pd.to_numeric(grupo["Potássio"], errors="coerce").max(),
            "Magnésio": pd.to_numeric(grupo["Magnésio"], errors="coerce").max(),
            "Cálcio": pd.to_numeric(grupo["Cálcio"], errors="coerce").max(),
            "Fósforo": pd.to_numeric(grupo["Fósforo"], errors="coerce").max(),
            "Hemoglobina": pd.to_numeric(ultimo["Hemoglobina"], errors="coerce"),
            "Plaquetas": pd.to_numeric(ultimo["Plaquetas"], errors="coerce"),
            "Proteína C Reativa": pd.to_numeric(grupo["Proteína C Reativa"], errors="coerce").max()
        }
        registros.append(registro)

    df_grouped = pd.DataFrame(registros)

    nomes_df = df_grouped["Paciente"].dropna().tolist()
    nomes_normalizados = {normalizar_nome(n): n for n in nomes_df}

    try:
        dados_censo = planilha.worksheet("CENSO AUTOMÁTICO").get("A19:D88")
        time.sleep(1)
        aba_para_paciente = {
            linha[0].zfill(2): linha[3].strip().title()
            for linha in dados_censo
            if len(linha) >= 4 and linha[0] and linha[3]
        }
    except Exception as e:
        print(f"❌ Erro ao acessar 'CENSO AUTOMÁTICO': {e}")
        return False

    total_preenchido = 0
    total_abas = 0

    todas_abas = []
    for i in range(1, 71):
        aba_nome = f"{i:02d}"
        try:
            aba = planilha.worksheet(aba_nome)
            todas_abas.append(aba)
        except gspread.exceptions.WorksheetNotFound:
            continue

    total_aba_count = len(todas_abas)

    for aba in todas_abas:
        try:
            nome_aba = aba.title
            if nome_aba in ABAS_IGNORADAS:
                continue

            nome_paciente_b1 = aba_para_paciente.get(nome_aba)
            if not nome_paciente_b1:
                continue

            nome_b1_normalizado = normalizar_nome(nome_paciente_b1)

            if nome_b1_normalizado not in nomes_normalizados:
                continue

            nome_correto = nomes_normalizados[nome_b1_normalizado]
            dados_paciente = df_grouped[df_grouped["Paciente"] == nome_correto]
            if dados_paciente.empty:
                continue

            dados_paciente = dados_paciente[COLUNAS_GOOGLE]
            valores_aba = aba.get_all_values()
            time.sleep(0.5)
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
                    time.sleep(0.5)
                    range_escreve = f"H{linha_destino}:T{linha_destino}"
                    aba.update(range_escreve, [valores_formatados[1:13]])
                    time.sleep(0.5)
                    total_preenchido += 1
                    linha_destino += 1
                except Exception:
                    continue

            total_abas += 1
            if barra_progresso:
                barra_progresso.progress(total_abas / total_aba_count)

            time.sleep(1.0)

        except Exception as e:
            print(f"Erro ao processar aba {aba.title}: {e}")
            continue

    print(f"Total de abas processadas: {total_abas}")
    print(f"Total de linhas preenchidas: {total_preenchido}")
    return True

__all__ = ["enviar_para_google_sheets"]
