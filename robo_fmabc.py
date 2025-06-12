# robo_fmabc.py

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException
from datetime import datetime
import os
import time
import tempfile
import shutil
import subprocess
import streamlit as st


def executar_robo_fmabc(lista_pacientes):
    # Impede repouso do computador
    caffeinate = subprocess.Popen(["caffeinate"])

    # Pasta de destino com timestamp
    base_folder = os.path.expanduser("~/myp/automacao_fmabc/pdfs_abc")
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_folder = os.path.join(base_folder, timestamp)
    os.makedirs(output_folder, exist_ok=True)

    def iniciar_driver():
        options = Options()
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
        profile_path = tempfile.mkdtemp()
        options.add_argument(f"--user-data-dir={profile_path}")
        service = Service("/Users/kwayla/myp/automacao_fmabc/fmabc/chromedriver")
        driver = webdriver.Chrome(service=service, options=options)
        return driver, profile_path

    driver, profile_path = iniciar_driver()
    try:
        driver.get("http://laboratorio.fmabc.br/matrixnet/wfrmBlank.aspx")
        st.write("🌐 Navegador iniciado")

        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.NAME, "userLogin")))
        driver.find_element(By.NAME, "userLogin").send_keys("HOAN")
        driver.find_element(By.NAME, "userPassword").send_keys("5438")
        driver.find_element(By.ID, "btnEntrar").click()

        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "97-0B-E6-B7-F9-16-53-7C-C6-2C-E0-37-D0-67-F7-9E"))).click()
        time.sleep(1)
        driver.find_element(By.ID, "A1-2C-C6-AF-7F-6B-2B-3E-D5-00-73-F2-37-A1-D6-25").click()

        progresso = st.progress(0)
        total = len(lista_pacientes)

        for idx, paciente in enumerate(lista_pacientes):
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
                    progresso.progress((idx + 1) / total)
                    continue

                for botao in botoes:
                    try:
                        original_tabs = driver.window_handles
                        driver.execute_script("arguments[0].click();", botao)
                        WebDriverWait(driver, 10).until(lambda d: len(d.window_handles) > len(original_tabs))
                        new_tabs = [tab for tab in driver.window_handles if tab not in original_tabs]

                        if new_tabs:
                            nova_aba = new_tabs[0]
                            driver.switch_to.window(nova_aba)
                            time.sleep(2)

                            timeout = time.time() + 15
                            while any(f.endswith(".crdownload") for f in os.listdir(output_folder)):
                                if time.time() > timeout:
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

        st.success(f"✅ PDFs foram baixados para a pasta: {output_folder}")
        return output_folder

    except Exception as e:
        st.error(f"❌ Erro inesperado: {e}")
    finally:
        driver.quit()
        shutil.rmtree(profile_path, ignore_errors=True)
        caffeinate.terminate()
        st.write("✅ Robô finalizado")
