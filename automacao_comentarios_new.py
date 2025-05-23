import time
import random
import os
import pyperclip
import threading
from PyQt5.QtCore import QThread, pyqtSignal
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

class AutomacaoComentariosWorker(QThread):
    """
    Worker especializado para executar comentÃ¡rios automatizados em posts do Instagram usando perfis do Dolphin Anty.
    """
    # Sinais: perfil, aÃ§Ã£o, sucesso, mensagem
    acao_concluida = pyqtSignal(str, str, bool, str)
    progresso_atualizado = pyqtSignal(int, int)  # aÃ§Ãµes concluÃ­das, total de aÃ§Ãµes
    status_update = pyqtSignal(str)
    automacao_concluida = pyqtSignal()

    def __init__(self, dolphin_manager, post_url, perfis, total_acoes, perfis_simultaneos, 
                 tempo_entre_acoes, texto_comentario="", parent=None, manter_navegador_aberto=False):
        super().__init__(parent)
        self.dolphin_manager = dolphin_manager
        self.post_url = post_url
        self.perfis = perfis  # Lista de nomes de usuÃ¡rio dos perfis
        self.total_acoes = total_acoes
        self.perfis_simultaneos = perfis_simultaneos
        self.tempo_entre_acoes = tempo_entre_acoes
        self.manter_navegador_aberto = manter_navegador_aberto
        
        # Tratar o texto_comentario como uma lista de comentÃ¡rios
        if texto_comentario:
            # Dividir o texto em linhas e filtrar linhas vazias
            self.lista_comentarios = [linha.strip() for linha in texto_comentario.split('\n') if linha.strip()]
        else:
            self.lista_comentarios = []
        self._stop_flag = False
        self.acoes_concluidas = 0
        self.workers_ativos = {}  # Armazena os drivers ativos por perfil

    def stop(self):
        """Para a execuÃ§Ã£o da automaÃ§Ã£o."""
        self._stop_flag = True
        self.workers_ativos.clear()

    def run(self):
        """Executa a automaÃ§Ã£o de comentÃ¡rios nos perfis."""
        if not self.perfis or not self.post_url:
            self.status_update.emit("âŒ Erro: URL do post ou lista de perfis vazia.")
            self.automacao_concluida.emit()
            return

        # Verifica se hÃ¡ comentÃ¡rios disponÃ­veis
        if not self.lista_comentarios:
            self.status_update.emit("âŒ Erro: Nenhum comentÃ¡rio definido.")
            self.automacao_concluida.emit()
            return

        # Verifica se o nÃºmero de aÃ§Ãµes Ã© maior que o nÃºmero de perfis disponÃ­veis
        if self.total_acoes > len(self.perfis):
            self.status_update.emit(f"âš ï¸ Aviso: O nÃºmero de aÃ§Ãµes ({self.total_acoes}) Ã© maior que o nÃºmero de perfis disponÃ­veis ({len(self.perfis)}). Alguns perfis serÃ£o usados mais de uma vez.")

        # Embaralha a lista de perfis para usar em ordem aleatÃ³ria
        perfis_disponiveis = self.perfis.copy()
        random.shuffle(perfis_disponiveis)

        # Inicia o loop de automaÃ§Ã£o
        self.acoes_concluidas = 0
        self.progresso_atualizado.emit(self.acoes_concluidas, self.total_acoes)
        
        # Criar um lock para acesso thread-safe Ã  variÃ¡vel acoes_concluidas
        self.acoes_lock = threading.Lock()
        
        # Criar uma lista para controlar os perfis jÃ¡ usados
        self.perfis_em_execucao = []
        
        while self.acoes_concluidas < self.total_acoes and not self._stop_flag:
            # Verifica quantos workers estÃ£o ativos no momento
            workers_ativos_count = len(self.workers_ativos)
            
            # Se jÃ¡ temos o mÃ¡ximo de workers ativos, aguarda
            if workers_ativos_count >= self.perfis_simultaneos:
                time.sleep(1)
                continue
            
            # Verificar quantas aÃ§Ãµes jÃ¡ foram iniciadas (em execuÃ§Ã£o + concluÃ­das)
            with self.acoes_lock:
                acoes_em_andamento = len(self.perfis_em_execucao)
                acoes_totais_iniciadas = acoes_em_andamento + self.acoes_concluidas
                
                # Se jÃ¡ iniciamos todas as aÃ§Ãµes necessÃ¡rias, apenas aguarda a conclusÃ£o
                if acoes_totais_iniciadas >= self.total_acoes:
                    time.sleep(1)
                    continue
            
            # Selecionar prÃ³ximo perfil disponÃ­vel
            perfil_escolhido = None
            for perfil in perfis_disponiveis:
                if perfil not in self.perfis_em_execucao and perfil not in self.workers_ativos:
                    perfil_escolhido = perfil
                    break
            
            # Se nÃ£o encontrou perfil disponÃ­vel, tentar reutilizar um perfil
            if not perfil_escolhido and self.total_acoes > len(self.perfis):
                # Verificar quais perfis jÃ¡ foram usados mas nÃ£o estÃ£o ativos no momento
                perfis_ja_usados = [p for p in self.perfis if p not in self.perfis_em_execucao and p not in self.workers_ativos]
                if perfis_ja_usados:
                    perfil_escolhido = random.choice(perfis_ja_usados)
            
            # Se ainda nÃ£o encontrou perfil, aguardar
            if not perfil_escolhido:
                time.sleep(1)
                continue
            
            # Adicionar perfil Ã  lista de perfis em execuÃ§Ã£o
            self.perfis_em_execucao.append(perfil_escolhido)
            
            # Iniciar thread para executar a aÃ§Ã£o neste perfil
            self.status_update.emit(f"ðŸš€ Iniciando aÃ§Ã£o com perfil '{perfil_escolhido}'")
            threading.Thread(target=self._executar_acao_perfil, args=(perfil_escolhido,)).start()
            
            # Aguardar intervalo entre aÃ§Ãµes
            intervalo = random.uniform(self.tempo_entre_acoes * 0.8, self.tempo_entre_acoes * 1.2)  # VariaÃ§Ã£o de Â±20%
            self.status_update.emit(f"â±ï¸ Aguardando {intervalo:.1f} segundos antes da prÃ³xima aÃ§Ã£o...")
            time.sleep(intervalo)
        
        # Aguardar todos os workers concluÃ­rem
        while self.workers_ativos and not self._stop_flag:
            self.status_update.emit(f"âŒ› Aguardando {len(self.workers_ativos)} workers concluÃ­rem...")
            time.sleep(2)
        
        # Emitir sinal de conclusÃ£o
        self.status_update.emit(f"âœ… AutomaÃ§Ã£o concluÃ­da! {self.acoes_concluidas} comentÃ¡rios realizados.")
        self.automacao_concluida.emit()

    def _executar_acao_perfil(self, username):
        """Executa a aÃ§Ã£o para um perfil especÃ­fico."""
        if self._stop_flag:
            if username in self.perfis_em_execucao:
                self.perfis_em_execucao.remove(username)
            return
        
        # Tentar obter um comentÃ¡rio aleatÃ³rio
        if not self.lista_comentarios:
            self.status_update.emit(f"âŒ Erro: Lista de comentÃ¡rios vazia para '{username}'.")
            if username in self.perfis_em_execucao:
                self.perfis_em_execucao.remove(username)
            return
        
        comentario = random.choice(self.lista_comentarios)
        
        self.status_update.emit(f"ðŸ”„ Iniciando navegador para '{username}'...")
        
        # Iniciar navegador e abrir post
        success, message = self.dolphin_manager.launch_profile_instagram(username, go_to_instagram_home=False)
        
        if not success:
            self.status_update.emit(f"âŒ Erro ao abrir navegador para '{username}': {message}")
            if username in self.perfis_em_execucao:
                self.perfis_em_execucao.remove(username)
            return
        
        driver = self.dolphin_manager.get_profile_driver(username)
        if not driver:
            self.status_update.emit(f"âŒ Erro: Driver nÃ£o encontrado para '{username}'.")
            if username in self.perfis_em_execucao:
                self.perfis_em_execucao.remove(username)
            return
        
        # Adicionar Ã  lista de workers ativos
        self.workers_ativos[username] = driver
        
        # Navegar para o post
        try:
            self.status_update.emit(f"ðŸŒ Navegando para URL do post ({username})...")
            driver.get(self.post_url)
            
            # Aguardar carregamento da pÃ¡gina
            self._aguardar_carregamento_pagina(driver, username)
            
            # Aguardar um tempo para garantir que a pÃ¡gina esteja totalmente carregada (crucial para mÃºltiplos perfis)
            time.sleep(3)
            
            # IMPORTANTE: Para perfis mÃºltiplos, precisamos dar foco para este navegador
            try:
                driver.execute_script("window.focus();")
                time.sleep(1)
                # Mover mouse para o centro da tela para ativaÃ§Ã£o
                action = ActionChains(driver)
                action.move_by_offset(0, 0).click().perform()
                self.status_update.emit(f"ðŸ‘ï¸ Dando foco ao navegador de '{username}'...")
                time.sleep(0.5)
            except Exception as e:
                self.status_update.emit(f"âš ï¸ Erro ao ativar navegador: {str(e)}")
            
            # Verificar se estÃ¡ logado
            if not self.dolphin_manager.is_logged_in(driver):
                self.status_update.emit(f"ðŸ”‘ Perfil '{username}' nÃ£o estÃ¡ logado. Tentando login automÃ¡tico...")
                login_success, login_message = self.dolphin_manager.attempt_login_instagram(
                    driver, username, "sua_senha_aqui"
                )
                
                if not login_success:
                    self.status_update.emit(f"âŒ Falha no login para '{username}': {login_message}")
                    driver.quit()
                    if username in self.workers_ativos:
                        del self.workers_ativos[username]
                    if username in self.perfis_em_execucao:
                        self.perfis_em_execucao.remove(username)
                    return
                
                # ApÃ³s login bem-sucedido, navegar novamente para o post
                driver.get(self.post_url)
                self._aguardar_carregamento_pagina(driver, username)
            
            # Lista para rastrear aÃ§Ãµes realizadas
            acoes_realizadas = []
            
            # Realizar comentÃ¡rio
            self.status_update.emit(f"ðŸ’¬ Tentando comentar com perfil '{username}'...")
            comentario_realizado = self._comentar_post(driver, username, comentario, acoes_realizadas)
            
            if not comentario_realizado:
                self.status_update.emit(f"âŒ Falha ao comentar com perfil '{username}'.")
                driver.quit()
                if username in self.workers_ativos:
                    del self.workers_ativos[username]
                if username in self.perfis_em_execucao:
                    self.perfis_em_execucao.remove(username)
                return
            
        except Exception as e:
            self.status_update.emit(f"âŒ Erro durante execuÃ§Ã£o para '{username}': {str(e)}")
            driver.quit()
            if username in self.workers_ativos:
                del self.workers_ativos[username]
            if username in self.perfis_em_execucao:
                self.perfis_em_execucao.remove(username)
            return

    def _aguardar_carregamento_pagina(self, driver, username):
        """Aguarda o carregamento da pÃ¡gina."""
        try:
            self.status_update.emit(f"â³ Aguardando carregamento da pÃ¡gina para '{username}'...")
            wait = WebDriverWait(driver, 30)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "article")))
            
            # Reduzido o tempo de espera apÃ³s carregar o artigo para agilizar o comentÃ¡rio
            time.sleep(2)  # Tempo suficiente para garantir que podemos interagir com a pÃ¡gina
            
            # Procurar explicitamente pelo campo de comentÃ¡rio para garantir que estÃ¡ carregado
            seletores_campo_comentario = [
                "//form[contains(@class, 'comment')]//textarea",
                "//textarea[contains(@placeholder, 'coment')]",
                "//textarea[contains(@aria-label, 'comment')]",
                "//*[@role='textbox' and contains(@aria-label, 'coment')]",
                "//*[@placeholder='Adicione um comentÃ¡rio...']",
                "//*[@placeholder='Add a commentâ€¦']"
            ]
            
            for seletor in seletores_campo_comentario:
                try:
                    wait.until(EC.presence_of_element_located((By.XPATH, seletor)))
                    self.status_update.emit(f"âœ… Campo de comentÃ¡rio encontrado e pronto para '{username}'")
                    return  # Encontrou o campo, podemos continuar
                except:
                    continue
            
            # Se nÃ£o encontrou o campo, tentar rolar a pÃ¡gina
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            time.sleep(1)
        except Exception as e:
            self.status_update.emit(f"âš ï¸ Erro ao aguardar carregamento: {str(e)}")

    def _comentar_post(self, driver, username, texto_comentario, acoes_realizadas):
        """Tenta adicionar um comentÃ¡rio ao post."""
        max_tentativas = 5  # Aumentado o nÃºmero de tentativas
        comentario_realizado = False
        
        # Apenas dar foco ao navegador antes de interagir, sem rolagem
        try:
            # IMPORTANTE: Dar foco ao navegador antes de interagir
            driver.execute_script("window.focus();")
            time.sleep(0.5)
        except Exception as e:
            self.status_update.emit(f"âš ï¸ Erro ao ativar navegador: {str(e)}")
            
        for tentativa in range(1, max_tentativas + 1):
            self.status_update.emit(f"ðŸ’¬ Tentativa {tentativa}/{max_tentativas} de comentar com '{username}'...")
            
            try:
                # Identificar o campo de comentÃ¡rio com estratÃ©gia mais agressiva
                seletores_campo_comentario = [
                    "//form[contains(@class, 'comment')]//textarea",
                    "//textarea[contains(@placeholder, 'coment')]",
                    "//textarea[contains(@aria-label, 'comment')]",
                    "//*[@role='textbox' and contains(@aria-label, 'coment')]",
                    "//*[@role='textbox']",  # Seletor mais genÃ©rico
                    "//*[@placeholder='Adicione um comentÃ¡rio...']",
                    "//*[@placeholder='Add a commentâ€¦']",
                    "//form//textarea",  # Qualquer textarea dentro de um form
                    "//section//textarea",  # Qualquer textarea dentro de section
                    "//textarea"  # Ãšltimo recurso: qualquer textarea na pÃ¡gina
                ]
                
                campo_comentario = None
                
                # Esperar explicitamente pelo campo de comentÃ¡rio
                try:
                    wait = WebDriverWait(driver, 10)
                    for seletor in seletores_campo_comentario:
                        try:
                            campo_comentario = wait.until(EC.element_to_be_clickable((By.XPATH, seletor)))
                            if campo_comentario.is_displayed():
                                self.status_update.emit(f"âœ… Campo de comentÃ¡rio encontrado com seletor: {seletor}")
                                break
                        except:
                            continue
                except:
                    pass
                
                # Se ainda nÃ£o encontrou, tentar abordagem tradicional
                if not campo_comentario:
                    for seletor in seletores_campo_comentario:
                        try:
                            campo_comentario = driver.find_element(By.XPATH, seletor)
                            if campo_comentario.is_displayed():
                                self.status_update.emit(f"âœ… Campo de comentÃ¡rio encontrado com seletor: {seletor}")
                                break
                        except:
                            continue
                
                # Se ainda nÃ£o encontrou, tentar rolagem em diferentes posiÃ§Ãµes
                if not campo_comentario:
                    self.status_update.emit(f"âš ï¸ Campo de comentÃ¡rio nÃ£o encontrado. Tentando rolagens diferentes...")
                    posicoes_rolagem = [100, 300, 500, 800, -100, -300]
                    
                    for posicao in posicoes_rolagem:
                        try:
                            driver.execute_script(f"window.scrollBy(0, {posicao});")
                            time.sleep(1)
                            
                            for seletor in seletores_campo_comentario:
                                try:
                                    campo_comentario = driver.find_element(By.XPATH, seletor)
                                    if campo_comentario.is_displayed():
                                        self.status_update.emit(f"âœ… Campo de comentÃ¡rio encontrado apÃ³s rolagem {posicao}px: {seletor}")
                                        break
                                except:
                                    continue
                            
                            if campo_comentario and campo_comentario.is_displayed():
                                break
                        except:
                            continue
                
                if not campo_comentario:
                    self.status_update.emit(f"âŒ Campo de comentÃ¡rio nÃ£o encontrado em tentativa {tentativa}")
                    if tentativa < max_tentativas:
                        time.sleep(3)
                        continue
                    else:
                        return False
                
                # EstratÃ©gia 1: Clique e digitaÃ§Ã£o direta com foco garantido
                try:
                    # IMPORTANTE: Para mÃºltiplos perfis, precisamos garantir o foco no elemento
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", campo_comentario)
                    time.sleep(0.5)
                    
                    # Usar JavaScript para destacar o campo visÃ­vel
                    driver.execute_script("""
                        arguments[0].style.border = '2px solid red'; 
                        arguments[0].style.backgroundColor = '#ffffcc';
                    """, campo_comentario)
                    time.sleep(0.5)
                    
                    # Limpar o campo usando JavaScript primeiro
                    driver.execute_script("arguments[0].value = '';", campo_comentario)
                    
                    # Clicar usando ActionChains para maior confiabilidade
                    actions = ActionChains(driver)
                    actions.move_to_element(campo_comentario).click().perform()
                    time.sleep(0.5)
                    
                    # Tentar digitar com diferentes mÃ©todos
                    campo_comentario.clear()
                    time.sleep(0.3)
                    
                    # MÃ©todo 1: Envio direto
                    campo_comentario.send_keys(texto_comentario)
                    time.sleep(0.5)
                    
                    # MÃ©todo 2: Digitar caractere por caractere
                    if not campo_comentario.get_attribute("value"):
                        for char in texto_comentario:
                            campo_comentario.send_keys(char)
                            time.sleep(0.05)
                    
                    time.sleep(0.5)
                    
                    # Tentar enviar comentÃ¡rio
                    try:
                        # MÃ©todo 1: Pressionar Enter usando diferentes abordagens
                        # Primeiro, verificar se o texto foi inserido corretamente
                        campo_valor = campo_comentario.get_attribute("value")
                        self.status_update.emit(f"ðŸ’¬ Texto inserido: '{campo_valor}'")
                        
                        # MÃ©todo 1A: Pressionar Enter diretamente
                        campo_comentario.send_keys(Keys.ENTER)
                        time.sleep(1)
                        
                        # MÃ©todo 1B: Usar ActionChains para Enter
                        if not self._verificar_comentario_enviado(driver, texto_comentario):
                            actions = ActionChains(driver)
                            actions.move_to_element(campo_comentario).click().send_keys(Keys.ENTER).perform()
                            time.sleep(1)
                        
                        # MÃ©todo 1C: Usar JavaScript para submeter o formulÃ¡rio
                        if not self._verificar_comentario_enviado(driver, texto_comentario):
                            try:
                                driver.execute_script("""
                                    var campo = arguments[0];
                                    var form = campo.form;
                                    if (form) form.submit();
                                """, campo_comentario)
                                time.sleep(1)
                            except:
                                pass
                            
                            # Verificar se o comentÃ¡rio foi enviado
                            if self._verificar_comentario_enviado(driver, texto_comentario):
                                self.status_update.emit(f"âœ… ComentÃ¡rio enviado com sucesso (mÃ©todo Enter)!")
                                # Fechar o navegador imediatamente
                                driver.quit()
                                if username in self.workers_ativos:
                                    del self.workers_ativos[username]
                                self.status_update.emit(f"ðŸšª Navegador de '{username}' fechado apÃ³s comentÃ¡rio bem-sucedido.")
                                # Finalizar a aÃ§Ã£o com sucesso
                                self._finalizar_acao_com_sucesso(driver, username, acoes_realizadas, "comentar")
                                return True
                    except:
                        pass
                    
                    # MÃ©todo 2: Procurar botÃ£o de enviar/publicar
                    try:
                        botoes_enviar = [
                            "//button[contains(@type, 'submit')]",
                            "//button[contains(text(), 'Publicar')]",
                            "//button[contains(text(), 'Post')]",
                            "//div[contains(text(), 'Publicar')]/parent::button",
                            "//div[contains(text(), 'Post')]/parent::button"
                        ]
                        
                        for seletor_botao in botoes_enviar:
                            try:
                                botao_publicar = driver.find_element(By.XPATH, seletor_botao)
                                if botao_publicar.is_displayed() and botao_publicar.is_enabled():
                                    botao_publicar.click()
                                    time.sleep(2)
                                    
                                    # Verificar se o comentÃ¡rio foi enviado
                                    if self._verificar_comentario_enviado(driver, texto_comentario):
                                        self.status_update.emit(f"âœ… ComentÃ¡rio enviado com sucesso (mÃ©todo botÃ£o)!")
                                        # Finalizar a aÃ§Ã£o com sucesso
                                        self._finalizar_acao_com_sucesso(driver, username, acoes_realizadas, "comentar")
                                        return True
                            except:
                                continue
                    except:
                        pass
{{ ... }}
                    ActionChains(driver).send_keys(Keys.ENTER).perform()
                    time.sleep(2)
                    
                    # Verificar se o comentÃ¡rio foi enviado
                    if self._verificar_comentario_enviado(driver, texto_comentario):
                        self.status_update.emit(f"âœ… ComentÃ¡rio enviado com sucesso (mÃ©todo Clipboard)!")
                        # Fechar o navegador imediatamente apÃ³s o comentÃ¡rio ser enviado com sucesso
                        try:
                            driver.quit()
                            if username in self.workers_ativos:
                                del self.workers_ativos[username]
                            self.status_update.emit(f"ðŸšª Navegador de '{username}' fechado apÃ³s comentÃ¡rio bem-sucedido.")
                        except Exception as e:
                            self.status_update.emit(f"âš ï¸ Erro ao fechar navegador: {str(e)}")
                        return self._atualizar_status_acao_concluida(driver, username, acoes_realizadas, "comentar")
                except:
                    pass
                
            except Exception as e:
{{ ... }}
            
            # Se nÃ£o conseguiu comentar, aguarda um pouco antes da prÃ³xima tentativa
            if not comentario_realizado:
                self.status_update.emit(f"âŒ›ï¸ Aguardando antes da prÃ³xima tentativa...")
                time.sleep(3)
        
        return False

    def _verificar_comentario_enviado(self, driver, texto_comentario):
        """Verifica se o comentÃ¡rio foi realmente enviado."""
        try:
            # Aguardar um momento para o comentÃ¡rio aparecer
            time.sleep(2)
            
            # Verificar 1: O campo de comentÃ¡rio deve estar vazio
            try:
                campos_comentario = driver.find_elements(By.XPATH, "//textarea[contains(@placeholder, 'coment')]")
                for campo in campos_comentario:
                    if campo.is_displayed() and campo.get_attribute("value") == "":
                        return True
            except:
                pass
            
            # Verificar 2: O comentÃ¡rio deve aparecer na lista de comentÃ¡rios
            try:
                comentarios = driver.find_elements(By.XPATH, "//ul/li/div[contains(@class, 'comment')]//span")
                for comentario in comentarios:
                    if texto_comentario in comentario.text:
                        return True
            except:
                pass
            
            # Verificar 3: Verificar mensagem de "ComentÃ¡rio publicado" ou similar
            try:
                mensagens = driver.find_elements(By.XPATH, "//*[contains(text(), 'Coment') or contains(text(), 'comment')]")
                for msg in mensagens:
                    if "publicado" in msg.text.lower() or "posted" in msg.text.lower():
                        return True
            except:
                pass
            
        except Exception as e:
            self.status_update.emit(f"âš ï¸ Erro ao fechar navegador: {str(e)}")
        return self._atualizar_status_acao_concluida(driver, username, acoes_realizadas, "comentar")
