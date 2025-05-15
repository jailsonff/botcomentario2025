"""
Otimizador de Cookies para o Bot de Comentários do Instagram
Este módulo otimiza o armazenamento de perfis extraindo apenas os cookies essenciais,
reduzindo drasticamente o espaço em disco usado.
"""
import os
import json
import time
import shutil
from selenium import webdriver

class CookiesOptimizer:
    """Classe para otimizar o armazenamento de cookies e sessões do Instagram."""
    
    def __init__(self, base_path=None, original_profiles_dir="dolphin_profiles", optimized_sessions_dir="sessions_otimizadas"):
        """Inicializa o otimizador de cookies.
        
        Args:
            base_path: Caminho base onde estão os diretórios
            original_profiles_dir: Diretório com os perfis originais do Dolphin Anty
            optimized_sessions_dir: Diretório onde serão salvas as sessões otimizadas
        """
        self.base_path = base_path if base_path else ""
        
        # Se não houver um caminho base especificado, usar o caminho do bot original
        if not base_path:
            self.original_profiles_dir = os.path.join("C:\\Users\\Felix\\Desktop\\meu_bot_instagram", original_profiles_dir)
            self.optimized_sessions_dir = os.path.join("C:\\Users\\Felix\\Desktop\\meu_bot_instagram", optimized_sessions_dir)
        else:
            self.original_profiles_dir = os.path.join(self.base_path, original_profiles_dir)
            self.optimized_sessions_dir = os.path.join(self.base_path, optimized_sessions_dir)
        
        # Garantir que os diretórios existam
        if not os.path.exists(self.optimized_sessions_dir):
            os.makedirs(self.optimized_sessions_dir)
    
    def extrair_cookies_essenciais(self, driver):
        """Extrai apenas os cookies necessários para login no Instagram de um driver ativo.
        
        Args:
            driver: WebDriver do Selenium com uma sessão ativa do Instagram
            
        Returns:
            list: Lista de cookies essenciais
        """
        todos_cookies = driver.get_cookies()
        # Filtrar cookies relevantes (domínios do Instagram/Facebook)
        cookies_essenciais = [
            cookie for cookie in todos_cookies 
            if any(domain in cookie.get('domain', '') 
                  for domain in ['.instagram.com', 'instagram.com', '.facebook.com', 'facebook.com'])
        ]
        return cookies_essenciais
    
    def salvar_cookies(self, username, cookies):
        """Salva os cookies de um perfil em formato otimizado.
        
        Args:
            username: Nome do perfil
            cookies: Lista de cookies a serem salvos
            
        Returns:
            bool: True se salvo com sucesso, False caso contrário
        """
        try:
            # Criar diretório para o perfil
            perfil_dir = os.path.join(self.optimized_sessions_dir, username)
            os.makedirs(perfil_dir, exist_ok=True)
            
            # Salvar cookies em formato JSON
            cookies_file = os.path.join(perfil_dir, "cookies.json")
            with open(cookies_file, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)
                
            # Salvar metadata básico
            metadata = {
                "username": username,
                "login_status": "conectado",
                "last_extract": time.strftime("%Y-%m-%d %H:%M:%S"),
                "cookies_count": len(cookies)
            }
            
            metadata_file = os.path.join(perfil_dir, "metadata.json")
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
                
            return True
        except Exception as e:
            print(f"[DEBUG] Erro ao salvar cookies otimizados para {username}: {e}")
            return False
    
    def carregar_cookies(self, username):
        """Carrega os cookies otimizados de um perfil.
        
        Args:
            username: Nome do perfil
            
        Returns:
            list or None: Lista de cookies ou None se não encontrado
        """
        try:
            cookies_file = os.path.join(self.optimized_sessions_dir, username, "cookies.json")
            if os.path.exists(cookies_file):
                with open(cookies_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return None
        except Exception as e:
            print(f"[DEBUG] Erro ao carregar cookies para {username}: {e}")
            return None
    
    def restaurar_cookies_em_driver(self, driver, username):
        """Restaura os cookies otimizados em um driver.
        
        Args:
            driver: WebDriver do Selenium
            username: Nome do perfil
            
        Returns:
            bool: True se restaurado com sucesso, False caso contrário
        """
        try:
            cookies = self.carregar_cookies(username)
            if not cookies:
                print(f"[DEBUG] Cookies não encontrados para {username}")
                return False
                
            print(f"[DEBUG] Restaurando {len(cookies)} cookies para {username}")
            
            # Garantir que o driver esteja no domínio do Instagram antes de definir os cookies
            current_url = driver.current_url.lower()
            if not ("instagram.com" in current_url):
                driver.get("https://www.instagram.com/")
                time.sleep(2)
            
            # Excluir cookies atuais
            driver.delete_all_cookies()
            
            # Adicionar cookies salvos
            success_count = 0
            error_count = 0
            
            for cookie in cookies:
                try:
                    # Ignorar cookies incompletos ou inválidos
                    if 'name' not in cookie or 'value' not in cookie:
                        continue
                        
                    # Alguns cookies podem ter o atributo expiry que causa problemas
                    if 'expiry' in cookie:
                        cookie['expiry'] = int(cookie['expiry'])
                        
                    driver.add_cookie(cookie)
                    success_count += 1
                except Exception as e:
                    print(f"[DEBUG] Erro ao adicionar cookie: {e}")
                    error_count += 1
            
            print(f"[DEBUG] {success_count} cookies restaurados, {error_count} erros")
            
            # Atualizar para aplicar os cookies
            driver.refresh()
            time.sleep(2)
            
            return success_count > 0
            
        except Exception as e:
            print(f"[DEBUG] Erro ao restaurar cookies para {username}: {e}")
            return False
    
    def iniciar_navegador_sem_perfil(self):
        """Inicia um navegador Chrome limpo, sem perfil pesado.
        
        Returns:
            WebDriver: Instância do Chrome WebDriver
        """
        try:
            options = webdriver.ChromeOptions()
            options.add_argument("--start-maximized")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option('excludeSwitches', ['enable-automation'])
            options.add_experimental_option('useAutomationExtension', False)
            options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36")
            
            driver = webdriver.Chrome(options=options)
            return driver
        except Exception as e:
            print(f"[DEBUG] Erro ao iniciar navegador: {e}")
            return None
    
    def iniciar_navegador_com_cookies(self, username):
        """Inicia um navegador Chrome e restaura os cookies do perfil.
        
        Args:
            username: Nome do perfil
            
        Returns:
            tuple: (WebDriver, success_status, message)
        """
        try:
            # Verificar se existem cookies para o perfil
            if not self.cookies_existem(username):
                return None, False, "Cookies não encontrados"
            
            # Iniciar navegador
            driver = self.iniciar_navegador_sem_perfil()
            if not driver:
                return None, False, "Falha ao iniciar navegador"
            
            # Navegar para o Instagram
            driver.get("https://www.instagram.com/")
            time.sleep(2)
            
            # Restaurar cookies
            success = self.restaurar_cookies_em_driver(driver, username)
            if success:
                # Atualizar página após restaurar cookies
                driver.get("https://www.instagram.com/")
                time.sleep(3)
                
                return driver, True, "Cookies restaurados com sucesso"
            else:
                driver.quit()
                return None, False, "Falha ao restaurar cookies"
                
        except Exception as e:
            print(f"[DEBUG] Erro ao iniciar navegador com cookies: {e}")
            return None, False, f"Erro: {str(e)}"
    
    def cookies_existem(self, username):
        """Verifica se existem cookies otimizados para um perfil.
        
        Args:
            username: Nome do perfil
            
        Returns:
            bool: True se existem cookies, False caso contrário
        """
        cookies_file = os.path.join(self.optimized_sessions_dir, username, "cookies.json")
        return os.path.exists(cookies_file)
    
    def otimizar_perfil_existente(self, profile_name, dolphin_manager):
        """Extrai cookies de um perfil Dolphin existente e salva em formato otimizado.
        
        Args:
            profile_name: Nome do perfil
            dolphin_manager: Instância do DolphinAntyManager
            
        Returns:
            tuple: (success, message)
        """
        try:
            print(f"[DEBUG] Iniciando otimização do perfil {profile_name}")
            
            # Verificar se o perfil já está otimizado
            if self.cookies_existem(profile_name):
                return True, "Perfil já otimizado"
            
            # Verificar se o perfil original existe
            profile_dir = os.path.join(self.original_profiles_dir, profile_name)
            if not os.path.exists(profile_dir):
                return False, "Perfil original não encontrado"
            
            # Verificar se há um driver ativo para este perfil
            driver = dolphin_manager.get_profile_driver(profile_name)
            driver_criado = False
            
            if not driver:
                # Lançar o perfil se não estiver ativo
                success, message = dolphin_manager.launch_profile_instagram(profile_name)
                if not success:
                    return False, f"Falha ao lançar perfil: {message}"
                    
                # Obter o driver após o lançamento
                driver = dolphin_manager.get_profile_driver(profile_name)
                if not driver:
                    return False, "Driver não encontrado após lançamento"
                    
                driver_criado = True
            
            # Extrair cookies
            cookies = self.extrair_cookies_essenciais(driver)
            if not cookies:
                if driver_criado:
                    dolphin_manager.close_profile_driver(profile_name)
                return False, "Nenhum cookie extraído"
            
            # Salvar cookies
            if not self.salvar_cookies(profile_name, cookies):
                if driver_criado:
                    dolphin_manager.close_profile_driver(profile_name)
                return False, "Falha ao salvar cookies"
            
            # Fechar o driver se foi criado por este método
            if driver_criado:
                dolphin_manager.close_profile_driver(profile_name)
            
            return True, f"{len(cookies)} cookies otimizados com sucesso"
            
        except Exception as e:
            print(f"[DEBUG] Erro ao otimizar perfil {profile_name}: {e}")
            return False, f"Erro: {str(e)}"
    
    def limpar_cache_dolphin(self, preservar_dias=7):
        """Limpa diretórios de cache dos perfis Dolphin Anty.
        
        Args:
            preservar_dias: Não limpar perfis acessados nos últimos X dias
            
        Returns:
            tuple: (total_profiles, cleaned_profiles, saved_space)
        """
        try:
            # Verificar se o diretório de perfis existe
            if not os.path.exists(self.original_profiles_dir):
                return 0, 0, "0 MB"
                
            # Calcular data limite para não limpar perfis recentes
            agora = time.time()
            tempo_min = agora - (preservar_dias * 24 * 60 * 60)  # Converter dias para segundos
            
            # Contadores
            total_profiles = 0
            cleaned_profiles = 0
            bytes_liberados = 0
            
            # Processar cada perfil
            for profile_name in os.listdir(self.original_profiles_dir):
                profile_dir = os.path.join(self.original_profiles_dir, profile_name)
                
                # Pular arquivos e diretórios especiais
                if not os.path.isdir(profile_dir) or profile_name == "all_profiles_metadata.json":
                    continue
                    
                total_profiles += 1
                
                # Verificar se o perfil foi acessado recentemente
                metadata_file = os.path.join(profile_dir, "metadata.json")
                skip_clean = False
                
                if os.path.exists(metadata_file):
                    try:
                        # Verificar última atualização do arquivo de metadados
                        mod_time = os.path.getmtime(metadata_file)
                        if mod_time > tempo_min:
                            skip_clean = True
                    except:
                        pass
                
                if skip_clean:
                    continue
                
                # Lista de diretórios que contêm cache e podem ser limpos
                cache_dirs = [
                    'Cache', 'Code Cache', 'GPUCache', 'DawnCache', 
                    'Service Worker', 'Session Storage', 'CacheStorage',
                    'IndexedDB', 'blob_storage'
                ]
                
                # Lista de arquivos que podem ser limpos
                cache_files = [
                    'Cookies-journal', 'History-journal', 'Network Action Predictor',
                    'Visited Links', 'Network Persistent State', 'QuotaManager',
                    'Extension State', 'Extension Rules', 'Last Session', 'Last Tabs'
                ]
                
                # Limpar diretórios de cache
                for cache_dir in cache_dirs:
                    dir_path = os.path.join(profile_dir, cache_dir)
                    if os.path.exists(dir_path):
                        # Calcular tamanho antes de remover
                        dir_size = self._get_dir_size(dir_path)
                        bytes_liberados += dir_size
                        
                        # Remover diretório
                        shutil.rmtree(dir_path, ignore_errors=True)
                
                # Limpar arquivos de cache
                for cache_file in cache_files:
                    file_path = os.path.join(profile_dir, cache_file)
                    if os.path.exists(file_path):
                        bytes_liberados += os.path.getsize(file_path)
                        os.remove(file_path)
                
                cleaned_profiles += 1
                
            # Converter bytes para MB ou GB para facilitar leitura
            saved_space = bytes_liberados
            if saved_space > 1024 * 1024 * 1024:
                saved_space_str = f"{saved_space / (1024 * 1024 * 1024):.2f} GB"
            else:
                saved_space_str = f"{saved_space / (1024 * 1024):.2f} MB"
                
            return total_profiles, cleaned_profiles, saved_space_str
                
        except Exception as e:
            print(f"[DEBUG] Erro ao limpar cache: {e}")
            return 0, 0, "0 MB"
    
    def _get_dir_size(self, path):
        """Calcula o tamanho total de um diretório recursivamente."""
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                try:
                    total_size += os.path.getsize(fp)
                except:
                    pass
        return total_size
    
    def remover_perfis_otimizados_invalidos(self):
        """Remove perfis otimizados que não têm cookies válidos."""
        removidos = 0
        
        try:
            for username in os.listdir(self.optimized_sessions_dir):
                perfil_dir = os.path.join(self.optimized_sessions_dir, username)
                if not os.path.isdir(perfil_dir):
                    continue
                    
                cookies_file = os.path.join(perfil_dir, "cookies.json")
                if not os.path.exists(cookies_file):
                    shutil.rmtree(perfil_dir, ignore_errors=True)
                    removidos += 1
        except Exception as e:
            print(f"[DEBUG] Erro ao remover perfis inválidos: {e}")
            
        return removidos
