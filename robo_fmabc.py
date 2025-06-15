# robo_fmabc_otimizado.py - Versão otimizada para downloads mais rápidos

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
import threading
from concurrent.futures import ThreadPoolExecutor


class DownloadMonitor:
    """Monitor de downloads otimizado"""
    def __init__(self, pasta_download):
        self.pasta_download = pasta_download
        self.arquivos_iniciais = set()
        self.reset()
    
    def reset(self):
        """Reseta o estado do monitor"""
        try:
            self.arquivos_iniciais = set(os.listdir(self.pasta_download))
        except:
            self.arquivos_iniciais = set()
    
    def aguardar_download(self, timeout=15):
        """Aguarda download com verificação otimizada"""
        inicio = time.time()
        
        while time.time() - inicio < timeout:
            try:
                arquivos_atuais = set(os.listdir(self.pasta_download))
                
                # Verifica arquivos temporários
                arquivos_temp = [f for f in arquivos_atuais if f.endswith(('.crdownload', '.tmp', '.part'))]
                
                # Se há novos arquivos e não há temporários, download completo
                novos_arquivos = arquivos_atuais - self.arquivos_iniciais
                if novos_arquivos and not arquivos_temp:
                    # Aguarda apenas 1 segundo para garantir
                    time.sleep(1)
                    return True
                
                # Se há arquivos temporários, aguarda eles sumirem
                if arquivos_temp:
                    # Aguarda menos tempo quando há progresso visível
                    time.sleep(0.5)
                else:
                    # Aguarda mais quando não há atividade
                    time.sleep(1)
                    
            except Exception:
                time.sleep(0.5)
        
        # Verifica uma última vez se houve sucesso
        try:
            arquivos_finais = set(os.listdir(self.pasta_download))
            return len(arquivos_finais) > len(self.arquivos_iniciais)
        except:
            return False


def verificar_driver_ativo(driver):
    """Verifica se o driver ainda está ativo"""
    try:
        driver.current_window_handle
        return True
    except (NoSuchWindowException, WebDriverException):
        return False


def contar_pdfs_pasta(pasta):
    """Conta arquivos PDF na pasta"""
    try:
        return len([f for f in os.listdir(pasta) if f.lower().endswith('.pdf')])
    except:
        return 0


def verificar_processos_orfaos():
    """Verifica se há processos Chrome órfãos"""
    try:
        result = subprocess.run(["pgrep", "-f", "chrome"], capture_output=True, text=True)
        return len(result.stdout.strip().split('\n')) > 1 if result.stdout.strip() else False
    except:
        return False


def limpar_processos_chrome_inteligente():
    """Remove processos Chrome órfãos apenas se necessário"""
    if verificar_processos_orfaos():
        st.info("🧹 Detectados processos órfãos, limpando...")
        try:
            subprocess.run(["pkill", "-f", "chrome"], check=False, capture_output=True, timeout=3)
            subprocess.run(["pkill", "-f", "chromedriver"], check=False, capture_output=True, timeout=3)
            time.sleep(0.5)  # Mínimo necessário
        except Exception:
            pass
    else:
        st.info("✅ Sem processos órfãos detectados")


