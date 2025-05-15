# Método para ser adicionado na classe AutomacaoComentariosWorker

def _comentar_post(self, driver, username, texto_comentario, acoes_realizadas):
    """Tenta adicionar um comentário ao post."""
    max_tentativas = 5  # Aumentado o número de tentativas
    
    # Dar foco ao navegador antes de interagir
    try:
        driver.switch_to.window(driver.current_window_handle)
        driver.execute_script("window.focus();")
    except Exception as e:
        self.status_update.emit(f"⚠️ Erro ao ativar navegador: {str(e)}")
    
    # Loop de tentativas para comentar
    for tentativa in range(1, max_tentativas + 1):
        self.status_update.emit(f"💬 Tentativa {tentativa}/{max_tentativas} de comentar com '{username}'...")
        
        # Identificar o campo de comentário com estratégia mais agressiva
        seletores_campo_comentario = [
            # Seletores específicos do Instagram
            "//form[contains(@class, 'comment')]//textarea",
            "//textarea[contains(@placeholder, 'coment')]",
            "//textarea[contains(@aria-label, 'comment')]",
            "//textarea[contains(@aria-label, 'coment')]",
            "//*[@role='textbox' and contains(@aria-label, 'coment')]",
            "//*[@role='textbox' and contains(@aria-label, 'comment')]",
            "//*[@role='textbox']",  # Seletor mais genérico
            "//*[@placeholder='Adicione um comentário...']",
            "//*[@placeholder='Add a comment…']",
            "//span[text()='Add a comment…']/parent::*/parent::*//*[@role='textbox']",
            "//span[text()='Adicione um comentário...']/parent::*/parent::*//*[@role='textbox']",
            # Último recurso: qualquer textarea na página
            "//form//textarea",
            "//section//textarea",
            "//textarea"
        ]
        
        campo_comentario = None  # Resetar campo para cada tentativa
        
        # Tentar encontrar o campo de comentário
        for seletor in seletores_campo_comentario:
            try:
                campo_comentario = driver.find_element(By.XPATH, seletor)
                if campo_comentario.is_displayed():
                    self.status_update.emit(f"✅ Campo de comentário encontrado com seletor: {seletor}")
                    break
            except:
                continue
                
        # Se não encontrou, tente rolar a página e procurar novamente
        if not campo_comentario:
            driver.execute_script("window.scrollBy(0, 300);")
            time.sleep(1)
            for seletor in seletores_campo_comentario:
                try:
                    campo_comentario = driver.find_element(By.XPATH, seletor)
                    if campo_comentario.is_displayed():
                        self.status_update.emit(f"✅ Campo de comentário encontrado após rolagem: {seletor}")
                        break
                except:
                    continue
        
        # Se ainda não encontrou, desistir desta tentativa
        if not campo_comentario:
            self.status_update.emit(f"❌ Campo de comentário não encontrado na tentativa {tentativa}")
            if tentativa < max_tentativas:
                continue
            else:
                return False
        
        # Tentar digitar e enviar o comentário
        try:
            # Clicar e limpar o campo
            campo_comentario.click()
            campo_comentario.clear()
            time.sleep(0.5)
            
            # Digitar o comentário
            campo_comentario.send_keys(texto_comentario)
            time.sleep(1)
            
            # Método 1: Pressionar Enter
            campo_comentario.send_keys(Keys.ENTER)
            time.sleep(2)
            
            # Verificar se o comentário foi enviado
            if not campo_comentario.get_attribute("value"):
                self.status_update.emit(f"✅ Comentário enviado com sucesso para '{username}'!")
                return True
            
            # Método 2: Procurar e clicar no botão de publicar
            botoes = driver.find_elements(By.XPATH, "//button[contains(text(), 'Publicar') or contains(text(), 'Post') or contains(text(), 'Comentar') or contains(text(), 'Comment')]")
            for botao in botoes:
                if botao.is_displayed() and botao.is_enabled():
                    botao.click()
                    time.sleep(2)
                    if not campo_comentario.get_attribute("value"):
                        self.status_update.emit(f"✅ Comentário enviado com sucesso para '{username}'!")
                        return True
            
            # Se chegamos aqui, não conseguimos enviar o comentário nesta tentativa
            self.status_update.emit(f"⚠️ Não foi possível enviar o comentário na tentativa {tentativa}")
            
        except Exception as e:
            self.status_update.emit(f"⚠️ Erro ao tentar comentar: {str(e)}")
        
        # Se não conseguimos enviar o comentário, tente novamente se não for a última tentativa
        if tentativa < max_tentativas:
            time.sleep(1)
            continue
    
    # Se chegamos aqui, todas as tentativas falharam
    self.status_update.emit(f"❌ Todas as {max_tentativas} tentativas de comentar falharam para '{username}'.")
    return False