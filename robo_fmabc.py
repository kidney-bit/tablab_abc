"""
robo_fmabc.py - Robô para download de exames com Selenium
Versão corrigida para Google Cloud Platform
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
import psutil
import random

# Limpar diretórios temporários antigos na inicialização
def cleanup_old_temp_dirs():
    temp_base = tempfile.gettempdir()
    for item in os.listdir(temp_base):
        if item.startswith('chrome_session_'):
            path = os.path.join(temp_base, item)
            try:
                shutil.rmtree(path, ignore_errors=True)
            except:
                pass

cleanup_old_temp_dirs()

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChromeManager:
    """Gerenciador do Chrome otimizado para Google Cloud Platform"""
    
    def __init__(self, download_path=None, headless=True):
        self.driver = None
        self.temp_dir = None
        self.download_path = download_path
        self.headless = headless
        self.session_id = f"{uuid.uuid4().hex}_{int(time.time())}"
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
    
    def _force_kill_chrome_processes(self):
        """Mata todos os processos Chrome de forma agressiva"""
        try:
            # Listar processos Chrome
            chrome_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['name'] and any(x in proc.info['name'].lower() for x in ['chrome', 'chromium', 'chromedriver']):
                        chrome_processes.append(proc.info['pid'])
                    elif proc.info['cmdline'] and any('chrome' in str(cmd).lower() for cmd in proc.info['cmdline']):
                        chrome_processes.append(proc.info['pid'])
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Matar processos encontrados
            for pid in chrome_processes:
                try:
                    proc = psutil.Process(pid)
                    proc.terminate()
                    proc.wait(timeout=3)
                except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                    try:
                        proc.kill()
                    except psutil.NoSuchProcess:
                        pass
                except Exception:
                    pass
            
            # Backup com comandos do sistema
            subprocess.run(['pkill', '-9', '-f', 'chrome'], check=False, capture_output=True, timeout=3)
            subprocess.run(['pkill', '-9', '-f', 'chromium'], check=False, capture_output=True, timeout=3)
            subprocess.run(['pkill', '-9', '-f', 'chromedriver'], check=False, capture_output=True, timeout=3)
            
            logger.info("🧹 Todos os processos Chrome foram terminados")
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao matar processos Chrome: {e}")
    
    def _cleanup_temp_dir(self):
        """Limpa diretório temporário de forma robusta"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                # Tenta remover normalmente
                shutil.rmtree(self.temp_dir, ignore_errors=True)
                
                # Se ainda existe, força remoção
                if os.path.exists(self.temp_dir):
                    subprocess.run(['rm', '-rf', self.temp_dir], check=False, timeout=5)
                
                logger.info(f"✅ Diretório temporário limpo: {self.temp_dir}")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao limpar diretório: {e}")
                # Tenta com sudo em último caso
                try:
                    subprocess.run(['sudo', 'rm', '-rf', self.temp_dir], check=False, timeout=5)
                except:
                    pass
    
    def _kill_chrome_processes(self):
        """Mata processos Chrome órfãos de forma inteligente"""
        self._force_kill_chrome_processes()
        time.sleep(2)  # Aguarda processos terminarem
    
    def _create_unique_temp_dir(self):
        """Cria diretório temporário completamente único"""
        # Múltiplas camadas de unicidade
        timestamp = str(int(time.time() * 1000000))  # microsegundos
        random_suffix = str(random.randint(10000, 99999))
        process_id = str(os.getpid())
        
        # Base temporária do sistema
        system_temp = tempfile.gettempdir()
        
        # Subdiretório único
        unique_name = f"chrome_session_{self.session_id}_{timestamp}_{process_id}_{random_suffix}"
        self.temp_dir = os.path.join(system_temp, unique_name)
        
        # Remove se existir (não deveria)
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        
        # Cria diretório
        os.makedirs(self.temp_dir, mode=0o700, exist_ok=False)
        
        logger.info(f"📁 Diretório temporário criado: {self.temp_dir}")
        return self.temp_dir
    
    def _create_chrome_options(self):
        """Cria opções otimizadas do Chrome para GCP"""
        # Criar diretório temporário único
        temp_dir = self._create_unique_temp_dir()
        
        options = Options()

        # Configurações críticas para GCP e servidores
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-software-rasterizer')
        options.add_argument('--disable-background-timer-throttling')
        options.add_argument('--disable-backgrounding-occluded-windows')
        options.add_argument('--disable-renderer-backgrounding')
        options.add_argument('--disable-features=TranslateUI')
        options.add_argument('--disable-features=BlinkGenPropertyTrees')
        options.add_argument('--disable-ipc-flooding-protection')
        
        # Diretório de dados único - CRÍTICO
        options.add_argument(f'--user-data-dir={temp_dir}')
        options.add_argument(f'--data-path={temp_dir}')
        options.add_argument(f'--disk-cache-dir={temp_dir}/cache')
        
        # Porta de debug aleatória
        debug_port = random.randint(9000, 9999)
        options.add_argument(f'--remote-debugging-port={debug_port}')
        
        # Configurações de rede e segurança
        options.add_argument('--disable-web-security')
        options.add_argument('--disable-features=VizDisplayCompositor')
        options.add_argument('--disable-popup-blocking')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-plugins')
        options.add_argument('--disable-images')
        options.add_argument('--disable-java')
        options.add_argument('--disable-background-networking')
        options.add_argument('--disable-sync')
        options.add_argument('--disable-translate')
        options.add_argument('--disable-default-apps')
        options.add_argument('--no-first-run')
        options.add_argument('--no-default-browser-check')
        options.add_argument('--disable-logging')
        options.add_argument('--disable-client-side-phishing-detection')
        options.add_argument('--disable-component-update')
        options.add_argument('--disable-domain-reliability')
        options.add_argument('--disable-features=AutomationControlled')
        
        # Configurações de memória para GCP
        options.add_argument('--memory-pressure-off')
        options.add_argument('--max_old_space_size=4096')
        options.add_argument('--aggressive-cache-discard')
        
        # Configurações de download
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
        
        # Anti-detecção
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Configurações de janela
        options.add_argument("--window-size=1280,720")
        options.add_argument("--start-maximized")
        
        if self.headless:
            options.add_argument("--headless=new")  # Novo modo headless
        
        return options
    
    def _find_chrome_binary(self):
        """Encontra o binário do Chrome no sistema"""
        chrome_paths = [
            "/usr/bin/google-chrome-stable",
            "/usr/bin/google-chrome",
            "/usr/bin/chromium-browser",
            "/usr/bin/chromium",
            "/usr/bin/chrome",
            "/opt/google/chrome/chrome",
            "/opt/google/chrome/google-chrome",
            "/snap/bin/chromium"
        ]
        
        for chrome_path in chrome_paths:
            if os.path.exists(chrome_path) and os.access(chrome_path, os.X_OK):
                logger.info(f"✅ Chrome encontrado em: {chrome_path}")
                return chrome_path
        
        raise Exception("❌ Chrome não encontrado no sistema")
    
    def _find_chromedriver(self):
        """Encontra o ChromeDriver no sistema"""
        driver_paths = [
            "/usr/local/bin/chromedriver",
            "/usr/bin/chromedriver",
            "/opt/chromedriver/chromedriver",
            "/home/chromedriver",
            "./chromedriver"
        ]
        
        for driver_path in driver_paths:
            if os.path.exists(driver_path) and os.access(driver_path, os.X_OK):
                logger.info(f"✅ ChromeDriver encontrado em: {driver_path}")
                return driver_path
        
        raise Exception("❌ ChromeDriver não encontrado no sistema")
    
    def start_driver(self):
        """Inicia o driver Chrome com retry e recuperação"""
        max_attempts = 3
        
        for attempt in range(max_attempts):
            try:
                logger.info(f"🚀 Tentativa {attempt + 1}/{max_attempts} de iniciar Chrome")
                
                # Limpeza agressiva antes de cada tentativa
                self._kill_chrome_processes()
                time.sleep(3)
                
                # Criar opções
                options = self._create_chrome_options()
                
                # Encontrar binários
                chrome_binary = self._find_chrome_binary()
                options.binary_location = chrome_binary
                
                chromedriver_path = self._find_chromedriver()
                
                # Configurar serviço
                service = Service(chromedriver_path)
                service.start()
                
                # Criar driver
                self.driver = webdriver.Chrome(service=service, options=options)
                
                # Configurações de timeout
                self.driver.implicitly_wait(10)
                self.driver.set_page_load_timeout(60)
                self.driver.set_script_timeout(30)
                
                # Anti-detecção
                self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                
                # Teste básico
                self.driver.get("data:,")  # Página em branco para teste
                
                logger.info(f"✅ Chrome iniciado com sucesso na tentativa {attempt + 1}")
                logger.info(f"📁 Usando diretório: {self.temp_dir}")
                return self.driver
                
            except Exception as e:
                logger.error(f"❌ Tentativa {attempt + 1} falhou: {e}")
                
                # Limpeza após falha
                if self.driver:
                    try:
                        self.driver.quit()
                    except:
                        pass
                    self.driver = None
                
                self._cleanup_temp_dir()
                self._kill_chrome_processes()
                
                if attempt < max_attempts - 1:
                    wait_time = (attempt + 1) * 5
                    logger.info(f"⏳ Aguardando {wait_time}s antes da próxima tentativa...")
                    time.sleep(wait_time)
                else:
                    raise Exception(f"❌ Falha ao iniciar Chrome após {max_attempts} tentativas: {e}")
    
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
        
        time.sleep(3)
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
            if os.path.exists(self.pasta_download):
                self.arquivos_iniciais = set(os.listdir(self.pasta_download))
            else:
                os.makedirs(self.pasta_download, exist_ok=True)
                self.arquivos_iniciais = set()
        except Exception as e:
            logger.warning(f"⚠️ Erro ao resetar monitor: {e}")
            self.arquivos_iniciais = set()
    
    def aguardar_download(self, timeout=20):
        """Aguarda download com verificação otimizada"""
        inicio = time.time()
        
        while time.time() - inicio < timeout:
            try:
                if not os.path.exists(self.pasta_download):
                    time.sleep(0.5)
                    continue
                    
                arquivos_atuais = set(os.listdir(self.pasta_download))
                
                # Verifica arquivos temporários
                arquivos_temp = [f for f in arquivos_atuais if f.endswith(('.crdownload', '.tmp', '.part'))]
                
                # Se há novos arquivos e não há temporários, download completo
                novos_arquivos = arquivos_atuais - self.arquivos_iniciais
                if novos_arquivos and not arquivos_temp:
                    time.sleep(1)  # Aguarda estabilização
                    return True
                
                # Se há arquivos temporários, aguarda eles sumirem
                if arquivos_temp:
                    time.sleep(0.5)
                else:
                    time.sleep(1)
                    
            except Exception as e:
                logger.warning(f"⚠️ Erro no monitor: {e}")
                time.sleep(0.5)
        
        # Verifica uma última vez se houve sucesso
        try:
            if os.path.exists(self.pasta_download):
                arquivos_finais = set(os.listdir(self.pasta_download))
                return len(arquivos_finais) > len(self.arquivos_iniciais)
        except:
            pass
        
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
        if not os.path.exists(pasta):
            return 0
        return len([f for f in os.listdir(pasta) if f.lower().endswith('.pdf')])
    except Exception as e:
        logger.warning(f"⚠️ Erro ao contar PDFs: {e}")
        return 0


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
    except Exception as e:
        logger.warning(f"⚠️ Erro ao fechar abas: {e}")


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
            
            # Click otimizado com retry
            success = False
            for attempt in range(3):
                try:
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", botao)
                    time.sleep(0.5)
                    driver.execute_script("arguments[0].click();", botao)
                    success = True
                    break
                except Exception as e:
                    if attempt == 2:
                        raise e
                    time.sleep(1)
            
            if not success:
                st.warning(f"⚠️ Falha ao clicar no download {idx_botao + 1}")
                continue
            
            # Aguarda download
            if monitor.aguardar_download(timeout=15):
                downloads_sucesso += 1
                st.success(f"✅ Download {idx_botao + 1} concluído")
            else:
                st.warning(f"⚠️ Download {idx_botao + 1} pode ter falhado (timeout)")
            
            # Pausa entre downloads
            time.sleep(1)
            
        except Exception as e:
            st.warning(f"Erro no download {idx_botao + 1}: {str(e)}")
            continue
    
    return downloads_sucesso


