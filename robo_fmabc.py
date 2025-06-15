# robo_fmabc.py - Versão corrigida para VM

import streamlit as st
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException
from datetime import datetime
import time
import os
import subprocess


def iniciar_driver(headless=True):
    options = webdriver.ChromeOptions()
    prefs = {
        "download.default_directory": output_folder,
        "download.prompt_for_download": False,
        "plugins.always_open_pdf_externally": True
    }
    options.add_experimental_option("prefs", prefs)
    
    # Configurações anti-detecção (mais importantes que headless)
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--disable-web-security")
    
    # Configurações essenciais para VM
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    
    # Headless opcional
    if headless:
        options.add_argument("--headless")
        st.info("🤖 Rodando em modo headless (sem interface)")
    else:
        options.add_argument("--start-maximized")
        st.info("🖥️ Rodando com interface gráfica")
    
    # Matar processos Chrome anteriores
    try:
        subprocess.run(["pkill", "-f", "chrome"], check=False)
        time.sleep(2)
    except:
        pass
    
    service = Service("/usr/local/bin/chromedriver")
    options.binary_location = "/usr/bin/google-chrome"
    
    driver = webdriver.Chrome(service=service, options=options)
    
    # Configurações anti-detecção no JavaScript
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver


def executar_robo_fmabc():
    st.subheader("⬇️ Download de exames")
    
    # Opção para o usuário escolher o modo
    modo_headless = st.checkbox("🤖 Modo headless (recomendado para VM)", value=True)
    
    entrada_pacientes = st.text_area("Cole aqui os nomes dos pacientes (um por linha):")

    if st.button("executar nephroghost"):
        # ✅ Caminho adaptado para VM
        base_folder = "/home/karolinewac/tablab_abc/pdfs_abc"
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        global output_folder
        output_folder = os.path.join(base_folder, timestamp)
        os.makedirs(output_folder, exist_ok=True)

        driver = iniciar_driver(headless=modo_headless)

        try:
            driver.get("http://laboratorio.fmabc.br/matrixnet/wfrmBlank.aspx")
            st.success("🌐 Navegador iniciado")

            WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.NAME, "userLogin")))
            driver.find_element(By.NAME, "userLogin").send_keys("HOAN")
            driver.find_element(By.NAME, "userPassword").send_keys("5438")
            driver.find_element(By.ID, "btnEntrar").click()

            WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.ID, "97-0B-E6-B7-F9-16-53-7C-C6-2C-E0-37-D0-67-F7-9E"))).click()
            time.sleep(1)
            driver.find_element(By.ID, "A1-2C-C6-AF-7F-6B-2B-3E-D5-00-73-F2-37-A1-D6-25").click()

            nomes = [n.strip() for n in entrada_pacientes.strip().splitlines() if n.strip()]
            progresso = st.progress(0)
            total = len(nomes)

            for idx, paciente in enumerate(nomes):
                try:
                    st.write(f"🔍 Buscando paciente: {paciente}")
                    aba_principal = driver.current_window_handle

                    WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "textoDigitado")))
                    campo = driver.find_element(By.ID, "textoDigitado")
                    campo.clear()
                    campo.send_keys(paciente)
                    driver.find_element(By.XPATH, "//button[contains(., 'Pesquisar')]").click()
                    time.sleep(3)

                    botoes = driver.find_elements(By.XPATH, "//button[contains(., 'Laudo Completo')]")
                    if not botoes:
                        st.warning(f"⚠️ Paciente não encontrado: {paciente}")
                        continue

                    for botao in botoes:
                        try:
                            original_tabs = driver.window_handles
                            driver.execute_script("arguments[0].click();", botao)
                            WebDriverWait(driver, 15).until(lambda d: len(d.window_handles) > len(original_tabs))
                            nova_aba = [t for t in driver.window_handles if t not in original_tabs][0]

                            driver.switch_to.window(nova_aba)
                            time.sleep(3)

                            # Aguardar download finalizar
                            timeout = time.time() + 20
                            while True:
                                crdownloads = [f for f in os.listdir(output_folder) if f.endswith(".crdownload")]
                                if not crdownloads or time.time() > timeout:
                                    break
                                time.sleep(1)

                            driver.close()
                            driver.switch_to.window(aba_principal)

                        except Exception as e:
                            st.warning(f"Erro no download: {str(e)}")
                            if len(driver.window_handles) > 1:
                                try:
                                    driver.close()
                                    driver.switch_to.window(aba_principal)
                                except:
                                    pass
                            continue

                    driver.switch_to.window(aba_principal)

                except WebDriverException as e:
                    st.warning(f"Erro na busca do paciente {paciente}: {str(e)}")
                    continue
                finally:
                    progresso.progress((idx + 1) / total)

            st.success(f"✅ PDFs foram baixados para: {output_folder}")

        except Exception as e:
            st.error(f"❌ Erro inesperado: {e}")

        finally:
            driver.quit()
            time.sleep(2)
            st.write("✅ nephroghost finalizado")
