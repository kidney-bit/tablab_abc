# robo_fmabc.py - Versão final corrigida para a VM

import streamlit as st
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException, NoSuchWindowException, TimeoutException
from datetime import datetime
import time
import os
import subprocess
import glob

class DownloadMonitor:
    def __init__(self, pasta_download):
        self.pasta_download = pasta_download
        self.arquivos_iniciais = set()
        self.reset()

    def reset(self):
        try:
            self.arquivos_iniciais = set(os.listdir(self.pasta_download))
        except:
            self.arquivos_iniciais = set()

    def aguardar_download(self, timeout=15):
        inicio = time.time()
        while time.time() - inicio < timeout:
            try:
                arquivos_atuais = set(os.listdir(self.pasta_download))
                arquivos_temp = [f for f in arquivos_atuais if f.endswith('.crdownload')]
                if arquivos_atuais - self.arquivos_iniciais and not arquivos_temp:
                    time.sleep(1) # Garante que o arquivo foi escrito
                    return True
                time.sleep(1)
            except Exception:
                time.sleep(0.5)
        return False

def verificar_driver_ativo(driver):
    try:
        driver.current_window_handle
        return True
    except (NoSuchWindowException, WebDriverException):
        return False

def limpar_processos_chrome_inteligente():
    try:
        result = subprocess.run(["pgrep", "-f", "chrome"], capture_output=True, text=True)
        if result.stdout.strip():
            subprocess.run(["pkill", "-f", "chrome"], check=False)
            subprocess.run(["pkill", "-f", "chromedriver"], check=False)
            time.sleep(1)
    except Exception:
        pass

def iniciar_driver(headless=True, output_folder=None):
    limpar_processos_chrome_inteligente()
    options = webdriver.ChromeOptions()
    prefs = {
        "download.default_directory": output_folder,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
        "plugins.always_open_pdf_externally": True,
    }
    options.add_experimental_option("prefs", prefs)
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--window-size=1280,720")
    
    # REMOVIDO --disable-javascript PORQUE QUEBRA O SITE
    # options.add_argument("--disable-javascript")
    
    if headless:
        options.add_argument("--headless")

    try:
        # Caminhos para Linux (VM)
        service = Service("/usr/bin/chromedriver")
        options.binary_location = "/usr/bin/google-chrome"
        driver = webdriver.Chrome(service=service, options=options)
        driver.implicitly_wait(10)
        return driver
    except Exception as e:
        st.error(f"❌ Erro ao iniciar Chrome (verifique os caminhos em robo_fmabc.py): {e}")
        raise

def fechar_abas_extras_rapido(driver, aba_principal):
    try:
        for aba in driver.window_handles:
            if aba != aba_principal:
                driver.switch_to.window(aba)
                driver.close()
        driver.switch_to.window(aba_principal)
    except Exception:
        pass

def executar_downloads_automatico(nomes_pacientes, modo_headless=True):
    base_folder = os.path.join(os.path.dirname(__file__), "pdfs_abc")
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_folder = os.path.join(base_folder, timestamp)
    os.makedirs(output_folder, exist_ok=True)
    
    monitor = DownloadMonitor(output_folder)
    driver = None
    try:
        driver = iniciar_driver(headless=modo_headless, output_folder=output_folder)
        driver.get("http://laboratorio.fmabc.br/matrixnet/wfrmBlank.aspx")
        
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.NAME, "userLogin")))
        driver.find_element(By.NAME, "userLogin").send_keys("HOAN")
        driver.find_element(By.NAME, "userPassword").send_keys("5438")
        driver.find_element(By.ID, "btnEntrar").click()
        time.sleep(3)

        element = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "97-0B-E6-B7-F9-16-53-7C-C6-2C-E0-37-D0-67-F7-9E")))
        driver.execute_script("arguments[0].click();", element)
        time.sleep(1)
        
        second_element = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "A1-2C-C6-AF-7F-6B-2B-3E-D5-00-73-F2-37-A1-D6-25")))
        driver.execute_script("arguments[0].click();", second_element)
        time.sleep(1)

        progresso = st.progress(0)
        total = len(nomes_pacientes)
        
        for idx, paciente in enumerate(nomes_pacientes):
            if not verificar_driver_ativo(driver):
                st.error(f"❌ Driver perdeu conexão no paciente: {paciente}")
                break
            
            st.write(f"🔍 Buscando paciente: {paciente}")
            aba_principal = driver.current_window_handle
            
            campo = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "textoDigitado")))
            campo.clear()
            campo.send_keys(paciente)
            driver.find_element(By.XPATH, "//button[contains(., 'Pesquisar')]").click()
            time.sleep(2)

            botoes = driver.find_elements(By.XPATH, "//button[contains(., 'Laudo Completo')]")
            if not botoes:
                st.warning(f"⚠️ Paciente não encontrado ou sem laudos: {paciente}")
                continue

            for botao in botoes:
                monitor.reset()
                driver.execute_script("arguments[0].click();", botao)
                monitor.aguardar_download()
                fechar_abas_extras_rapido(driver, aba_principal)

            progresso.progress((idx + 1) / total)
        
        st.success(f"✅ Downloads concluídos! PDFs salvos em: {output_folder}")
        return output_folder # ✅ Retorna o caminho para o app.py

    except Exception as e:
        st.error(f"❌ Erro crítico no robô: {e}")
        return None
    finally:
        if driver:
            driver.quit()
        limpar_processos_chrome_inteligente()

# ✅ FUNÇÃO PRINCIPAL CORRIGIDA
def executar_robo_fmabc(nomes_pacientes=None):
    """
    Função que orquestra o robô.
    - Se receber 'nomes_pacientes', executa o modo automático.
    - Se não, exibe a interface do Streamlit.
    """
    # MODO AUTOMÁTICO (chamado pelo "Rodar tudo")
    if nomes_pacientes is not None:
        return executar_downloads_automatico(nomes_pacientes, modo_headless=True)
    
    # MODO INDIVIDUAL (interface do Streamlit)
    st.subheader("⬇️ Download de exames")
    modo_headless = st.checkbox("🤖 Executar em modo silencioso (headless)", value=True)
    entrada_pacientes = st.text_area("Cole aqui os nomes dos pacientes (um por linha):")

    if st.button("🚀 Iniciar Downloads"):
        nomes = [n.strip() for n in entrada_pacientes.strip().splitlines() if n.strip()]
        if not nomes:
            st.error("❌ Por favor, insira pelo menos um nome de paciente.")
        else:
            executar_downloads_automatico(nomes, modo_headless)

if __name__ == "__main__":
    executar_robo_fmabc()