def iniciar_driver(headless=True):
    # Limpar processos apenas se realmente necessário
    limpar_processos_chrome_inteligente()
    
    options = webdriver.ChromeOptions()
    
    # CONFIGURAÇÕES OTIMIZADAS PARA DOWNLOAD RÁPIDO
    prefs = {
        "download.default_directory": output_folder,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": False,  # DESABILITA VERIFICAÇÃO DE SEGURANÇA
        "safebrowsing.disable_download_protection": True,
        "plugins.always_open_pdf_externally": True,
        "plugins.plugins_disabled": ["Chrome PDF Viewer"],
        "profile.default_content_settings.popups": 0,
        "profile.default_content_setting_values.automatic_downloads": 1,
        "profile.managed_default_content_settings.images": 2,  # BLOQUEIA IMAGENS
        "profile.default_content_setting_values.stylesheet": 2,  # BLOQUEIA CSS
    }
    options.add_experimental_option("prefs", prefs)
    
    # Configurações otimizadas para velocidade
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-web-security")
    options.add_argument("--disable-features=VizDisplayCompositor")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-images")  # BLOQUEIA IMAGENS
    options.add_argument("--disable-javascript")  # PODE QUEBRAR - TESTE PRIMEIRO
    options.add_argument("--disable-plugins")
    options.add_argument("--disable-java")
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-sync")
    options.add_argument("--disable-translate")
    options.add_argument("--disable-default-apps")
    options.add_argument("--no-first-run")
    options.add_argument("--fast-start")
    options.add_argument("--disable-logging")
    
    # Anti-detecção otimizada
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Janela menor para economizar recursos
    options.add_argument("--window-size=1280,720")
    
    if headless:
        options.add_argument("--headless")
        st.info("🤖 Modo headless otimizado ativado")
    
    try:
        service = Service("/usr/local/bin/chromedriver")
        options.binary_location = "/usr/bin/google-chrome"
        
        driver = webdriver.Chrome(service=service, options=options)
        
        # Timeouts otimizados
        driver.implicitly_wait(10)  # Reduzido de 20 para 10
        driver.set_page_load_timeout(30)  # Reduzido de 60 para 30
        
        # Configuração anti-detecção
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return driver
        
    except Exception as e:
        st.error(f"❌ Erro ao iniciar Chrome: {e}")
        raise


def fechar_abas_extras_rapido(driver, aba_principal):
    """Versão otimizada para fechar abas extras"""
    try:
        todas_abas = driver.window_handles
        if len(todas_abas) <= 1:
            return  # Só uma aba, não precisa fazer nada
            
        for aba in todas_abas:
            if aba != aba_principal:
                try:
                    driver.switch_to.window(aba)
                    driver.close()
                except:
                    pass
        driver.switch_to.window(aba_principal)
    except Exception:
        pass


def processar_downloads_paciente(driver, botoes, paciente, monitor, aba_principal):
    """Processa downloads de um paciente de forma otimizada"""
    downloads_sucesso = 0
    
    for idx_botao, botao in enumerate(botoes):
        try:
            if not verificar_driver_ativo(driver):
                st.error("❌ Driver perdeu conexão durante download")
                break

            st.info(f"📥 Download {idx_botao + 1}/{len(botoes)} - {paciente}")
            
            # Reset do monitor para este download
            monitor.reset()
            
            # Click otimizado
            driver.execute_script("arguments[0].click();", botao)
            
            # Aguarda download com timeout reduzido
            if monitor.aguardar_download(timeout=10):  # Reduzido de 20 para 10 segundos
                downloads_sucesso += 1
                st.success(f"✅ Download {idx_botao + 1} concluído")
            else:
                st.warning(f"⚠️ Download {idx_botao + 1} pode ter falhado (timeout)")
            
            # Pausa mínima entre downloads
            time.sleep(0.5)  # Reduzido de 3 para 0.5 segundos
            
        except Exception as e:
            st.warning(f"Erro no download {idx_botao + 1}: {str(e)}")
            continue
    
    return downloads_sucesso


