"""
DolphinAntyManager para o Bot de Comentários - Versão com armazenamento eficiente de cookies.
Esta versão trabalha com o otimizador de cookies para reduzir drasticamente 
o tamanho da pasta de perfis.
"""
import os
import shutil
import time
import json
import random
import string
from PyQt5.QtCore import QThread, pyqtSignal
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException

from cookies_optimizer import CookiesOptimizer

class DirectoryRemoverWorker(QThread):
    """Worker para remover diretórios em background, evitando bloqueio da interface."""
    removal_completed = pyqtSignal(str, bool)  # Sinal para informar quando a remoção for concluída (perfil, sucesso)
    
    def __init__(self, directory_path, profile_name):
        super().__init__()
        self.directory_path = directory_path
        self.profile_name = profile_name
    
    def run(self):
        """Remove um diretório em uma thread separada"""
        try:
            print(f"[DEBUG] Worker: Removendo diretório do perfil com erro: {self.profile_name}")
            # Aguarda um momento para garantir que outros processos tenham liberado o diretório
            time.sleep(0.5)
            # Remove o diretório recursivamente
            shutil.rmtree(self.directory_path, ignore_errors=True)
            # Verifica se a remoção foi bem-sucedida
            success = not os.path.exists(self.directory_path)
            # Emite o sinal com o resultado
            self.removal_completed.emit(self.profile_name, success)
        except Exception as e:
            print(f"[DEBUG] Worker: Erro ao remover diretório {self.directory_path}: {e}")
            self.removal_completed.emit(self.profile_name, False)