def executar_downloads_automatico(nomes_pacientes, modo_headless=True):
    """
    Função para executar downloads de forma automática
    """
    
    # Configuração de pastas
    base_folder = os.path.join(os.path.dirname(__file__), "pdfs_abc")
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_folder = os.path.join(base_folder, timestamp)
    os.makedirs(output_folder, exist_ok=True)

    try:
        st.info("🚀 Iniciando navegador otimizado para GCP...")
        
        with ChromeManager(download_path=output_folder, headless=modo_headless) as driver:
            st.info("🤖 Modo headless ativado" if modo_headless else "🖥️ Modo visual ativado")
            
            # Inicializar monitor de downloads
            monitor = DownloadMonitor(output_folder)

            st.info("🔗 Acessando site...")
            driver.get("http://laboratorio.fmabc.br/matrixnet/wfrmBlank.aspx")
            st.success("🌐 Site carregado")

            # Login
            st.info("🔑 Fazendo login...")
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.NAME, "userLogin")))
            driver.find_element(By.NAME, "userLogin").send_keys("HOAN")
            driver.find_element(By.NAME, "userPassword").send_keys("5438")
            driver.find_element(By.ID, "btnEntrar").click()
            
            time.sleep(3)
            st.success("✅ Login realizado")

            if not verificar_driver_ativo(driver):
                st.error("❌ Driver perdeu conexão após login")
                return None

            st.info("🎯 Navegando para exames...")
            
            # Navegação com timeouts aumentados
            try:
                element = WebDriverWait(driver, 15).until(
                    EC.element_to_be_clickable((By.ID, "97-0B-E6-B7-F9-16-53-7C-C6-2C-E0-37-D0-67-F7-9E"))
                )
                driver.execute_script("arguments[0].click();", element)
                time.sleep(2)
                
                second_element = WebDriverWait(driver, 15).until(
                    EC.element_to_be_clickable((By.ID, "A1-2C-C6-AF-7F-6B-2B-3E-D5-00-73-F2-37-A1-D6-25"))
                )
                driver.execute_script("arguments[0].click();", second_element)
                time.sleep(2)
                
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
                    campo = WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "textoDigitado")))
                    campo.clear()
                    campo.send_keys(paciente)
                    driver.find_element(By.XPATH, "//button[contains(., 'Pesquisar')]").click()
                    time.sleep(3)

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
        logger.error(f"Erro crítico detalhado: {e}", exc_info=True)
        return None


def executar_robo_fmabc(nomes_pacientes=None):
    """
    Função principal que pode ser chamada tanto pela interface quanto programaticamente
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
