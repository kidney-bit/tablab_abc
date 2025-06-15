# robo_fmabc.py - Atualizado para integração com app.py

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
import tempfile
import shutil

def executar_robo_fmabc():
    st.subheader("⬇️ Download de exames")
    entrada_pacientes = st.text_area("Cole aqui os nomes dos pacientes (um por linha):")

    if st.button("executar nephroghost"):
        # ⚠️ REMOVIDO caffeinate (não existe no Linux)
        # caffeinate = subprocess.Popen(["caffeinate"])

        # ✅ Caminho adaptado para VM
        base_folder = "/home/karolinewac/tablab_abc/pdfs_abc"
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_folder = os.path.join(base_folder, timestamp)
        os.makedirs(output_folder, exist_ok=True)

        def iniciar_driver():
    options = webdriver.ChromeOptions()

    profile_path = tempfile.mkdtemp(prefix="chrome_profile_")
    
    prefs = {
        "download.default_directory": output_folder,
        "download.prompt_for_download": False,
        "plugins.always_open_pdf_externally": True
    }
    options.add_experimental_option("prefs", prefs)
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument(f"--user-data-dir={profile_path}")

    service = Service("/snap/chromium/current/usr/lib/chromium-browser/chromedriver")
    driver = webdriver.Chrome(service=service, options=options)
    return driver, profile_path

            # ✅ Caminho do chromedriver adaptado para VM
            service = Service("/snap/chromium/current/usr/lib/chromium-browser/chromedriver")
            driver = webdriver.Chrome(service=service, options=options)
            return driver, profile_path

        driver, profile_path = iniciar_driver()

        try:
            driver.get("http://laboratorio.fmabc.br/matrixnet/wfrmBlank.aspx")
            st.success("🌐 Navegador iniciado")

            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.NAME, "userLogin")))
            driver.find_element(By.NAME, "userLogin").send_keys("HOAN")
            driver.find_element(By.NAME, "userPassword").send_keys("5438")
            driver.find_element(By.ID, "btnEntrar").click()

            WebDriverWait(driver, 10).until(
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

                    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "textoDigitado")))
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
                            WebDriverWait(driver, 10).until(lambda d: len(d.window_handles) > len(original_tabs))
                            nova_aba = [t for t in driver.window_handles if t not in original_tabs][0]

                            driver.switch_to.window(nova_aba)
                            time.sleep(2)

                            timeout = time.time() + 15
                            while True:
                                crdownloads = [f for f in os.listdir(output_folder) if f.endswith(".crdownload")]
                                if not crdownloads or time.time() > timeout:
                                    break
                                time.sleep(1)

                            driver.close()
                            driver.switch_to.window(aba_principal)

                        except:
                            if len(driver.window_handles) > 0:
                                try:
                                    driver.switch_to.window(aba_principal)
                                except:
                                    pass
                            continue

                    driver.switch_to.window(aba_principal)

                except WebDriverException:
                    continue
                finally:
                    progresso.progress((idx + 1) / total)

            st.success(f"✅ PDFs foram baixados para: {output_folder}")

        except Exception as e:
            st.error(f"❌ Erro inesperado: {e}")

        finally:
            driver.quit()
            shutil.rmtree(profile_path, ignore_errors=True)
            # caffeinate.terminate()  # ⚠️ REMOVIDO
            st.write("✅ nephroghost finalizado")