class DolphinAntyManager:
    """Versão otimizada do gerenciador Dolphin Anty que usa cookies em vez de perfis inteiros."""
    
    def __init__(self, base_bot_path=None, profiles_dir="dolphin_profiles", optimized_sessions_dir="sessions_otimizadas", browser_type="chrome"):
        """Inicializa o gerenciador otimizado de perfis do Dolphin Anty.
        
        Args:
            base_bot_path: Caminho base do bot
            profiles_dir: Diretório para os perfis originais (legado)
            optimized_sessions_dir: Diretório para as sessões otimizadas
            browser_type: Tipo de navegador (chrome, edge, etc.)
        """
        self.base_bot_path = base_bot_path
        
        # Se não for fornecido um caminho base, usar a pasta do bot original
        if not base_bot_path:
            self.profiles_dir = os.path.join("C:\\Users\\Felix\\Desktop\\meu_bot_instagram", profiles_dir)
            self.optimized_sessions_dir = os.path.join("C:\\Users\\Felix\\Desktop\\meu_bot_instagram", optimized_sessions_dir)
        else:
            # Combinar base_bot_path com os diretórios se não forem caminhos absolutos
            if not os.path.isabs(profiles_dir):
                self.profiles_dir = os.path.join(base_bot_path, profiles_dir)
            else:
                self.profiles_dir = profiles_dir
                
            if not os.path.isabs(optimized_sessions_dir):
                self.optimized_sessions_dir = os.path.join(base_bot_path, optimized_sessions_dir)
            else:
                self.optimized_sessions_dir = optimized_sessions_dir
                
        self.browser_type = browser_type
        self.profile_drivers = {}
        
        # Criar diretórios necessários
        if not os.path.exists(self.optimized_sessions_dir):
            os.makedirs(self.optimized_sessions_dir)
            
        # Inicializar o otimizador de cookies
        self.cookies_optimizer = CookiesOptimizer(base_bot_path, profiles_dir, optimized_sessions_dir)
        
    def get_profile_driver(self, profile_name):
        """Retorna o driver do navegador para um perfil específico, se estiver ativo.
        
        Args:
            profile_name (str): Nome do perfil para o qual obter o driver
            
        Returns:
            WebDriver or None: O driver do navegador se estiver ativo, ou None caso contrário
        """
        return self.profile_drivers.get(profile_name)
        
    def get_profile_metadata(self, profile_name):
        """Obtém os metadados de um perfil.
        
        Args:
            profile_name: Nome do perfil
            
        Returns:
            dict: Metadados do perfil
        """
        try:
            # Primeiro tentar ler os metadados da sessão otimizada
            optimized_metadata_file = os.path.join(self.optimized_sessions_dir, profile_name, "metadata.json")
            if os.path.exists(optimized_metadata_file):
                with open(optimized_metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            
            # Se não encontrar na sessão otimizada, tentar no perfil original
            original_metadata_file = os.path.join(self.profiles_dir, profile_name, "metadata.json")
            if os.path.exists(original_metadata_file):
                with open(original_metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            
            # Se não encontrar, retornar metadados mínimos
            return {
                "username": profile_name,
                "bot_login_status": "desconhecido",
                "last_login": "nunca"
            }
            
        except Exception as e:
            print(f"[DEBUG] Erro ao ler metadados para {profile_name}: {e}")
            return {
                "username": profile_name,
                "bot_login_status": "erro",
                "error": str(e)
            }
            
    def update_profile_bot_login_status(self, profile_name, status, message=None):
        """Atualiza o status de login de um perfil específico.
        
        Args:
            profile_name (str): Nome do perfil a ser atualizado
            status (str): Status atual do perfil ('logando', 'success', 'failed', etc)
            message (str, optional): Mensagem adicional sobre o status
        
        Returns:
            bool: True se a atualização foi bem-sucedida, False caso contrário
        """
        try:
            # Primeiro, obter metadados existentes
            metadata = self.get_profile_metadata(profile_name)
            
            # Atualizar campos relevantes
            metadata["bot_login_status"] = status
            metadata["last_update"] = time.strftime("%Y-%m-%d %H:%M:%S")
            
            if message:
                metadata["status_message"] = message
            
            # Salvar metadados na sessão otimizada
            perfil_dir = os.path.join(self.optimized_sessions_dir, profile_name)
            os.makedirs(perfil_dir, exist_ok=True)
            
            metadata_file = os.path.join(perfil_dir, "metadata.json")
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            return True
            
        except Exception as e:
            print(f"[DEBUG] Erro ao atualizar status para {profile_name}: {e}")
            return False
    
    def get_all_profiles_metadata(self):
        """Retorna um dicionário com metadados de todos os perfis.
        
        Returns:
            dict: Dicionário com nome do perfil como chave e metadados como valor
        """
        profiles_metadata = {}
        
        # Função para processar perfis de um diretório
        def process_profiles_dir(dir_path, is_optimized=False):
            if not os.path.exists(dir_path):
                return
                
            for profile_name in os.listdir(dir_path):
                # Pular arquivos e perfis já processados
                profile_path = os.path.join(dir_path, profile_name)
                if not os.path.isdir(profile_path) or profile_name in profiles_metadata:
                    continue
                
                # Verificar se é um perfil válido (tem metadata.json)
                metadata_file = os.path.join(profile_path, "metadata.json")
                if not os.path.exists(metadata_file):
                    continue
                    
                try:
                    # Ler metadados
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    
                    # Adicionar flag de otimizado
                    metadata["is_optimized"] = is_optimized
                    
                    # Verificar último acesso
                    metadata["last_accessed"] = time.strftime(
                        "%Y-%m-%d %H:%M:%S", 
                        time.localtime(os.path.getmtime(metadata_file))
                    )
                    
                    profiles_metadata[profile_name] = metadata
                    
                except Exception as e:
                    print(f"[DEBUG] Erro ao ler metadados de {profile_name}: {e}")
                    profiles_metadata[profile_name] = {
                        "username": profile_name,
                        "is_optimized": is_optimized,
                        "error": str(e)
                    }
        
        # Processar perfis originais e otimizados
        process_profiles_dir(self.profiles_dir, False)
        process_profiles_dir(self.optimized_sessions_dir, True)
        
        return profiles_metadata
        
    def launch_profile_instagram(self, profile_name, go_to_instagram_home=True):
        """Lança um perfil otimizado no Instagram.
        
        Primeiro tenta usar a sessão otimizada (cookies). Se não encontrar ou se falhar,
        utiliza o método legado e depois otimiza a sessão.
        
        Args:
            profile_name (str): Nome do perfil a ser lançado
            go_to_instagram_home (bool): Se True, navega para a página inicial do Instagram
            
        Returns:
            tuple: (success, message) ou (driver, success, message)
        """
        # Verificar se o driver já está aberto para este perfil
        if profile_name in self.profile_drivers:
            driver = self.profile_drivers[profile_name]
            try:
                # Verificar se o driver ainda é utilizável
                current_url = driver.current_url
                print(f"[DEBUG] Driver para {profile_name} já está aberto em: {current_url}")
                
                # Navegar para a página inicial do Instagram se necessário
                if go_to_instagram_home and "instagram.com" not in current_url:
                    driver.get("https://www.instagram.com/")
                
                return True, f"Driver já estava aberto para {profile_name}"
                
            except Exception:
                # Driver está em estado inválido, fechá-lo e reabri-lo
                print(f"[DEBUG] Driver para {profile_name} estava em estado inválido, reiniciando")
                try:
                    driver.quit()
                except:
                    pass
                del self.profile_drivers[profile_name]
        
        # Atualizar status antes de iniciar
        self.update_profile_bot_login_status(profile_name, "iniciando", "Iniciando navegador")
        
        # Verificar se existem cookies otimizados para este perfil
        if self.cookies_optimizer.cookies_existem(profile_name):
            print(f"[DEBUG] Cookies otimizados encontrados para {profile_name}")
            
            # Iniciar navegador com cookies
            driver, success, message = self.cookies_optimizer.iniciar_navegador_com_cookies(profile_name)
            
            if success:
                # Armazenar driver na lista de ativos
                self.profile_drivers[profile_name] = driver
                
                # Navegar para a página inicial do Instagram se necessário
                if go_to_instagram_home:
                    driver.get("https://www.instagram.com/")
                
                # Verificar se está logado
                if self.is_logged_in(driver):
                    print(f"[DEBUG] Login automático bem-sucedido para {profile_name}")
                    self.update_profile_bot_login_status(profile_name, "conectado", "Login restaurado com cookies")
                    return True, "Login restaurado com sucesso"
                else:
                    print(f"[DEBUG] Cookies existem mas login falhou para {profile_name}")
                    self.update_profile_bot_login_status(profile_name, "login_necessario", "Cookies inválidos")
                    # Aqui pode-se tentar login manual/automatizado
                    return True, "Navegador aberto com cookies, mas login manual necessário"
            else:
                print(f"[DEBUG] Falha ao iniciar navegador com cookies para {profile_name}: {message}")
                self.update_profile_bot_login_status(profile_name, "erro", f"Falha ao iniciar: {message}")
                return False, message
        else:
            print(f"[DEBUG] Cookies otimizados não encontrados para {profile_name}")
            self.update_profile_bot_login_status(profile_name, "tentando_legado", "Cookies otimizados não encontrados, tentando método tradicional")
            
            # Tentar iniciar navegador pelo método tradicional (perfil legado)
            driver = self.cookies_optimizer.iniciar_navegador_sem_perfil()
            if not driver:
                self.update_profile_bot_login_status(profile_name, "erro", "Falha ao iniciar navegador tradicional")
                return False, "Falha ao iniciar navegador tradicional"
            
            # Navegar para o Instagram
            driver.get("https://www.instagram.com/")
            time.sleep(3)
            
            # Armazenar driver na lista de ativos
            self.profile_drivers[profile_name] = driver
            
            self.update_profile_bot_login_status(profile_name, "login_necessario", "Navegador aberto, login necessário")
            
            # Após login manual/automatizado, otimizar perfil
            success, msg = self.cookies_optimizer.otimizar_perfil_existente(profile_name, self)
            if success:
                print(f"[DEBUG] Perfil {profile_name} otimizado após login.")
                self.update_profile_bot_login_status(profile_name, "conectado", "Perfil otimizado após login tradicional")
                return True, "Perfil otimizado após login tradicional"
            else:
                print(f"[DEBUG] Não foi possível otimizar perfil {profile_name} após login: {msg}")
                self.update_profile_bot_login_status(profile_name, "erro", f"Não foi possível otimizar perfil após login: {msg}")
                return False, f"Não foi possível otimizar perfil após login: {msg}"
    
    def is_logged_in(self, driver):
        """Verifica se o perfil está logado no Instagram.
        
        Args:
            driver: WebDriver do Selenium
            
        Returns:
            bool: True se estiver logado, False caso contrário
        """
        try:
            # Verificar elementos que indicam que está logado
            logged_in_elements = [
                # Verificar o avatar/foto de perfil no topo
                "//div[@role='button']//*[local-name()='svg' and @aria-label='Seu perfil']",
                "//div[@role='button']//*[local-name()='svg' and @aria-label='Your profile']",
                
                # Verificar o ícone de perfil (alternativo)
                "//nav//img[@data-testid='user-avatar']",
                
                # Verificar botão de mensagens
                "//div[@role='button']//*[local-name()='svg' and @aria-label='Mensagens']",
                "//div[@role='button']//*[local-name()='svg' and @aria-label='Messenger']",
                
                # Verificar botão de notificações
                "//div[@role='button']//*[local-name()='svg' and @aria-label='Notificações']",
                "//div[@role='button']//*[local-name()='svg' and @aria-label='Notifications']",
                
                # Verificar feed
                "//span[text()='Sugestões para você']",
                "//span[text()='Suggested for you']",
                
                # Links de navegação no menu
                "//span[text()='Página inicial']",
                "//span[text()='Home']"
            ]
            
            for selector in logged_in_elements:
                try:
                    elements = driver.find_elements(By.XPATH, selector)
                    if elements and any(e.is_displayed() for e in elements):
                        print(f"[DEBUG] is_logged_in: Encontrado elemento logado: {selector}")
                        return True
                except:
                    continue
                    
            # Verificar elementos que indicam que NÃO está logado
            logged_out_elements = [
                # Botão de login
                "//button[text()='Entrar']",
                "//button[text()='Log In']",
                
                # Outros elementos da página de login
                "//input[@name='username']",
                "//input[@name='password']",
                "//span[text()='Cadastre-se']",
                "//span[text()='Sign up']"
            ]
            
            for selector in logged_out_elements:
                try:
                    elements = driver.find_elements(By.XPATH, selector)
                    if elements and any(e.is_displayed() for e in elements):
                        print(f"[DEBUG] is_logged_in: Encontrado elemento deslogado: {selector}")
                        return False
                except:
                    continue
            
            # Se não encontrou nenhum indicador claro, verificar URL
            current_url = driver.current_url.lower()
            if "instagram.com/accounts/login" in current_url:
                return False
                
            return False  # Em caso de dúvida, assumir que não está logado
            
        except Exception as e:
            print(f"[DEBUG] Erro ao verificar login: {e}")
            return False
    
    def close_profile_driver(self, profile_name):
        """Fecha o driver de um perfil específico.
        
        Args:
            profile_name: Nome do perfil
            
        Returns:
            bool: True se fechado com sucesso, False caso contrário
        """
        if profile_name in self.profile_drivers:
            try:
                driver = self.profile_drivers[profile_name]
                driver.quit()
                del self.profile_drivers[profile_name]
                print(f"[DEBUG] Driver para {profile_name} fechado com sucesso")
                return True
            except Exception as e:
                print(f"[DEBUG] Erro ao fechar driver para {profile_name}: {e}")
                try:
                    del self.profile_drivers[profile_name]
                except:
                    pass
                return False
        return False
        
    def attempt_login_instagram(self, driver, username, password, max_retries=2):
        """Tenta fazer login no Instagram.
        
        Args:
            driver: WebDriver do Selenium
            username: Nome de usuário do Instagram
            password: Senha do Instagram
            max_retries: Número máximo de tentativas
            
        Returns:
            tuple: (success, message)
        """
        try:
            # Verificar se já está logado
            if self.is_logged_in(driver):
                print(f"[DEBUG] Perfil já está logado no Instagram: {username}")
                self._otimizar_perfil_apos_login(driver, username)
                return True, "Já estava logado"
            
            # Navegar para a página de login
            print(f"[DEBUG] Navegando para página de login do Instagram para {username}")
            driver.get("https://www.instagram.com/accounts/login/")
            
            # Aguardar carregamento da página de login
            wait = WebDriverWait(driver, 10)
            
            for tentativa in range(max_retries):
                try:
                    print(f"[DEBUG] Tentativa {tentativa + 1} de login para {username}")
                    
                    # Esperar elementos de login
                    username_input = wait.until(EC.presence_of_element_located((By.NAME, "username")))
                    password_input = wait.until(EC.presence_of_element_located((By.NAME, "password")))
                    
                    # Limpar campos e inserir credenciais
                    username_input.clear()
                    username_input.send_keys(username)
                    
                    password_input.clear()
                    password_input.send_keys(password)
                    
                    # Clicar no botão de login
                    login_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']")))
                    login_button.click()
                    
                    # Aguardar carregamento após login
                    time.sleep(5)
                    
                    # Verificar se login foi bem sucedido
                    if self.is_logged_in(driver):
                        print(f"[DEBUG] Login bem-sucedido para {username}")
                        self._otimizar_perfil_apos_login(driver, username)
                        return True, "Login bem-sucedido"
                    
                    # Verificar mensagens de erro
                    try:
                        error_message = driver.find_element(By.ID, "slfErrorAlert").text
                        if error_message:
                            return False, f"Erro de login: {error_message}"
                    except:
                        pass
                    
                    time.sleep(1)
                    
                except Exception as e:
                    print(f"[DEBUG] Erro na tentativa {tentativa + 1} de login: {str(e)}")
                    if tentativa < max_retries - 1:
                        time.sleep(1)
                        continue
                    else:
                        return False, f"Erro ao tentar login: {str(e)}"
            
            return False, "Falha no login após várias tentativas"
            
        except Exception as e:
            print(f"[DEBUG] Erro no processo de login: {str(e)}")
            return False, f"Erro no processo de login: {str(e)}"
    
    def _otimizar_perfil_apos_login(self, driver, username):
        """Otimiza um perfil após login bem-sucedido extraindo e salvando cookies.
        
        Args:
            driver: WebDriver do Selenium com login ativo
            username: Nome do perfil
        """
        try:
            print(f"[DEBUG] Otimizando perfil {username} após login bem-sucedido")
            
            # Extrair cookies
            cookies = self.cookies_optimizer.extrair_cookies_essenciais(driver)
            if cookies:
                # Salvar cookies
                if self.cookies_optimizer.salvar_cookies(username, cookies):
                    print(f"[DEBUG] Perfil {username} otimizado com sucesso: {len(cookies)} cookies salvos")
                    return True
                else:
                    print(f"[DEBUG] Falha ao salvar cookies para {username}")
            else:
                print(f"[DEBUG] Nenhum cookie extraído para {username}")
            
            return False
        except Exception as e:
            print(f"[DEBUG] Erro ao otimizar perfil após login: {e}")
            return False