def executar_robo_fmabc():
    st.subheader("⬇️ Download de exames - Versão Otimizada")
    
    modo_headless = st.checkbox("🤖 Modo headless (recomendado)", value=True)
    entrada_pacientes = st.text_area("Cole aqui os nomes dos pacientes (um por linha):")

    if st.button("🚀 Executar Nephroghost Otimizado"):
        # Configuração de pastas
        base_folder = "/home/karolinewac/tablab_abc/pdfs_abc"
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        global output_folder
        output_folder = os.path.join(base_folder, timestamp)
        os.makedirs(output_folder, exist_ok=True)

        # Inicializar monitor de downloads
        monitor = DownloadMonitor(output_folder)

        driver = None
        try:
            st.info("🚀 Iniciando navegador otimizado...")
            driver = iniciar_driver(headless=modo_headless)

            st.info("🔗 Acessando site...")
            driver.get("http://laboratorio.fmabc.br/matrixnet/wfrmBlank.aspx")
            st.success("🌐 Site carregado")

            # Login otimizado
            st.info("🔑 Fazendo login...")
            WebDriverWait(driver, 15).wait(EC.presence_of_element_located((By.NAME, "userLogin")))
            driver.find_element(By.NAME, "userLogin").send_keys("HOAN")
            driver.find_element(By.NAME, "userPassword").send_keys("5438")
            driver.find_element(By.ID, "btnEntrar").click()
            
            time.sleep(3)  # Reduzido de 8 para 3 segundos
            st.success("✅ Login realizado")

            if not verificar_driver_ativo(driver):
                st.error("❌ Driver perdeu conexão após login")
                return

            st.info("🎯 Navegando para exames...")
            
            # Navegação otimizada com timeouts reduzidos
            try:
                element = WebDriverWait(driver, 10).until(  # Reduzido de 20 para 10
                    EC.element_to_be_clickable((By.ID, "97-0B-E6-B7-F9-16-53-7C-C6-2C-E0-37-D0-67-F7-9E"))
                )
                driver.execute_script("arguments[0].click();", element)
                time.sleep(1)  # Reduzido de 3 para 1
                
                second_element = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "A1-2C-C6-AF-7F-6B-2B-3E-D5-00-73-F2-37-A1-D6-25"))
                )
                driver.execute_script("arguments[0].click();", second_element)
                time.sleep(1)  # Reduzido de 3 para 1
                
                st.success("✅ Navegação concluída")
                
            except Exception as e:
                st.error(f"❌ Erro na navegação: {e}")
                return

            # Processar pacientes
            nomes = [n.strip() for n in entrada_pacientes.strip().splitlines() if n.strip()]
            progresso = st.progress(0)
            total = len(nomes)
            
            st.info(f"📋 Processando {total} pacientes...")

            for idx, paciente in enumerate(nomes):
                try:
                    if not verificar_driver_ativo(driver):
                        st.error(f"❌ Driver perdeu conexão no paciente: {paciente}")
                        break

                    st.write(f"🔍 Paciente: {paciente}")
                    aba_principal = driver.current_window_handle

                    # Busca otimizada
                    campo = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "textoDigitado")))
                    campo.clear()
                    campo.send_keys(paciente)
                    driver.find_element(By.XPATH, "//button[contains(., 'Pesquisar')]").click()
                    time.sleep(2)  # Reduzido de 5 para 2

                    botoes = driver.find_elements(By.XPATH, "//button[contains(., 'Laudo Completo')]")
                    if not botoes:
                        st.warning(f"⚠️ Paciente não encontrado: {paciente}")
                        continue

                    # Processar downloads do paciente
                    downloads = processar_downloads_paciente(driver, botoes, paciente, monitor, aba_principal)
                    st.write(f"📥 {downloads}/{len(botoes)} downloads realizados para {paciente}")

                    # Limpeza rápida de abas
                    fechar_abas_extras_rapido(driver, aba_principal)

                except Exception as e:
                    st.warning(f"Erro no paciente {paciente}: {str(e)}")
                    continue

                finally:
                    progresso.progress((idx + 1) / total)

            # Resultado final
            total_pdfs = contar_pdfs_pasta(output_folder)
            st.success(f"✅ Concluído! {total_pdfs} PDFs baixados em: {output_folder}")

        except Exception as e:
            st.error(f"❌ Erro crítico: {str(e)}")

        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
            
            # Limpeza final apenas se necessário
            if verificar_processos_orfaos():
                limpar_processos_chrome_inteligente()
            st.write("✅ Nephroghost otimizado finalizado")


# Para executar diretamente
if __name__ == "__main__":
    executar_robo_fmabc()
