# robo_fmabc.py - Versão corrigida para problemas de VM/window closed

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


def verificar_driver_ativo(driver):
    """Verifica se o driver ainda está ativo e acessível"""
    try:
        driver.current_window_handle
        return True
    except (NoSuchWindowException, WebDriverException):
        return False


def aguardar_download_completo(pasta_download, timeout=30):
    """Aguarda todos os downloads completarem"""
    inicio = time.time()
    while time.time() - inicio < timeout:
        # Verifica arquivos .crdownload (Chrome) e .tmp (temporários)
        arquivos_temporarios = (
            glob.glob(os.path.join(pasta_download, "*.crdownload")) +
            glob.glob(os.path.join(pasta_download, "*.tmp"))
        )
        if not arquivos_temporarios:
            time.sleep(2)  # Aguarda um pouco mais para garantir
            return True
        time.sleep(1)
    return False


def limpar_processos_chrome():
    """Remove processos Chrome órfãos"""
    try:
        subprocess.run(["pkill", "-f", "chrome"], check=False, capture_output=True)
        subprocess.run(["pkill", "-f", "chromedriver"], check=False, capture_output=True)
        time.sleep(3)
    except Exception:
        pass


def iniciar_driver(headless=True):
    # Limpar processos anteriores
    limpar_processos_chrome()
    
    options = webdriver.ChromeOptions()
    prefs = {
        "download.default_directory": output_folder,
        "download.prompt_for_download": False,
        "plugins.always_open_pdf_externally": True,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    options.add_experimental_option("prefs", prefs)
    
    # Configurações essenciais para VM
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-web-security")
    options.add_argument("--allow-running-insecure-content")
    options.add_argument("--disable-features=VizDisplayCompositor")
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-backgrounding-occluded-windows")
    
    # Configurações anti-detecção
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Configurações de janela
    options.add_argument("--window-size=1920,1080")
    
    if headless:
        options.add_argument("--headless")
        st.info("🤖 Rodando em modo headless (sem interface)")
    else:
        st.info("🖥️ Rodando com interface gráfica")
    
    try:
        service = Service("/usr/local/bin/chromedriver")
        options.binary_location = "/usr/bin/google-chrome"
        
        driver = webdriver.Chrome(service=service, options=options)
        
        # Timeouts mais generosos para VM
        driver.implicitly_wait(20)
        driver.set_page_load_timeout(60)
        
        # Configurações anti-detecção no JavaScript
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return driver
        
    except Exception as e:
        st.error(f"❌ Erro ao iniciar Chrome: {e}")
        raise


def fechar_abas_extras(driver, aba_principal):
    """Fecha todas as abas exceto a principal"""
    try:
        todas_abas = driver.window_handles
        for aba in todas_abas:
            if aba != aba_principal:
                try:
                    driver.switch_to.window(aba)
                    driver.close()
                except:
                    pass
        driver.switch_to.window(aba_principal)
    except Exception as e:
        st.warning(f"Aviso: Erro ao fechar abas extras: {e}")


def executar_robo_fmabc():
    st.subheader("⬇️ Download de exames")
    
    modo_headless = st.checkbox("🤖 Modo headless (recomendado para VM)", value=True)
    entrada_pacientes = st.text_area("Cole aqui os nomes dos pacientes (um por linha):")

    if st.button("executar nephroghost"):
        # Configuração de pastas
        base_folder = "/home/karolinewac/tablab_abc/pdfs_abc"
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        global output_folder
        output_folder = os.path.join(base_folder, timestamp)
        os.makedirs(output_folder, exist_ok=True)

        driver = None
        try:
            driver = iniciar_driver(headless=modo_headless)

            st.info("🔗 Acessando site do laboratório...")
            driver.get("http://laboratorio.fmabc.br/matrixnet/wfrmBlank.aspx")
            st.success("🌐 Navegador iniciado")

            # Login
            st.info("🔑 Fazendo login...")
            WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.NAME, "userLogin")))
            driver.find_element(By.NAME, "userLogin").send_keys("HOAN")
            driver.find_element(By.NAME, "userPassword").send_keys("5438")
            driver.find_element(By.ID, "btnEntrar").click()
            
            # Aguardar login processar
            time.sleep(8)
            st.success("✅ Login realizado")

            # Verificar se driver ainda está ativo após login
            if not verificar_driver_ativo(driver):
                st.error("❌ Driver perdeu conexão após login")
                return

            st.info("🎯 Navegando para seção de exames...")
            
            # Primeiro elemento - com retry
            sucesso_primeiro = False
            for tentativa in range(3):
                try:
                    if not verificar_driver_ativo(driver):
                        st.error("❌ Driver inativo durante navegação")
                        return
                        
                    element = WebDriverWait(driver, 20).until(
                        EC.element_to_be_clickable((By.ID, "97-0B-E6-B7-F9-16-53-7C-C6-2C-E0-37-D0-67-F7-9E"))
                    )
                    driver.execute_script("arguments[0].click();", element)
                    time.sleep(3)
                    sucesso_primeiro = True
                    st.success("✅ Primeiro elemento clicado")
                    break
                    
                except Exception as e:
                    st.warning(f"⚠️ Tentativa {tentativa + 1} falhou: {e}")
                    if tentativa < 2:
                        time.sleep(5)
                    
            if not sucesso_primeiro:
                st.error("❌ Falha ao clicar no primeiro elemento após 3 tentativas")
                return

            # Segundo elemento - com retry
            sucesso_segundo = False
            for tentativa in range(3):
                try:
                    if not verificar_driver_ativo(driver):
                        st.error("❌ Driver inativo durante segundo clique")
                        return
                        
                    second_element = driver.find_element(By.ID, "A1-2C-C6-AF-7F-6B-2B-3E-D5-00-73-F2-37-A1-D6-25")
                    driver.execute_script("arguments[0].click();", second_element)
                    time.sleep(3)
                    sucesso_segundo = True
                    st.success("✅ Seção de exames acessada")
                    break
                    
                except Exception as e:
                    st.warning(f"⚠️ Segundo elemento - tentativa {tentativa + 1} falhou: {e}")
                    if tentativa < 2:
                        time.sleep(5)

            if not sucesso_segundo:
                st.error("❌ Falha ao acessar seção de exames")
                return

            # Processar pacientes
            nomes = [n.strip() for n in entrada_pacientes.strip().splitlines() if n.strip()]
            progresso = st.progress(0)
            total = len(nomes)

            for idx, paciente in enumerate(nomes):
                try:
                    # Verificar driver antes de cada paciente
                    if not verificar_driver_ativo(driver):
                        st.error(f"❌ Driver perdeu conexão durante processamento do paciente: {paciente}")
                        break

                    st.write(f"🔍 Buscando paciente: {paciente}")
                    aba_principal = driver.current_window_handle

                    # Buscar paciente
                    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "textoDigitado")))
                    campo = driver.find_element(By.ID, "textoDigitado")
                    campo.clear()
                    campo.send_keys(paciente)
                    driver.find_element(By.XPATH, "//button[contains(., 'Pesquisar')]").click()
                    time.sleep(5)

                    botoes = driver.find_elements(By.XPATH, "//button[contains(., 'Laudo Completo')]")
                    if not botoes:
                        st.warning(f"⚠️ Paciente não encontrado: {paciente}")
                        continue

                    # Processar cada botão de laudo
                    for idx_botao, botao in enumerate(botoes):
                        try:
                            # Verificar driver antes de cada download
                            if not verificar_driver_ativo(driver):
                                st.error("❌ Driver perdeu conexão durante download")
                                break

                            abas_antes = driver.window_handles[:]
                            
                            # Clicar no botão
                            driver.execute_script("arguments[0].click();", botao)
                            
                            # Aguardar nova aba aparecer
                            try:
                                WebDriverWait(driver, 15).until(lambda d: len(d.window_handles) > len(abas_antes))
                                nova_aba = [t for t in driver.window_handles if t not in abas_antes][0]
                                
                                # Mudar para nova aba
                                driver.switch_to.window(nova_aba)
                                time.sleep(5)
                                
                                # Aguardar download completar
                                if not aguardar_download_completo(output_folder, timeout=30):
                                    st.warning(f"⚠️ Timeout no download do paciente {paciente}")
                                
                                # Fechar aba e voltar para principal
                                driver.close()
                                driver.switch_to.window(aba_principal)
                                
                            except TimeoutException:
                                st.warning(f"⚠️ Nova aba não abriu para {paciente} - botão {idx_botao + 1}")
                                # Garantir que estamos na aba principal
                                driver.switch_to.window(aba_principal)

                        except Exception as e:
                            st.warning(f"Erro no download {idx_botao + 1} do paciente {paciente}: {str(e)}")
                            try:
                                # Tentar voltar para aba principal
                                fechar_abas_extras(driver, aba_principal)
                            except:
                                pass

                    # Limpar abas extras após cada paciente
                    fechar_abas_extras(driver, aba_principal)

                except Exception as e:
                    st.warning(f"Erro geral no paciente {paciente}: {str(e)}")
                    try:
                        # Tentar manter driver funcional
                        if verificar_driver_ativo(driver):
                            aba_principal = driver.window_handles[0]
                            fechar_abas_extras(driver, aba_principal)
                    except:
                        pass

                finally:
                    progresso.progress((idx + 1) / total)

            st.success(f"✅ PDFs foram baixados para: {output_folder}")

        except Exception as e:
            st.error(f"❌ Erro crítico: {str(e)}")
            # Debug adicional
            st.write(f"**Tipo do erro:** {type(e).__name__}")
            try:
                if driver and verificar_driver_ativo(driver):
                    screenshot_path = os.path.join(output_folder, "erro_debug.png")
                    driver.save_screenshot(screenshot_path)
                    st.write(f"📸 Screenshot salvo em: {screenshot_path}")
            except:
                st.write("❌ Não foi possível capturar screenshot")

        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
            
            # Limpeza final
            time.sleep(3)
            limpar_processos_chrome()
            st.write("✅ nephroghost finalizado")
