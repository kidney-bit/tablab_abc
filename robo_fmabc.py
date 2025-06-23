"""
robo_fmabc.py - Robô para download de exames com Selenium
Versão para servidor com gerenciamento de sessões
"""

import streamlit as st
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
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
import tempfile
import shutil
import atexit
import signal
import uuid
import logging

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChromeManager:
    """Gerenciador do Chrome para servidor - Controla sessões e diretórios únicos"""
    
    def __init__(self, download_path=None, headless=True):
        self.driver = None
        self.temp_dir = None
        self.download_path = download_path
        self.headless = headless
        self._setup_cleanup()
    
    def _setup_cleanup(self):
        """Configura limpeza automática"""
        def cleanup():
            self._cleanup_temp_dir()
            self._kill_chrome_processes()
            logger.info("🧼 Cleanup automático executado")

        atexit.register(cleanup)

        if threading.current_thread() is threading.main_thread():
            try:
                signal.signal(signal.SIGTERM, lambda s, f: cleanup())
                signal.signal(signal.SIGINT, lambda s, f: cleanup())
            except Exception as e:
                logger.warning(f"⚠️ Falha ao registrar signal handler: {e}")
    
    def _cleanup_temp_dir(self):
        """Limpa diretório temporário"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir, ignore_errors=True)
                logger.info(f"✅ Diretório temporário limpo: {self.temp_dir}")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao limpar diretório: {e}")
    
    def _kill_chrome_processes(self):
        """Mata processos Chrome órfãos"""
        try:
            # Tentar matar processos Chrome
            subprocess.run(['pkill', '-f', 'chrome'], check=False, capture_output=True, timeout=5)
            subprocess.run(['pkill', '-f', 'chromium'], check=False, capture_output=True, timeout=5)
            subprocess.run(['pkill', '-f', 'chromedriver'], check=False, capture_output=True, timeout=5)
            
            time.sleep(1)
            
            # Força morte se necessário
            subprocess.run(['pkill', '-9', '-f', 'chrome'], check=False, capture_output=True, timeout=3)
            subprocess.run(['pkill', '-9', '-f', 'chromium'], check=False, capture_output=True, timeout=3)
            
            logger.info("🧹 Processos Chrome limpos")
        except Exception as e:
            logger.warning(f"⚠️ Erro ao limpar processos: {e}")
    
    def _create_chrome_options(self):
        """Cria opções otimizadas do Chrome"""
        # Criar diretório temporário único
        self.temp_dir = tempfile.mkdtemp(prefix='chrome_profile_')
        
        options = Options()
        
        # Configurações críticas para servidor
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--remote-debugging-port=0')  # Porta aleatória
        options.add_argument(f'--user-data-dir={self.temp_dir}')  # Diretório único
        
        # Configurações de download otimizadas
        if self.download_path:
            prefs = {
                "download.default_directory": self.download_path,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": False,
                "safebrowsing.disable_download_protection": True,
                "plugins.always_open_pdf_externally": True,
                "plugins.plugins_disabled": ["Chrome PDF Viewer"],
                "profile.default_content_settings.popups": 0,
                "profile.default_content_setting_values.automatic_downloads": 1,
                "profile.managed_default_content_settings.images": 2,
                "profile.default_content_setting_values.stylesheet": 2,
            }
            options.add_experimental_option("prefs", prefs)
        
        # Otimizações de velocidade
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-web-security")
        options.add_argument("--disable-features=VizDisplayCompositor")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--disable-images")
        options.add_argument("--disable-plugins")
        options.add_argument("--disable-java")
        options.add_argument("--disable-background-networking")
        options.add_argument("--disable-sync")
        options.add_argument("--disable-translate")
        options.add_argument("--disable-default-apps")
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")
        options.add_argument("--disable-logging")
        options.add_argument("--disable-client-side-phishing-detection")
        options.add_argument("--disable-backgrounding-occluded-windows")
        options.add_argument("--disable-renderer-backgrounding")
        options.add_argument("--disable-background-timer-throttling")
        
        # Anti-detecção
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Configurações de janela
        options.add_argument("--window-size=1280,720")
        
        if self.headless:
            options.add_argument("--headless")
        
        return options
    
    def start_driver(self):
        """Inicia o driver Chrome"""
        # Limpeza prévia
        self._kill_chrome_processes()
        self._cleanup_temp_dir()  # ← Adiciona isso aqui
        time.sleep(2)
        
        try:
            options = self._create_chrome_options()
            
            # Tentar diferentes caminhos do Chrome
            chrome_paths = [
                "/usr/bin/google-chrome",
                "/usr/bin/chromium-browser",
                "/usr/bin/chrome",
                "/opt/google/chrome/chrome"
            ]
            
            for chrome_path in chrome_paths:
                if os.path.exists(chrome_path):
                    options.binary_location = chrome_path
                    break
            
            # Configurar serviço do ChromeDriver
            service = Service("/usr/local/bin/chromedriver")
            
            # Criar driver
            self.driver = webdriver.Chrome(service=service, options=options)
            
            # Configurações de timeout
            self.driver.implicitly_wait(10)
            self.driver.set_page_load_timeout(30)
            
            # Anti-detecção
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            logger.info(f"✅ Chrome iniciado com sucesso - Temp Dir: {self.temp_dir}")
            return self.driver
            
        except Exception as e:
            self._cleanup_temp_dir()
            logger.error(f"❌ Erro ao iniciar Chrome: {e}")
            raise
    
    def __enter__(self):
        """Context manager - entrada"""
        return self.start_driver()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager - saída"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("✅ Driver Chrome fechado")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao fechar driver: {e}")
        
        time.sleep(2)
        self._cleanup_temp_dir()
        self._kill_chrome_processes()


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
                    time.sleep(1)
                    return True
                
                # Se há arquivos temporários, aguarda eles sumirem
                if arquivos_temp:
                    time.sleep(0.5)
                else:
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
            time.sleep(0.5)
        except Exception:
            pass
    else:
        st.info("✅ Sem processos órfãos detectados")


def fechar_abas_extras_rapido(driver, aba_principal):
    """Versão otimizada para fechar abas extras"""
    try:
        todas_abas = driver.window_handles
        if len(todas_abas) <= 1:
            return
            
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
            if monitor.aguardar_download(timeout=10):
                downloads_sucesso += 1
                st.success(f"✅ Download {idx_botao + 1} concluído")
            else:
                st.warning(f"⚠️ Download {idx_botao + 1} pode ter falhado (timeout)")
            
            # Pausa mínima entre downloads
            time.sleep(0.5)
            
        except Exception as e:
            st.warning(f"Erro no download {idx_botao + 1}: {str(e)}")
            continue
    
    return downloads_sucesso


def executar_downloads_automatico(nomes_pacientes, modo_headless=True):
    """
    Função para executar downloads de forma automática (chamada pelo app.py)
    
    Args:
        nomes_pacientes (list): Lista de nomes dos pacientes
        modo_headless (bool): Se deve executar em modo headless
    
    Returns:
        str: Caminho da pasta onde os PDFs foram salvos
    """
    
    # Configuração de pastas
    base_folder = os.path.join(os.path.dirname(__file__), "pdfs_abc")
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_folder = os.path.join(base_folder, timestamp)
    os.makedirs(output_folder, exist_ok=True)

    # Usar o ChromeManager otimizado
    try:
        st.info("🚀 Iniciando navegador...")
        
        with ChromeManager(download_path=output_folder, headless=modo_headless) as driver:
            st.info("🤖 Modo headless ativado" if modo_headless else "🖥️ Modo visual ativado")
            
            # Inicializar monitor de downloads
            monitor = DownloadMonitor(output_folder)

            st.info("🔗 Acessando site...")
            driver.get("http://laboratorio.fmabc.br/matrixnet/wfrmBlank.aspx")
            st.success("🌐 Site carregado")

            # Login
            st.info("🔑 Fazendo login...")
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.NAME, "userLogin")))
            driver.find_element(By.NAME, "userLogin").send_keys("HOAN")
            driver.find_element(By.NAME, "userPassword").send_keys("5438")
            driver.find_element(By.ID, "btnEntrar").click()
            
            time.sleep(3)
            st.success("✅ Login realizado")

            if not verificar_driver_ativo(driver):
                st.error("❌ Driver perdeu conexão após login")
                return None

            st.info("🎯 Navegando para exames...")
            
            # Navegação com timeouts
            try:
                element = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "97-0B-E6-B7-F9-16-53-7C-C6-2C-E0-37-D0-67-F7-9E"))
                )
                driver.execute_script("arguments[0].click();", element)
                time.sleep(1)
                
                second_element = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "A1-2C-C6-AF-7F-6B-2B-3E-D5-00-73-F2-37-A1-D6-25"))
                )
                driver.execute_script("arguments[0].click();", second_element)
                time.sleep(1)
                
                st.success("✅ Navegação concluída")
                
            except Exception as e:
                st.error(f"❌ Erro na navegação: {e}")
                return None

            # Processar pacientes
            progresso = st.progress(0)
            total = len(nomes_pacientes)
            
            st.info(f"📋 Processando {total} pacientes...")

            for idx, paciente in enumerate(nomes_pacientes):
                try:
                    if not verificar_driver_ativo(driver):
                        st.error(f"❌ Driver perdeu conexão no paciente: {paciente}")
                        break

                    st.write(f"🔍 Paciente: {paciente}")
                    aba_principal = driver.current_window_handle

                    # Busca
                    campo = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "textoDigitado")))
                    campo.clear()
                    campo.send_keys(paciente)
                    driver.find_element(By.XPATH, "//button[contains(., 'Pesquisar')]").click()
                    time.sleep(2)

                    botoes = driver.find_elements(By.XPATH, "//button[contains(., 'Laudo Completo')]")
                    if not botoes:
                        st.warning(f"⚠️ Paciente não encontrado: {paciente}")
                        continue

                    # Processar downloads do paciente
                    downloads = processar_downloads_paciente(driver, botoes, paciente, monitor, aba_principal)
                    st.write(f"📥 {downloads}/{len(botoes)} downloads realizados para {paciente}")

                    # Limpeza de abas
                    fechar_abas_extras_rapido(driver, aba_principal)

                except Exception as e:
                    st.warning(f"Erro no paciente {paciente}: {str(e)}")
                    continue

                finally:
                    progresso.progress((idx + 1) / total)

            # Resultado final
            total_pdfs = contar_pdfs_pasta(output_folder)
            st.success(f"✅ Concluído! {total_pdfs} PDFs baixados em: {output_folder}")
            
            return output_folder

    except Exception as e:
        st.error(f"❌ Erro crítico: {str(e)}")
        return None


def executar_robo_fmabc(nomes_pacientes=None):
    """
    Função principal que pode ser chamada tanto pela interface quanto programaticamente
    
    Args:
        nomes_pacientes (list, optional): Lista de nomes. Se None, usa interface do Streamlit
    """
    
    # Se recebeu lista de nomes, executa automaticamente
    if nomes_pacientes is not None:
        return executar_downloads_automatico(nomes_pacientes, modo_headless=True)
    
    # Caso contrário, mostra interface do Streamlit
    st.subheader("⬇️ Download de exames")
    
    modo_headless = st.checkbox("🤖 Modo headless (recomendado)", value=True)
    entrada_pacientes = st.text_area("Cole aqui os nomes dos pacientes (um por linha):")

    if st.button("🚀 Executar Nephroghost"):
        nomes = [n.strip() for n in entrada_pacientes.strip().splitlines() if n.strip()]
        
        if not nomes:
            st.error("❌ Por favor, insira pelo menos um nome de paciente.")
            return
        
        resultado = executar_downloads_automatico(nomes, modo_headless)
        
        if resultado:
            st.success(f"✅ Downloads concluídos com sucesso! Pasta: {resultado}")
        else:
            st.error("❌ Erro durante a execução dos downloads.")


# Para executar diretamente
if __name__ == "__main__":
    executar_robo_fmabc()