except:
    pass

def _verificar_comentario_enviado(self, driver, texto_comentario):
    """Verifica se o comentÃ¡rio foi realmente enviado."""
    try:
        # Aguardar um momento para o comentÃ¡rio aparecer
        time.sleep(2)
        
        # Verificar 1: O campo de comentÃ¡rio deve estar vazio
        try:
            campos_comentario = driver.find_elements(By.XPATH, "//textarea[contains(@placeholder, 'coment')]")
            for campo in campos_comentario:
                if campo.is_displayed() and campo.get_attribute("value") == "":
                    return True
        except:
            pass
        
        # Verificar 2: O comentÃ¡rio deve aparecer na lista de comentÃ¡rios
        try:
            comentarios = driver.find_elements(By.XPATH, "//ul/li/div[contains(@class, 'comment')]//span")
            for comentario in comentarios:
                if texto_comentario in comentario.text:
                    return True
        except:
            pass
        
        # Verificar 3: Verificar mensagem de "ComentÃ¡rio publicado" ou similar
        try:
            mensagens = driver.find_elements(By.XPATH, "//*[contains(text(), 'Coment') or contains(text(), 'comment')]")
            for msg in mensagens:
                if "publicado" in msg.text.lower() or "posted" in msg.text.lower():
                    return True
        except:
            pass
        
        return False
    except Exception as e:
        self.status_update.emit(f"âš ï¸ Erro ao verificar comentÃ¡rio: {str(e)}")
        return False

