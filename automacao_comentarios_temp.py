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
            
            # Selecionar próximo perfil disponível 
            for perfil in perfis_disponiveis:
                # Pular perfis que já estão em execução
                if perfil in self.perfis_em_execucao:
                    continue
                # Adicionar à lista de perfis em execução
                self.perfis_em_execucao.append(perfil)
                # Iniciar thread para este perfil
                self.status_update.emit(f"🔄 Iniciando perfil: {perfil}")
                self._executar_acao_perfil(perfil)
                # Aguardar um tempo entre iniciar perfis para evitar sobrecarga
                time.sleep(self.tempo_entre_acoes)
                break
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
            
            # Se for um perfil específico como gabrielamartinsrt, tentar comentar imediatamente
            if "gabrielamartinsrt" in self.post_url or "iniciar_rapido" in str(username).lower():
                self.status_update.emit(f"⚡ Perfil específico detectado. Iniciando comentário imediato para '{username}'...")
                
                # Implementação direta de comentário
                success = False
                try:
                    # Dar foco ao navegador antes de interagir
                    driver.switch_to.window(driver.current_window_handle)
                    driver.execute_script("window.focus();")
                    time.sleep(1)
                    
                    # Procurar o campo de comentário com diferentes seletores
                    seletores = [
                        "//textarea[contains(@placeholder, 'coment')]",
                        "//textarea[contains(@aria-label, 'comment')]",
                        "//*[@role='textbox']",
                        "//form//textarea",
                        "//section//textarea",
                        "//*[@placeholder='Adicione um comentário...']",
                        "//*[@placeholder='Add a comment…']",
                        "//span[text()='Add a comment…']/parent::*/parent::*//*[@role='textbox']",
                        "//span[text()='Adicione um comentário...']/parent::*/parent::*//*[@role='textbox']"
                    ]
                    
                    campo = None
                    for seletor in seletores:
                        try:
                            campo = driver.find_element(By.XPATH, seletor)
                            if campo and campo.is_displayed():
                                self.status_update.emit(f"✅ Campo de comentário encontrado com seletor: {seletor}")
                                break
                        except:
                            continue
                    
                    # Se não encontrou com os seletores anteriores, tente rolar a página
                    if not campo:
                        self.status_update.emit(f"⚠️ Campo não encontrado, tentando rolar a página...")
                        driver.execute_script("window.scrollBy(0, 300);")
                        time.sleep(1)
                        for seletor in seletores:
                            try:
                                campo = driver.find_element(By.XPATH, seletor)
                                if campo and campo.is_displayed():
                                    self.status_update.emit(f"✅ Campo encontrado após rolagem com seletor: {seletor}")
                                    break
                            except:
                                continue
                                
                    if campo:
                        # Clicar e limpar o campo
                        campo.click()
                        campo.clear()
                        time.sleep(0.5)
                        
                        # Digitar o comentário
                        campo.send_keys(comentario)
                        time.sleep(1)
                        
                        # Método 1: Pressionar Enter
                        campo.send_keys(Keys.ENTER)
                        time.sleep(2)
                        
                        # Verificar se comentário foi enviado
                        if not campo.get_attribute("value"):
                            success = True
                            self.status_update.emit(f"✅ Comentário enviado com sucesso para '{username}'!")
                        else:
                            # Tentar método 2: procurar botão de publicar
                            self.status_update.emit(f"⚠️ Enter não funcionou, tentando clicar no botão...")
                            botoes = driver.find_elements(By.XPATH, "//button[contains(text(), 'Publicar') or contains(text(), 'Post') or contains(text(), 'Comentar') or contains(text(), 'Comment')]")
                            for botao in botoes:
                                if botao.is_displayed() and botao.is_enabled():
                                    botao.click()
                                    time.sleep(2)
                                    if not campo.get_attribute("value"):
                                        success = True
                                        self.status_update.emit(f"✅ Comentário enviado com sucesso via botão para '{username}'!")
                                        break
                    else:
                        self.status_update.emit(f"❌ Não foi possível encontrar o campo de comentário para '{username}'")
                except Exception as e:
                    self.status_update.emit(f"⚠️ Erro ao tentar comentar: {str(e)}")
                
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

    def _comentar_direto(self, driver, username, texto_comentario):
        """Função simplificada para comentar diretamente, substituindo _comentar_post."""
        try:
            # IMPORTANTE: Dar foco ao navegador antes de interagir
            driver.switch_to.window(driver.current_window_handle)
            driver.execute_script("window.focus();")
            time.sleep(0.5)
            
            # Procurar o campo de comentário com diferentes seletores
            seletores = [
                "//textarea[contains(@placeholder, 'coment')]",
                "//textarea[contains(@aria-label, 'comment')]",
                "//*[@role='textbox']",
                "//form//textarea",
                "//section//textarea",
                "//*[@placeholder='Adicione um comentário...']",
                "//*[@placeholder='Add a comment…']",
                "//span[text()='Add a comment…']/parent::*/parent::*//*[@role='textbox']",
                "//span[text()='Adicione um comentário...']/parent::*/parent::*//*[@role='textbox']"
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
            
            # Clicar e limpar o campo
            campo.click()
            campo.clear()
            time.sleep(0.5)
            
            # Digitar o comentário
            campo.send_keys(texto_comentario)
            time.sleep(1)
            
            # Método 1: Pressionar Enter
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
            
            # Método 2: Procurar e clicar em botões
            botoes = driver.find_elements(By.XPATH, "//button[contains(text(), 'Publicar') or contains(text(), 'Post') or contains(text(), 'Comentar') or contains(text(), 'Comment')]")
            for botao in botoes:
                if botao.is_displayed() and botao.is_enabled():
                    botao.click()
                    time.sleep(2)
                    if not campo.get_attribute("value"):
                        self.status_update.emit(f"✅ Comentário enviado com sucesso (botão) para '{username}'!")
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
