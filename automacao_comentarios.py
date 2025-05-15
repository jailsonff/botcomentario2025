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
    Worker especializado para executar comentários automatizados em posts do Instagram usando perfis do Dolphin Anty.
    """
    # Sinais: perfil, ação, sucesso, mensagem
    acao_concluida = pyqtSignal(str, str, bool, str)
    progresso_atualizado = pyqtSignal(int, int)  # ações concluídas, total de ações
    status_update = pyqtSignal(str)
    automacao_concluida = pyqtSignal()

    def __init__(self, dolphin_manager, post_url, perfis, total_acoes, perfis_simultaneos, 
                 tempo_entre_acoes, texto_comentario="", parent=None, manter_navegador_aberto=False):
        super().__init__(parent)
        self.dolphin_manager = dolphin_manager
        self.post_url = post_url
        self.perfis = perfis  # Lista de nomes de usuário dos perfis
        self.total_acoes = total_acoes
        self.perfis_simultaneos = perfis_simultaneos
        self.tempo_entre_acoes = tempo_entre_acoes
        self.manter_navegador_aberto = manter_navegador_aberto
        
        # Dicionário para rastrear ações já contadas por perfil
        self.acoes_ja_contadas = {}
        # Lock para acesso ao dicionário de ações contadas
        self.acoes_contadas_lock = threading.Lock()
        
        # Tratar o texto_comentario como uma lista de comentários
        if texto_comentario:
            # Dividir o texto em linhas e filtrar linhas vazias
            self.lista_comentarios = [linha.strip() for linha in texto_comentario.split('\n') if linha.strip()]
        else:
            self.lista_comentarios = []
        self._stop_flag = False
        self.acoes_concluidas = 0
        self.workers_ativos = {}  # Armazena os drivers ativos por perfil

    def stop(self):
        """Para a execução da automação."""
        self._stop_flag = True
        self.workers_ativos.clear()

    def run(self):
        """Executa a automação de comentários nos perfis."""
        if not self.perfis or not self.post_url:
            self.status_update.emit("❌ Erro: URL do post ou lista de perfis vazia.")
            self.automacao_concluida.emit()
            return

        # Verifica se há comentários disponíveis
        if not self.lista_comentarios:
            self.status_update.emit("❌ Erro: Nenhum comentário definido.")
            self.automacao_concluida.emit()
            return

        # Verifica se o número de ações é maior que o número de perfis disponíveis
        if self.total_acoes > len(self.perfis):
            self.status_update.emit(f"⚠️ Aviso: O número de ações ({self.total_acoes}) é maior que o número de perfis disponíveis ({len(self.perfis)}). Alguns perfis serão usados mais de uma vez.")

        # Embaralha a lista de perfis para usar em ordem aleatória
        perfis_disponiveis = self.perfis.copy()
        random.shuffle(perfis_disponiveis)

        # Inicia o loop de automação
        self.acoes_concluidas = 0
        self.progresso_atualizado.emit(self.acoes_concluidas, self.total_acoes)
        
        # Criar um lock para acesso thread-safe à variável acoes_concluidas
        self.acoes_lock = threading.Lock()
        
        # Criar uma lista para controlar os perfis já usados
        self.perfis_em_execucao = []
        
        while self.acoes_concluidas < self.total_acoes and not self._stop_flag:
            # Verifica quantos workers estão ativos no momento
            workers_ativos_count = len(self.workers_ativos)
            
            # Mostrar informações sobre navegadores ativos
            self.status_update.emit(f"💻 Navegadores ativos: {workers_ativos_count}/{self.perfis_simultaneos}")
            
            # Se já temos o máximo de workers ativos, aguarda
            if workers_ativos_count >= self.perfis_simultaneos:
                time.sleep(1)
                continue
            
            # Verificar quantas ações já foram iniciadas (em execução + concluídas)
            acoes_iniciadas = self.acoes_concluidas + len(self.perfis_em_execucao)
            
            # Se já iniciamos todas as ações necessárias, aguarda a conclusão
            if acoes_iniciadas >= self.total_acoes:
                time.sleep(1)
                continue
            
            # Verificar quantos perfis precisamos iniciar para atingir o máximo de simultâneos
            perfis_para_iniciar = self.perfis_simultaneos - workers_ativos_count
            self.status_update.emit(f"💼 Tentando iniciar {perfis_para_iniciar} novos navegadores para atingir o limite de {self.perfis_simultaneos} simultâneos")
            
            # Selecionar próximos perfis disponíveis e iniciar todos de uma vez
            perfis_iniciados = 0
            for perfil in perfis_disponiveis:
                # Parar quando atingir o número de perfis necessários
                if perfis_iniciados >= perfis_para_iniciar:
                    break
                    
                # Pular perfis que já estão em execução
                if perfil in self.perfis_em_execucao:
                    continue
                    
                # Adicionar à lista de perfis em execução
                self.perfis_em_execucao.append(perfil)
                
                # Iniciar thread separada para este perfil para permitir execução simultânea
                self.status_update.emit(f"🔄 Iniciando perfil #{perfis_iniciados+1}/{perfis_para_iniciar}: {perfil} em thread separada")
                
                # Criar e iniciar uma thread para esse perfil
                perfil_thread = threading.Thread(target=self._executar_acao_perfil, args=(perfil,))
                perfil_thread.daemon = True  # Garantir que a thread termine quando o programa principal terminar
                perfil_thread.start()
                
                # Contar mais um perfil iniciado
                perfis_iniciados += 1
                
                # Curta pausa para evitar sobrecarga no sistema
                time.sleep(0.2)  # Reduzir o tempo de pausa para abrir navegadores mais rapidamente
                
            # Aguardar o tempo entre ações apenas se algum perfil foi iniciado
            if perfis_iniciados > 0:
                self.status_update.emit(f"⏳ {perfis_iniciados} navegadores iniciados. Aguardando {self.tempo_entre_acoes}s antes de continuar...")
                time.sleep(self.tempo_entre_acoes)
            else:
                # Se não encontrou perfil disponível, aguarda um pouco
                time.sleep(1)
        
        # Aguardar todos os workers concluírem
        while self.workers_ativos and not self._stop_flag:
            self.status_update.emit(f"⌛ Aguardando {len(self.workers_ativos)} workers concluírem...")
            time.sleep(2)
        
        # Emitir sinal de conclusão
        self.status_update.emit(f"✅ Automação concluída! {self.acoes_concluidas} comentários realizados.")
        self.automacao_concluida.emit()

    def _executar_acao_perfil(self, username):
        """Executa a ação para um perfil específico."""
        if self._stop_flag:
            if username in self.perfis_em_execucao:
                self.perfis_em_execucao.remove(username)
            return
        
        # Tentar obter um comentário aleatório
        if not self.lista_comentarios:
            self.status_update.emit(f"❌ Erro: Lista de comentários vazia para '{username}'.")
            if username in self.perfis_em_execucao:
                self.perfis_em_execucao.remove(username)
            return
        
        comentario = random.choice(self.lista_comentarios)
        
        self.status_update.emit(f"🔄 Iniciando navegador para '{username}'...")
        
        # Iniciar navegador e abrir post
        success, message = self.dolphin_manager.launch_profile_instagram(username, go_to_instagram_home=False)
        
        if not success:
            self.status_update.emit(f"❌ Erro ao abrir navegador para '{username}': {message}")
            if username in self.perfis_em_execucao:
                self.perfis_em_execucao.remove(username)
            return
        
        driver = self.dolphin_manager.get_profile_driver(username)
        if not driver:
            self.status_update.emit(f"❌ Erro: Driver não encontrado para '{username}'.")
            if username in self.perfis_em_execucao:
                self.perfis_em_execucao.remove(username)
            return
        
        # Adicionar à lista de workers ativos
        self.workers_ativos[username] = driver
        
        # Navegar para o post
        try:
            self.status_update.emit(f"🌐 Navegando para URL do post ({username})...")
            driver.get(self.post_url)
            
            # Aguardar um tempo mínimo para carregamento inicial
            time.sleep(2)
            
            # Tentar comentar após carregar a página para qualquer perfil
            self.status_update.emit(f"⚡ Página carregada. Iniciando comentário para '{username}'...")
            
            # Aguardar carregamento completo da página
            try:
                self._aguardar_carregamento_pagina(driver, username)
                self.status_update.emit(f"✅ Página carregada com sucesso para '{username}'")
            except Exception as e:
                self.status_update.emit(f"⚠️ Erro ao aguardar carregamento, mas continuando: {str(e)}")
            
            # Obter um comentário aleatório da lista
            if self.lista_comentarios:
                comentario = random.choice(self.lista_comentarios)
                
                # Lista para controlar ações realizadas
                acoes_realizadas = []
                
                # Usar o novo método de comentário fornecido pelo usuário
                try:
                    self.status_update.emit(f"💬 Tentando comentar com o texto: '{comentario}'")
                    if self._comentar_post(driver, username, comentario, acoes_realizadas):
                        self.status_update.emit(f"✅ Comentário realizado com sucesso para '{username}'!")
                        success = True
                    else:
                        self.status_update.emit(f"❌ Falha ao comentar no post de '{username}'")
                        success = False
                except Exception as e:
                    self.status_update.emit(f"❌ Erro ao comentar: {str(e)}")
                    success = False
            else:
                self.status_update.emit("❌ Não há comentários disponíveis para postar!")
                success = False
                
                # Atualizar contadores
                if success:
                    self.acoes_concluidas += 1
                    self.progresso_atualizado.emit(self.acoes_concluidas, self.total_acoes)
                
                # Limpar
                if username in self.perfis_em_execucao:
                    self.perfis_em_execucao.remove(username)
                if username in self.workers_ativos:
                    del self.workers_ativos[username]
                if not self.manter_navegador_aberto:
                    driver.quit()
                return
            
            # Para outros perfis, continuar com o fluxo normal
            # Aguardar carregamento da página
            self._aguardar_carregamento_pagina(driver, username)
            
            # Aguardar um tempo para garantir que a página esteja totalmente carregada
            time.sleep(3)
            
            # IMPORTANTE: Para perfis múltiplos, precisamos dar foco para este navegador
            try:
                driver.execute_script("window.focus();")
                time.sleep(1)
                # Mover mouse para o centro da tela para ativação
                action = ActionChains(driver)
                action.move_by_offset(0, 0).click().perform()
                self.status_update.emit(f"👁️ Dando foco ao navegador de '{username}'...")
                time.sleep(0.5)
            except Exception as e:
                self.status_update.emit(f"⚠️ Erro ao ativar navegador: {str(e)}")
            
            # Verificar se está logado
            if not self.dolphin_manager.is_logged_in(driver):
                self.status_update.emit(f"🔑 Perfil '{username}' não está logado. Tentando login automático...")
                login_success, login_message = self.dolphin_manager.attempt_login_instagram(
                    driver, username, "sua_senha_aqui"
                )
                
                if not login_success:
                    self.status_update.emit(f"❌ Falha no login para '{username}': {login_message}")
                    driver.quit()
                    if username in self.workers_ativos:
                        del self.workers_ativos[username]
                    if username in self.perfis_em_execucao:
                        self.perfis_em_execucao.remove(username)
                    return
            
            # Continuar com a ação principal: comentar
            self.status_update.emit(f"📝 Iniciando comentário para '{username}'...")
            self._comentar_direto(driver, username, comentario)
            
        except Exception as e:
            self.status_update.emit(f"❌ Erro durante execução para '{username}': {str(e)}")
            if username in self.workers_ativos:
                del self.workers_ativos[username]
            if username in self.perfis_em_execucao:
                self.perfis_em_execucao.remove(username)
            if not self.manter_navegador_aberto:
                try:
                    driver.quit()
                except:
                    pass

    def _aguardar_carregamento_pagina(self, driver, username):
        """Aguarda o carregamento da página."""
        try:
            self.status_update.emit(f"⏳ Aguardando carregamento da página para '{username}'...")
            wait = WebDriverWait(driver, 30)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "article")))
                
            # Reduzido o tempo de espera após carregar o artigo para agilizar o comentário
            time.sleep(2)  # Tempo suficiente para garantir que podemos interagir com a página
                
            # Procurar explicitamente pelo campo de comentário para garantir que está carregado
            seletores_campo_comentario = [
                "//form[contains(@class, 'comment')]//textarea",
                "//textarea[contains(@placeholder, 'coment')]",
                "//textarea[contains(@aria-label, 'comment')]",
                "//*[@role='textbox' and contains(@aria-label, 'coment')]",
                "//*[@placeholder='Adicione um comentário...']",
                "//*[@placeholder='Add a comment…']"
            ]
                
            for seletor in seletores_campo_comentario:
                try:
                    wait.until(EC.presence_of_element_located((By.XPATH, seletor)))
                    self.status_update.emit(f"✅ Campo de comentário encontrado e pronto para '{username}'")
                    return  # Encontrou o campo, podemos continuar
                except:
                    continue
                
            # Se não encontrou o campo, tentar rolar a página
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            time.sleep(1)
        except Exception as e:
            self.status_update.emit(f"⚠️ Erro ao aguardar carregamento: {str(e)}")

    def _capturar_screenshot(self, driver, username, descricao):
        """Função vazia - screenshots desativadas"""
        # Screenshots desativadas a pedido do usuário
        pass
    
    def _atualizar_status_acao_concluida(self, driver, username, acoes_realizadas, tipo_acao):
        """Atualiza o status após a conclusão de uma ação - NÃO incrementa o contador"""
        try:
            # NOTA: Não incrementamos o contador aqui para evitar contagem duplicada
            # O contador será incrementado apenas uma vez no método final
            
            # Adicionar ação realizada se ainda não estiver na lista
            if tipo_acao not in acoes_realizadas:
                acoes_realizadas.append(tipo_acao)
            
            # Emitir sinal de ação concluída
            self.acao_concluida.emit(username, tipo_acao, True, "Ação concluída com sucesso")
            return True
        except Exception as e:
            self.status_update.emit(f"⚠️ Erro ao atualizar status: {str(e)}")
            return False
            
    def _comentar_post(self, driver, username, texto_comentario, acoes_realizadas):
        """Tenta adicionar um comentário ao post."""
        self.status_update.emit(f"💬 Tentando comentar no post com perfil '{username}'...")
        comentario_realizado = False
        max_tentativas = 5
        tentativa = 0
        
        # Substituir quebras de linha no texto do comentário
        texto = texto_comentario.replace('\n', ' ')
        
        # Copiar para a área de transferência para uso posterior
        pyperclip.copy(texto)
        
        while tentativa < max_tentativas and not comentario_realizado and not self._stop_flag:
            tentativa += 1
            self.status_update.emit(f"🔄 Tentativa #{tentativa} de comentar no post...")
            
            # Capturar screenshot para debug
            self._capturar_screenshot(driver, username, f"comment_attempt_{tentativa}")
            
            try:
                # Seletores para o campo de comentário
                seletores_comentario = [
                    "//textarea[@placeholder='Adicione um comentário...']",
                    "//textarea[@aria-label='Adicione um comentário...']",
                    "//form//textarea",
                    "//div[@role='dialog']//textarea",
                    "//*[contains(@placeholder, 'coment') or contains(@placeholder, 'Coment')]"
                ]
                
                # Tentar cada seletor
                campo_comentario = None
                for seletor in seletores_comentario:
                    elementos = driver.find_elements(By.XPATH, seletor)
                    for elem in elementos:
                        if elem.is_displayed():
                            campo_comentario = elem
                            break
                    if campo_comentario:
                        break
                
                if not campo_comentario:
                    self.status_update.emit(f"⚠️ Campo de comentário não encontrado, tentando novamente...")
                    # Pressionar Tab algumas vezes para tentar focar o campo de comentário
                    actions = ActionChains(driver)
                    for _ in range(3):
                        actions.send_keys(Keys.TAB).perform()
                        time.sleep(1)
                        
                        # Tentar novamente os seletores após pressionar Tab
                        for seletor in seletores_comentario:
                            elementos = driver.find_elements(By.XPATH, seletor)
                            for elem in elementos:
                                if elem.is_displayed():
                                    campo_comentario = elem
                                    break
                            if campo_comentario:
                                break
                                
                        if campo_comentario:
                            break
                    
                    if not campo_comentario:
                        # Última tentativa: procurar qualquer textarea visível
                        textareas = driver.find_elements(By.TAG_NAME, "textarea")
                        for textarea in textareas:
                            if textarea.is_displayed():
                                campo_comentario = textarea
                                break
                
                # Se encontrou o campo de comentário, tenta inserir o texto
                if campo_comentario:
                    # Clicar no campo para focar
                    try:
                        campo_comentario.click()
                        time.sleep(2)
                    except Exception:
                        # Se não puder clicar diretamente, tente com JS
                        driver.execute_script("arguments[0].click();", campo_comentario)
                        time.sleep(2)
                    
                    # SUPER FOCUS NO CAMPO DE COMENTÁRIO
                    self.status_update.emit(f"💡 FOCO INTENSO no campo de comentário")
                    # Destacar visualmente o campo para ver no navegador
                    driver.execute_script(
                        "arguments[0].style.border = '5px solid red'; "
                        "arguments[0].style.backgroundColor = 'yellow'; "
                        "arguments[0].scrollIntoView({block: 'center'});", 
                        campo_comentario
                    )
                    time.sleep(1)
                    
                    # Tirar screenshot para debug
                    self._capturar_screenshot(driver, username, "campo_comentario_destacado")
                    
                    # TENTATIVA MANUAL DE LIMPAR O CAMPO
                    self.status_update.emit(f"🗑 Limpando campo AGRESSIVAMENTE...")
                    try:
                        # Método 1: Clear padrão
                        campo_comentario.clear()
                        
                        # Método 2: Seleção total + delete
                        actions = ActionChains(driver)
                        actions.click(campo_comentario).key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).send_keys(Keys.DELETE).perform()
                        
                        # Método 3: JavaScript
                        driver.execute_script("arguments[0].value = '';", campo_comentario)
                        time.sleep(1)
                    except Exception as e:
                        self.status_update.emit(f"Erro ao limpar: {str(e)}")
                    
                    # SUPER DIGITAÇÃO DO TEXTO
                    self.status_update.emit(f"⌨️ DIGITANDO COMENTÁRIO: '{texto}'")
                    
                    texto_digitado = False
                    
                    # Método 1: Digitação direta
                    try:
                        campo_comentario.send_keys(texto)
                        self.status_update.emit(f"✅ Texto enviado via send_keys!")
                        texto_digitado = True
                    except Exception as e1:
                        self.status_update.emit(f"Erro no send_keys: {str(e1)}")
                        
                        # Método 2: Via JavaScript
                        try:
                            driver.execute_script("arguments[0].value = arguments[1];", campo_comentario, texto)
                            driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", campo_comentario)
                            time.sleep(0.5)
                            self.status_update.emit(f"✅ Texto definido via JavaScript!")
                            texto_digitado = True
                        except Exception as e2:
                            self.status_update.emit(f"Erro no JavaScript: {str(e2)}")
                            
                            # Método 3: Caractere por caractere
                            try:
                                for char in texto:
                                    campo_comentario.send_keys(char)
                                    time.sleep(0.05)
                                self.status_update.emit(f"✅ Texto digitado caractere por caractere!")
                                texto_digitado = True
                            except Exception as e3:
                                self.status_update.emit(f"Erro na digitação caractere por caractere: {str(e3)}")
                                
                                # Método 4: Via clipboard
                                try:
                                    # Garantir que o texto está na área de transferência
                                    pyperclip.copy(texto)
                                    # Clicar no campo e colar
                                    actions = ActionChains(driver)
                                    actions.click(campo_comentario).key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
                                    time.sleep(0.5)
                                    self.status_update.emit(f"✅ Texto colado via clipboard!")
                                    texto_digitado = True
                                except Exception as e4:
                                    self.status_update.emit(f"TODOS os métodos de digitação falharam!")
                                    continue  # Tentar próxima iteração
                    
                    # Verificar valor do campo
                    try:
                        valor_atual = campo_comentario.get_attribute("value")
                        self.status_update.emit(f"Valor atual do campo: '{valor_atual}'")
                        if not valor_atual:
                            self.status_update.emit(f"⚠️ Campo ainda está vazio! Tentando outros métodos...")
                        else:
                            self.status_update.emit(f"✅ Campo contém texto! Pronto para enviar.")
                    except Exception:
                        pass
                    
                    # Aguardar um momento para garantir que o texto foi inserido
                    time.sleep(2)
                    
                    # SUPER DETECTOR DE BOTÃO PUBLICAR
                    self.status_update.emit(f"🔍 Iniciando detecção intensiva do botão Publicar...")
                    
                    # Número máximo de tentativas para encontrar o botão
                    max_tentativas_botao = 10
                    tentativa_botao = 0
                    botao_publicar_encontrado = False
                    botao_publicado = False
                    
                    # Capturar screenshot para análise
                    self._capturar_screenshot(driver, username, "before_publish_button_search")
                    
                    while tentativa_botao < max_tentativas_botao and not botao_publicado and not self._stop_flag:
                        tentativa_botao += 1
                        self.status_update.emit(f"🔍 Tentativa #{tentativa_botao} de encontrar botão publicar...")
                        
                        # Seletores específicos fornecidos pelo usuário (prioridade máxima)
                        seletores_publicar = [
                            # Seletores de div que contém o texto "Postar"
                            "//div[@role='button'][text()='Postar']",
                            "//div[@role='button'][contains(text(), 'Postar')]",
                            "//div[@role='button'][@tabindex='0'][contains(text(), 'Postar')]",
                            "//div[contains(@class, 'x1i10hfl')][contains(@role, 'button')][contains(text(), 'Postar')]",
                            
                            # XPaths exatos fornecidos pelo usuário
                            "/html/body/div[9]/div[1]/div/div[3]/div/div/div/div/div[2]/div/article/div/div[2]/div/div/div[2]/section[3]/div/form/div/div[2]/div",
                            "/html/body/div[9]/div[1]/div/div[3]/div/div/div/div/div[2]/div/article/div/div[2]/div/div/div[2]/section[3]/div/form/div",
                            
                            # Variantes dos XPaths (para adaptar a diferentes versões)
                            "//div/article/div/div[2]/div/div/div[2]/section[3]/div/form/div/div[2]/div",
                            "//article//section[3]/div/form/div/div[2]/div",
                            "//form/div/div[2]/div[contains(text(), 'Postar')]",
                            
                            # Busca por elementos próximos ao textarea
                            "//textarea[@placeholder='Adicione um comentário...']/following::div[contains(text(), 'Postar')]",
                            "//textarea[@aria-label='Adicione um comentário...']/following::div[contains(text(), 'Postar')]",
                            "//textarea[contains(@placeholder, 'coment')]/parent::*/following-sibling::div",
                            
                            # Busca elementos com as classes específicas do botão Postar
                            "//div[contains(@class, 'x1i10hfl') and contains(@class, 'xjqpnuy') and contains(@class, 'xa49m3k')][contains(text(), 'Postar')]",
                            
                            # Botões baseados em texto (backup)
                            "//button[text()='Publicar']",
                            "//button[contains(text(), 'Publicar')]",
                            "//button[text()='Postar']",
                            "//button[contains(text(), 'Postar')]",
                            "//button[text()='Post']",
                            "//button[contains(text(), 'Post')]",
                            "//button[contains(text(), 'Comment')]",
                            "//button[text()='Enviar']",
                            "//button[contains(text(), 'Enviar')]"
                        ]
                        
                        # Buscar botões
                        for seletor in seletores_publicar:
                            # Se já encontrou o botão, não continua a busca
                            if botao_publicado:
                                break
                                
                            try:
                                botoes = driver.find_elements(By.XPATH, seletor)
                                self.status_update.emit(f"Encontrados {len(botoes)} botões com seletor: {seletor}")
                                
                                # Tentar clicar em cada botão visível
                                for botao in botoes:
                                    try:
                                        if botao.is_displayed() and botao.is_enabled():
                                            self.status_update.emit(f"👁 Botão potencial encontrado! Tentando clicar...")
                                            
                                            # Capturar screenshot antes do clique
                                            self._capturar_screenshot(driver, username, f"button_attempt_{tentativa_botao}")
                                            
                                            # NÃO rolar para o botão - pois pode dificultar a localização
                                            # Manter a página na posição atual sem rolagem
                                            
                                            # Mostrar informações sobre o botão
                                            try:
                                                botao_texto = botao.text
                                                botao_classe = botao.get_attribute("class")
                                                self.status_update.emit(f"Botão texto: '{botao_texto}', classe: '{botao_classe}'")
                                            except Exception:
                                                pass
                                            
                                            # Tentar múltiplos métodos de clique
                                            clique_ok = False
                                            
                                            # Método 1: Clique direto
                                            try:
                                                botao.click()
                                                self.status_update.emit(f"✅ Clique direto executado!")
                                                clique_ok = True
                                            except Exception as e1:
                                                self.status_update.emit(f"Erro no clique direto: {str(e1)}")
                                                
                                                # Método 2: JavaScript
                                                try:
                                                    driver.execute_script("arguments[0].click();", botao)
                                                    self.status_update.emit(f"✅ Clique via JavaScript executado!")
                                                    clique_ok = True
                                                except Exception as e2:
                                                    self.status_update.emit(f"Erro no clique JavaScript: {str(e2)}")
                                                    
                                                    # Método 3: ActionChains
                                                    try:
                                                        actions = ActionChains(driver)
                                                        actions.move_to_element(botao).click().perform()
                                                        self.status_update.emit(f"✅ Clique via ActionChains executado!")
                                                        clique_ok = True
                                                    except Exception as e3:
                                                        self.status_update.emit(f"Erro no ActionChains: {str(e3)}")
                                                        
                                                        # Método 4: TouchActions (para mobile)
                                                        try:
                                                            driver.execute_script(
                                                                "var evt = document.createEvent('MouseEvents');"  
                                                                "evt.initMouseEvent('click',true,true,window,0,0,0,0,0,false,false,false,false,0,null);"  
                                                                "arguments[0].dispatchEvent(evt);", botao)  
                                                            self.status_update.emit(f"✅ Clique via MouseEvent executado!")
                                                            clique_ok = True
                                                        except Exception as e4:
                                                            self.status_update.emit(f"Todos os métodos de clique falharam")
                                            
                                            if clique_ok:
                                                self.status_update.emit(f"✅ Tentativa de clique realizada, aguardando...")
                                                time.sleep(4)  # Aguardar para ver se o comentário foi publicado
                                                
                                                # Verificar se o comentário foi publicado
                                                try:
                                                    # Capturar screenshot após o clique
                                                    self._capturar_screenshot(driver, username, f"after_click_{tentativa_botao}")
                                                    
                                                    # Verificar se o campo está vazio agora (indica que o comentário foi enviado)
                                                    campo_vazio = False
                                                    try:
                                                        novo_campo = driver.find_element(By.XPATH, "//textarea[@placeholder='Adicione um comentário...']")
                                                        if not novo_campo.get_attribute("value"):
                                                            campo_vazio = True
                                                            self.status_update.emit(f"✅ Campo está vazio após o clique!")
                                                    except Exception:
                                                        pass
                                                    
                                                    # Procurar pelo comentário na lista de comentários
                                                    try:
                                                        texto_curto = texto[:15] if len(texto) > 15 else texto
                                                        comentarios = driver.find_elements(By.XPATH, f"//div[contains(text(), '{texto_curto}')]")
                                                        if comentarios and any(elem.is_displayed() for elem in comentarios):
                                                            self.status_update.emit(f"✅ Comentário encontrado na página!")
                                                            botao_publicado = True
                                                        else:
                                                            # Se o campo está vazio mas não encontramos o comentário ainda
                                                            if campo_vazio:
                                                                self.status_update.emit(f"✅ Campo vazio mas comentário não detectado ainda")
                                                                # Esperamos que foi postado
                                                                botao_publicado = True
                                                    except Exception as e:
                                                        self.status_update.emit(f"Erro ao verificar comentário: {str(e)}")
                                                    
                                                except Exception:
                                                    pass
                                                
                                                if botao_publicado:
                                                    self.status_update.emit(f"🎉 COMENTÁRIO PUBLICADO COM SUCESSO!")
                                                    # NÃO atualizar o contador aqui, será feito apenas uma vez no final do método
                                                    # Apenas marcamos a operação como bem-sucedida
                                                    acoes_realizadas.append("comentar")
                                                    break
                                    except Exception:
                                        continue
                                    
                                    if botao_publicado:
                                        break
                            except Exception as e:
                                self.status_update.emit(f"Erro ao avaliar seletor: {str(e)}")
                                continue
                        
                        # Se não publicou ainda, tenta métodos alternativos
                        if not botao_publicado:
                            self.status_update.emit(f"🔄 Tentando métodos alternativos... (tentativa {tentativa_botao})")
                            
                            # 1. Tenta pressionar Enter no campo novamente
                            try:
                                campo_comentario.click()
                                time.sleep(1)
                                campo_comentario.send_keys(Keys.RETURN)
                                self.status_update.emit(f"Enter pressionado novamente")
                                time.sleep(3)  # Aguardar para ver se funcionou
                                
                                # Verificar se campo está vazio (possível sucesso)
                                try:
                                    if not campo_comentario.get_attribute("value"):
                                        self.status_update.emit(f"✅ Campo vazio após pressionar Enter!")
                                        botao_publicado = True
                                        break
                                except Exception:
                                    pass
                            except Exception:
                                pass
                            
                            # 2. Tenta Tab + Enter
                            if not botao_publicado and tentativa_botao % 2 == 0:
                                try:
                                    actions = ActionChains(driver)
                                    actions.send_keys(Keys.TAB).perform()
                                    time.sleep(1)
                                    actions.send_keys(Keys.RETURN).perform()
                                    self.status_update.emit(f"Tab + Enter executado")
                                    time.sleep(3)  # Aguardar para ver se funcionou
                                except Exception:
                                    pass
                            
                            # 3. Tenta encontrar botões azuis (comuns no Instagram)
                            if not botao_publicado and tentativa_botao % 3 == 0:
                                try:
                                    # Buscar todos os elementos que podem ser botões azuis
                                    elementos_azuis = driver.find_elements(By.XPATH, "//button[contains(@style, 'color: rgb(0, 149, 246)') or contains(@style, 'background: rgb(0, 149, 246)')]")
                                    for elem in elementos_azuis:
                                        if elem.is_displayed():
                                            self.status_update.emit(f"Encontrado possível botão azul, tentando clicar...")
                                            try:
                                                elem.click()
                                                time.sleep(3)  # Aguardar para ver se funcionou
                                            except Exception:
                                                try:
                                                    driver.execute_script("arguments[0].click();", elem)
                                                    time.sleep(3)  # Aguardar para ver se funcionou
                                                except Exception:
                                                    pass
                                except Exception:
                                    pass
                            
                            # Aguardar um pouco antes da próxima tentativa e recarregar os elementos
                            time.sleep(2)
                            
                            # Se estamos na última tentativa, capture uma screenshot final
                            if tentativa_botao == max_tentativas_botao - 1:
                                self._capturar_screenshot(driver, username, "final_publish_attempt")
                    
                    # Se após todas as tentativas não conseguiu publicar, continuamos tentando na próxima iteração
                    if not botao_publicado:
                        self.status_update.emit(f"⚠️ Não conseguiu clicar no botão de publicar. Continuando...")
                        # Não desistimos, continuamos para a próxima tentativa do loop principal
                        continue
                    
                    # Aguardar o processamento do comentário
                    time.sleep(5)
                    
                    # Verificar se o comentário foi publicado
                    try:
                        # Procurar por elementos que indiquem que o comentário foi publicado
                        comentarios = driver.find_elements(By.XPATH, f"//div[contains(text(), '{texto[:20]}')]")
                        campo_vazio = driver.find_elements(By.XPATH, "//textarea[not(text()) or text()='']")
                        
                        if comentarios or campo_vazio:
                            comentario_realizado = True
                            self.status_update.emit(f"✅ Comentário publicado com sucesso!")
                            self._capturar_screenshot(driver, username, "after_successful_comment")
                            acoes_realizadas.append("comentar")
                            
                            # Fechar apenas este navegador e continuar com outras ações
                            self.status_update.emit(f"🚫 Fechando navegador de '{username}' após comentar com sucesso...")
                            
                            # Garantir que incrementamos o contador apenas UMA vez por perfil
                            with self.acoes_contadas_lock:
                                # Verificar se este perfil já foi contado
                                if username not in self.acoes_ja_contadas:
                                    # Marca este perfil como já contado
                                    self.acoes_ja_contadas[username] = True
                                    
                                    # Incrementa o contador com lock para thread-safety
                                    with self.acoes_lock:
                                        self.acoes_concluidas += 1
                                        self.progresso_atualizado.emit(self.acoes_concluidas, self.total_acoes)
                                    
                                    # Log de controle
                                    self.status_update.emit(f"📊 Contador atualizado: {self.acoes_concluidas}/{self.total_acoes} ações concluídas.")
                                
                            # Verificar se atingimos o total de ações
                            all_completed = False
                            with self.acoes_lock:
                                if self.acoes_concluidas >= self.total_acoes:
                                    all_completed = True
                            
                            # Limpar recursos e fechar navegador
                            if username in self.perfis_em_execucao:
                                self.perfis_em_execucao.remove(username)
                            if username in self.workers_ativos:
                                del self.workers_ativos[username]
                            
                            # Fechar o navegador
                            try:
                                driver.quit()
                                self.status_update.emit(f"✅ Navegador de '{username}' fechado após comentar. Ações: {self.acoes_concluidas}/{self.total_acoes}")
                            except Exception as e:
                                self.status_update.emit(f"⚠️ Erro ao fechar navegador: {str(e)}")
                                
                            # Se todas as ações foram concluídas, parar completamente
                            if all_completed:
                                self._stop_flag = True
                                self.status_update.emit(f"🎉 META ATINGIDA! Todas as {self.total_acoes} ações foram concluídas com sucesso!")
                                self.automacao_concluida.emit()
                            
                            return True
                    except Exception:
                        pass
            except Exception as e:
                self.status_update.emit(f"⚠️ Erro ao tentar comentar: {str(e)}")
            
            # Se não conseguiu comentar, aguarda um pouco antes da próxima tentativa
            if not comentario_realizado:
                self.status_update.emit(f"⌛️ Aguardando antes da próxima tentativa...")
                time.sleep(3)
        
        if not comentario_realizado:
            self.status_update.emit(f"⚠️ Não foi possível comentar após {max_tentativas} tentativas.")
            return False
    
    def _comentar_direto(self, driver, username, texto_comentario):
        # Função simplificada para comentar diretamente, substituindo _comentar_post.
        try:
            # Dar foco ao navegador antes de interagir
            driver.switch_to.window(driver.current_window_handle)
            driver.execute_script("window.focus();");
            time.sleep(0.5)
            
            # Procurar o campo de comentário com diferentes seletores (expandidos para garantir que encontre)
            seletores = [
                # Seletores diretos mais específicos
                "//textarea[contains(@placeholder, 'coment')]",
                "//textarea[contains(@aria-label, 'comment')]",
                "//textarea[contains(@aria-label, 'coment')]",
                "//textarea[@aria-label='Add a comment…']",
                "//textarea[@aria-label='Adicione um comentário...']",
                "//*[@role='textbox' and contains(@aria-label, 'comment')]",
                "//*[@role='textbox' and contains(@aria-label, 'coment')]",
                "//*[@role='textbox']",
                "//*[@placeholder='Adicione um comentário...']",
                "//*[@placeholder='Add a comment…']",
                
                # Caminhos de navegação contextual
                "//span[text()='Add a comment…']/parent::*/parent::*//*[@role='textbox']",
                "//span[text()='Adicione um comentário...']/parent::*/parent::*//*[@role='textbox']",
                "//span[contains(text(), 'comment')]/ancestor::div[3]//textarea",
                "//span[contains(text(), 'coment')]/ancestor::div[3]//textarea",
                
                # Caminhos XPath completos no Instagram (podem mudar, mas vale tentar)
                "//section/div/div[2]/div/div/div/div[1]/div/div[2]/div/div/div/div[2]/div/div/div[4]/div/div/div/div/div[2]/div/div/div/div/div/div/textarea",
                "//section/div/div/div/div/div/div[1]/div/div[2]/div/div/div/div[2]/div/div/div[2]/div/div/div/div/div[2]/div/div/div/div/div/div/textarea",
                
                # Últimos recursos genéricos
                "//form//textarea",
                "//section//textarea",
                "//article//textarea",
                "//textarea"
            ]
            
            campo = None
            for seletor in seletores:
                try:
                    campo = driver.find_element(By.XPATH, seletor)
                    if campo.is_displayed():
                        self.status_update.emit(f"✅ Campo de comentário encontrado com seletor: {seletor}")
                        break
                except:
                    continue
            
            if not campo:
                # Tentar rolagem para encontrar o campo
                posicoes_rolagem = [100, 300, 500]
                for pos in posicoes_rolagem:
                    driver.execute_script(f"window.scrollBy(0, {pos});")
                    time.sleep(1)
                    for seletor in seletores:
                        try:
                            campo = driver.find_element(By.XPATH, seletor)
                            if campo.is_displayed():
                                self.status_update.emit(f"✅ Campo encontrado após rolagem: {seletor}")
                                break
                        except:
                            continue
                    if campo and campo.is_displayed():
                        break
            
            # Se não encontrou o campo, relatório de falha
            if not campo:
                self.status_update.emit(f"❌ Campo de comentário não encontrado para '{username}'")
                return False
            
            # ESTRATÉGIA MAIS AGRESSIVA DE DIGITAÇÃO
            # =======================================
            self.status_update.emit(f"💬 Tentando digitar comentário: '{texto_comentario}'")
            
            # 1. Dar foco garantido usando JavaScript e cliques múltiplos
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", campo)
            driver.execute_script("arguments[0].style.border = '2px solid red';arguments[0].style.backgroundColor = '#ffffcc';", campo)
            time.sleep(0.5)
            
            # 2. Tentar múltiplos cliques para garantir foco
            actions = ActionChains(driver)
            actions.move_to_element(campo).click().perform()
            time.sleep(0.3)
            
            # 3. Garantir que o campo está limpo de várias maneiras
            campo.clear()  # Método padrão
            actions.double_click(campo).key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).send_keys(Keys.DELETE).perform()
            driver.execute_script("arguments[0].value = '';", campo)  # Limpar via JavaScript
            time.sleep(0.5)
            
            # 4. Digitar de várias maneiras
            # 4.1 Tentativa 1: Direta
            campo.send_keys(texto_comentario)
            time.sleep(0.5)
            
            # 4.2 Tentativa 2: Usando JavaScript se necessário
            if not campo.get_attribute("value"):
                self.status_update.emit("⚠️ Tentando digitar via JavaScript...")
                driver.execute_script(f"arguments[0].value = '{texto_comentario}';", campo)
                driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", campo)
                time.sleep(0.5)
            
            # 4.3 Tentativa 3: Caractere por caractere
            if not campo.get_attribute("value"):
                self.status_update.emit("⚠️ Tentando digitar caractere por caractere...")
                for char in texto_comentario:
                    campo.send_keys(char)
                    time.sleep(0.05)
            
            # Verificar se digitou
            if not campo.get_attribute("value"):
                self.status_update.emit("❌ Falha em digitar o comentário!")
                # Tentar uma última abordagem - clipboard
                pyperclip.copy(texto_comentario)
                actions.click(campo).key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
                time.sleep(0.5)
            
            # 5. Enviar de múltiplas maneiras (tentativas agressivas)
            # 5.1 Método 1: Pressionar Enter diretamente
            self.status_update.emit("🔄 Enviando comentário com Enter...")
            campo.send_keys(Keys.ENTER)
            time.sleep(2)
            
            # Verificar se enviou
            if not campo.get_attribute("value"):
                self.status_update.emit(f"✅ Comentário enviado com sucesso para '{username}'!")
                with self.acoes_lock:
                    self.acoes_concluidas += 1
                    self.progresso_atualizado.emit(self.acoes_concluidas, self.total_acoes)
                
                # Limpar recursos
                if username in self.perfis_em_execucao:
                    self.perfis_em_execucao.remove(username)
                if username in self.workers_ativos:
                    del self.workers_ativos[username]
                if not self.manter_navegador_aberto:
                    driver.quit()
                return True
            
            # 5.2 Método 2: Procurar e clicar em botões com seletores expandidos
            self.status_update.emit("🔄 Tentando encontrar botão de enviar...")
            seletores_botao = [
                # Botões com texto
                "//button[contains(text(), 'Publicar')]",
                "//button[contains(text(), 'Post')]",
                "//button[contains(text(), 'Comentar')]",
                "//button[contains(text(), 'Comment')]",
                "//button[contains(text(), 'Enviar')]",
                "//button[contains(text(), 'Send')]",
                
                # Botões de formulário
                "//form//button[@type='submit']",
                "//form//button",
                
                # Botões próximos ao campo
                "//textarea/following::button[1]",
                "//textarea/../..//button",
                "//textarea/ancestor::form//button",
                
                # Botões com indicadores visuais
                "//button[contains(@class, 'submit')]",
                "//button[contains(@class, 'primary')]",
                "//button[not(@disabled)]"
            ]
            
            for seletor in seletores_botao:
                try:
                    botoes = driver.find_elements(By.XPATH, seletor)
                    for botao in botoes:
                        if botao.is_displayed() and botao.is_enabled():
                            # Destaque o botão para debug visual
                            driver.execute_script("arguments[0].style.border = '2px solid green';", botao)
                            time.sleep(0.3)
                            # Tente clicar
                            botao.click()
                            time.sleep(2)
                            # Verificar se o campo está vazio (comentário enviado)
                            if not campo.get_attribute("value"):
                                self.status_update.emit(f"✅ Comentário enviado com botão ({seletor}) para '{username}'!")
                                with self.acoes_lock:
                                    self.acoes_concluidas += 1
                                    self.progresso_atualizado.emit(self.acoes_concluidas, self.total_acoes)
                                # Limpar recursos
                                if username in self.perfis_em_execucao:
                                    self.perfis_em_execucao.remove(username)
                                if username in self.workers_ativos:
                                    del self.workers_ativos[username]
                                if not self.manter_navegador_aberto:
                                    driver.quit()
                                return True
                except Exception as e:
                    continue
                    
            # 5.3 Método 3: Usar JavaScript para forçar o envio do formulário
            self.status_update.emit("🔄 Tentando enviar com JavaScript...")
            try:
                # Tentar vários métodos JavaScript
                scripts = [
                    # Acionar evento de tecla Enter no campo
                    "arguments[0].dispatchEvent(new KeyboardEvent('keydown', {'key': 'Enter', 'code': 'Enter', 'keyCode': 13, 'which': 13, 'bubbles': true}));",
                    # Procurar formulário pai e submeter
                    "arguments[0].form.submit();",
                    # Encontrar o botão mais próximo e clicar
                    "arguments[0].closest('form').querySelector('button').click();",
                    # Simular mudança de evento e pressionar Enter
                    "arguments[0].dispatchEvent(new Event('change', { bubbles: true })); arguments[0].dispatchEvent(new KeyboardEvent('keydown', {'key': 'Enter', 'bubbles': true}));"
                ]
                
                for script in scripts:
                    try:
                        driver.execute_script(script, campo)
                        time.sleep(2)
                        # Verificar se o comentário foi enviado
                        if not campo.get_attribute("value"):
                            self.status_update.emit(f"✅ Comentário enviado com JavaScript para '{username}'!")
                            with self.acoes_lock:
                                self.acoes_concluidas += 1
                                self.progresso_atualizado.emit(self.acoes_concluidas, self.total_acoes)
                            # Limpar recursos
                            if username in self.perfis_em_execucao:
                                self.perfis_em_execucao.remove(username)
                            if username in self.workers_ativos:
                                del self.workers_ativos[username]
                            if not self.manter_navegador_aberto:
                                driver.quit()
                            return True
                    except:
                        continue
            except Exception as e:
                self.status_update.emit(f"⚠️ Erro ao usar JavaScript: {str(e)}")
                
            # 5.4 Método 4: Tentar com ActionChains
            self.status_update.emit("🔄 Tentando com ActionChains...")
            try:
                actions = ActionChains(driver)
                actions.click(campo)
                actions.pause(0.5)
                actions.send_keys(Keys.ENTER)
                actions.perform()
                time.sleep(2)
                
                if not campo.get_attribute("value"):
                    self.status_update.emit(f"✅ Comentário enviado com ActionChains para '{username}'!")
                    with self.acoes_lock:
                        self.acoes_concluidas += 1
                        self.progresso_atualizado.emit(self.acoes_concluidas, self.total_acoes)
                    # Limpar recursos
                    if username in self.perfis_em_execucao:
                        self.perfis_em_execucao.remove(username)
                    if username in self.workers_ativos:
                        del self.workers_ativos[username]
                    if not self.manter_navegador_aberto:
                        driver.quit()
                    return True
            except Exception as e:
                self.status_update.emit(f"⚠️ Erro com ActionChains: {str(e)}")
            
            # 5.5 Persistir e tentar uma última vez
            self.status_update.emit("🔄 Última tentativa com combinação de técnicas...")
            try:
                # Dar foco novamente, limpar e redigitar
                actions = ActionChains(driver)
                actions.move_to_element(campo).click().perform()
                campo.clear()
                campo.send_keys(texto_comentario)
                # Simular Ctrl+Enter (funciona em alguns sites)
                actions.key_down(Keys.CONTROL).send_keys(Keys.ENTER).key_up(Keys.CONTROL).perform()
                time.sleep(2)
                
                if not campo.get_attribute("value"):
                    self.status_update.emit(f"✅ Comentário enviado na última tentativa para '{username}'!")
                    with self.acoes_lock:
                        self.acoes_concluidas += 1
                        self.progresso_atualizado.emit(self.acoes_concluidas, self.total_acoes)
                    # Limpar recursos
                    if username in self.perfis_em_execucao:
                        self.perfis_em_execucao.remove(username)
                    if username in self.workers_ativos:
                        del self.workers_ativos[username]
                    if not self.manter_navegador_aberto:
                        driver.quit()
                    return True
            except Exception as e:
                self.status_update.emit(f"⚠️ Erro na última tentativa: {str(e)}")
            
            # Avisar que todas as tentativas falharam
            self.status_update.emit(f"❌ Não foi possível enviar o comentário para '{username}' após múltiplas tentativas!")
            # Pode-se considerar uma solicitação manual ao usuário
            self.status_update.emit(f"ℹ️ Tente interagir manualmente com o navegador de '{username}' para finalizar o comentário")
            
            # Se chegou até aqui, falhou em enviar o comentário
            self.status_update.emit(f"❌ Falha ao enviar comentário para '{username}'")
            if username in self.perfis_em_execucao:
                self.perfis_em_execucao.remove(username)
            if username in self.workers_ativos:
                del self.workers_ativos[username]
            if not self.manter_navegador_aberto:
                driver.quit()
            return False
            
        except Exception as e:
            self.status_update.emit(f"❌ Erro ao comentar para '{username}': {str(e)}")
            # Limpar recursos
            if username in self.perfis_em_execucao:
                self.perfis_em_execucao.remove(username)
            if username in self.workers_ativos:
                del self.workers_ativos[username]
            if not self.manter_navegador_aberto:
                try:
                    driver.quit()
                except:
                    pass
            return False