def _finalizar_acao_com_sucesso(self, driver, username, acoes_realizadas, tipo_acao):
    """Finaliza uma aÃ§Ã£o de comentÃ¡rio com sucesso e fecha o navegador imediatamente.
    
    Args:
        driver: WebDriver do Selenium
        username: Nome do perfil
        acoes_realizadas: Lista de aÃ§Ãµes jÃ¡ realizadas
        tipo_acao: Tipo da aÃ§Ã£o concluÃ­da
    
    Returns:
        bool: True se a aÃ§Ã£o foi finalizada com sucesso, False caso contrÃ¡rio
    """
    # Adicionar Ã  lista de aÃ§Ãµes realizadas para este perfil
    acoes_realizadas.append(tipo_acao)
    
    # Fechar o navegador imediatamente
    try:
        driver.quit()
        self.status_update.emit(f"ðŸšª Navegador de '{username}' fechado apÃ³s comentÃ¡rio bem-sucedido.")
    except Exception as e:
        self.status_update.emit(f"âš ï¸ Erro ao fechar navegador: {str(e)}")
    
    # Remover perfil dos workers ativos
    if username in self.workers_ativos:
        del self.workers_ativos[username]
    
    # Usar lock para garantir acesso thread-safe Ã  variÃ¡vel compartilhada
    with self.acoes_lock:
        self.acoes_concluidas += 1
        # Emitir sinal para atualizar a interface em tempo real
        self.progresso_atualizado.emit(self.acoes_concluidas, self.total_acoes)
        # Verificar se atingimos o nÃºmero total de aÃ§Ãµes
        if self.acoes_concluidas >= self.total_acoes:
            self.status_update.emit(f"âœ¨ Total de aÃ§Ãµes concluÃ­das! ({self.acoes_concluidas}/{self.total_acoes})")
            self._stop_flag = True  # Para o bot quando atingir o total de aÃ§Ãµes
    
    # Remover perfil da lista de perfis em execuÃ§Ã£o
    if username in self.perfis_em_execucao:
        self.perfis_em_execucao.remove(username)
    
    # Notificar conclusÃ£o da aÃ§Ã£o
    nome_amigavel = "comentÃ¡rio"
    self.acao_concluida.emit(username, tipo_acao, True, f"{nome_amigavel.capitalize()} realizado com sucesso")
    self.status_update.emit(f"âœ… {nome_amigavel.capitalize()} realizado com perfil '{username}' (Total: {self.acoes_concluidas}/{self.total_acoes})")
    
    return True

def _atualizar_status_acao_concluida(self, driver, username, acoes_realizadas, tipo_acao):
    """MÃ©todo legado - agora apenas chama _finalizar_acao_com_sucesso."""
    return self._finalizar_acao_com_sucesso(driver, username, acoes_realizadas, tipo_acao)
