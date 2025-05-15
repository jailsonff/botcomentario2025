import sys
import os
import time
import json
import random
import re
from datetime import datetime
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QRegularExpression, pyqtSlot
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QListWidget, QListWidgetItem, QTabWidget, 
    QGroupBox, QTextEdit, QScrollArea, QMessageBox, QComboBox,
    QFileDialog, QProgressBar, QLineEdit, QCheckBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QSpinBox,
    QSplitter, QFrame, QRadioButton, QButtonGroup, QSpacerItem, QSizePolicy, QGridLayout,
    QColorDialog, QSlider
)
from PyQt5.QtGui import QIcon, QRegularExpressionValidator, QPixmap, QColor, QFont, QTextCursor

# Importações de módulos específicos do bot
from automacao_comentarios import AutomacaoComentariosWorker
from dolphin_anty_manager import DolphinAntyManager

class BotComentariosInterface(QMainWindow):
    """Interface gráfica para o Bot de Comentários do Instagram"""
    
    def __init__(self):
        super().__init__()
        
        # Propriedades principais
        self.setWindowTitle("Bot de Comentários Instagram")
        self.setMinimumSize(1000, 700)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #333333;
                color: white;
            }
            QLabel {
                color: white;
                font-size: 11pt;
            }
            QGroupBox {
                border: 1px solid #555555;
                border-radius: 5px;
                margin-top: 12px;
                font-size: 11pt;
                color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 10px;
                padding: 0 5px;
            }
            QPushButton {
                background-color: #555555;
                color: white;
                padding: 6px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #666666;
            }
            QPushButton:disabled {
                background-color: #444444;
                color: #888888;
            }
            QLineEdit, QTextEdit {
                background-color: #555555;
                color: white;
                border: 1px solid #777777;
                border-radius: 3px;
                padding: 5px;
            }
            QSpinBox {
                background-color: #777777;
                color: white;
                border: 2px solid #aaaaaa;
                border-radius: 5px;
                padding: 8px;
                min-width: 120px;
                min-height: 40px;
                text-align: center;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background-color: #777777;
                width: 16px;
            }
            QTabWidget::pane {
                border: 1px solid #555555;
                background-color: #333333;
            }
            QTabBar::tab {
                background-color: #444444;
                color: white;
                padding: 8px 15px;
                margin-right: 3px;
                border-top-left-radius: 3px;
                border-top-right-radius: 3px;
            }
            QTabBar::tab:selected {
                background-color: #555555;
            }
            QTabBar::tab:hover {
                background-color: #666666;
            }
            QTableWidget {
                background-color: #444444;
                color: white;
                gridline-color: #555555;
                outline: none;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QHeaderView::section {
                background-color: #555555;
                color: white;
                padding: 5px;
                border: 1px solid #666666;
            }
            QCheckBox {
                color: white;
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }
            QListWidget {
                background-color: #444444;
                color: white;
                border: 1px solid #555555;
                outline: none;
            }
            QListWidget::item {
                padding: 5px;
            }
            QListWidget::item:selected {
                background-color: #555555;
            }
            QScrollBar:vertical {
                background-color: #444444;
                width: 12px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: #666666;
                min-height: 20px;
                border-radius: 6px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QProgressBar {
                border: 1px solid #555555;
                border-radius: 3px;
                background-color: #444444;
                color: white;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #27ae60;
                width: 10px;
                margin: 0.5px;
            }
        """)
        
        # Inicializar gerenciador de perfis do Dolphin Anty
        self.dolphin_manager = DolphinAntyManager()
        
        # Variáveis para controle da automação
        self.automacao_worker = None
        self.perfis_selecionados = []
        self.automacao_em_execucao = False
        
        # Variável para o modo de seleção de cores
        self.modo_selecao_cores_ativo = False
        
        # Inicializar UI
        self.init_ui()
        
        # Carregar perfis do Dolphin Anty ao iniciar
        QTimer.singleShot(500, self.carregar_perfis)
        
        # Carregar configurações personalizadas salvas
        QTimer.singleShot(800, self.carregar_configuracao)
        
    def init_ui(self):
        """Inicializa a interface do usuário"""
        # Widget principal
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Título e informações
        titulo_layout = QHBoxLayout()
        
        titulo_label = QLabel("Bot de Comentários Instagram")
        titulo_label.setStyleSheet("font-size: 18pt; font-weight: bold; color: #27ae60;")
        
        versao_label = QLabel("v1.0")
        versao_label.setStyleSheet("font-size: 10pt; color: #888888;")
        
        titulo_layout.addWidget(titulo_label)
        titulo_layout.addStretch()
        titulo_layout.addWidget(versao_label)
        
        main_layout.addLayout(titulo_layout)
        
        # Separador
        separador = QFrame()
        separador.setFrameShape(QFrame.HLine)
        separador.setFrameShadow(QFrame.Sunken)
        separador.setStyleSheet("background-color: #555555;")
        main_layout.addWidget(separador)
        
        # Criando as abas
        self.tabs = QTabWidget()
        
        # Criar as abas principais
        self.tab_automacao = QWidget()
        self.tab_personalizacao = QWidget()
        
        # Adicionar abas ao widget de abas
        self.tabs.addTab(self.tab_automacao, "Automação de Comentários")
        self.tabs.addTab(self.tab_personalizacao, "Personalização")
        
        # Inicializar abas
        self.init_tab_automacao()
        self.init_tab_personalizacao()
        
        # Adicionar widget de abas ao layout principal
        main_layout.addWidget(self.tabs)
        
        # Área de log na parte inferior
        log_group = QGroupBox("Log de Operações")
        log_layout = QVBoxLayout(log_group)
        
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMinimumHeight(150)
        self.status_text.setStyleSheet("""
            QTextEdit {
                background-color: #222222;
                color: #cccccc;
                font-family: Consolas, Monaco, monospace;
                font-size: 10pt;
            }
        """)
        log_layout.addWidget(self.status_text)
        
        # Adicionar grupo de log ao layout principal
        main_layout.addWidget(log_group)
        
        # Barra de status inferior
        status_layout = QHBoxLayout()
        
        self.status_label = QLabel("Pronto")
        status_layout.addWidget(self.status_label)
        
        status_layout.addStretch()
        
        self.perfis_status_label = QLabel("0 perfis carregados")
        status_layout.addWidget(self.perfis_status_label)
        
        main_layout.addLayout(status_layout)
        
        # Adicionar mensagem inicial no log
        self.adicionar_log("Bot de Comentários inicializado. Carregando perfis...")
    
    def init_tab_automacao(self):
        """Inicializa a aba de automação de comentários"""
        # Layout principal da aba
        layout = QVBoxLayout(self.tab_automacao)
        layout.setSpacing(10)
        
        # Divisão horizontal da aba (perfis à esquerda, configurações à direita)
        splitter = QSplitter(Qt.Horizontal)
        
        # Área de perfis (lado esquerdo)
        perfis_widget = QWidget()
        perfis_layout = QVBoxLayout(perfis_widget)
        perfis_layout.setContentsMargins(5, 5, 5, 5)
        
        # Título e botões para controle de perfis
        perfis_header = QHBoxLayout()
        
        perfis_titulo = QLabel("Perfis Disponíveis")
        perfis_titulo.setStyleSheet("font-weight: bold; font-size: 12pt;")
        
        atualizar_perfis_button = QPushButton("🔄 Atualizar")
        atualizar_perfis_button.setMaximumWidth(100)
        atualizar_perfis_button.setStyleSheet("""
            QPushButton {
                background-color: #444444;
                padding: 5px;
            }
        """)
        atualizar_perfis_button.clicked.connect(self.carregar_perfis)
        
        perfis_header.addWidget(perfis_titulo)
        perfis_header.addStretch()
        perfis_header.addWidget(atualizar_perfis_button)
        
        perfis_layout.addLayout(perfis_header)
        
        # Botões de seleção de perfis
        perfis_selecao_layout = QHBoxLayout()
        
        selecionar_todos_btn = QPushButton("Selecionar Todos")
        selecionar_todos_btn.setStyleSheet("""
            QPushButton {
                background-color: #2980b9;
                color: white;
                padding: 5px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3498db;
            }
        """)
        selecionar_todos_btn.clicked.connect(self.selecionar_todos_perfis)
        
        desmarcar_todos_btn = QPushButton("Desmarcar Todos")
        desmarcar_todos_btn.setStyleSheet("""
            QPushButton {
                background-color: #7f8c8d;
                color: white;
                padding: 5px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #95a5a6;
            }
        """)
        desmarcar_todos_btn.clicked.connect(self.desmarcar_todos_perfis)
        
        perfis_selecao_layout.addWidget(selecionar_todos_btn)
        perfis_selecao_layout.addWidget(desmarcar_todos_btn)
        

        
        perfis_layout.addLayout(perfis_selecao_layout)
        
        # Lista de perfis
        self.lista_perfis = QListWidget()
        self.lista_perfis.setSelectionMode(QAbstractItemView.MultiSelection)
        perfis_layout.addWidget(self.lista_perfis)
        
        # Informações sobre perfis selecionados
        self.info_selecao_label = QLabel("0 perfis selecionados")
        perfis_layout.addWidget(self.info_selecao_label)
        
        # Conectar sinal de alteração na seleção
        self.lista_perfis.itemSelectionChanged.connect(self.atualizar_perfis_selecionados)
        
        # Área de configurações (lado direito)
        # Criar um widget de scroll para as configurações
        config_scroll = QScrollArea()
        config_scroll.setWidgetResizable(True)
        config_scroll.setFrameShape(QFrame.NoFrame)  # Sem borda na área de rolagem
        
        # Widget interno para conter os elementos de configuração
        config_widget = QWidget()
        config_layout = QVBoxLayout(config_widget)
        config_layout.setContentsMargins(5, 5, 5, 5)
        
        # Definir o widget interno no ScrollArea
        config_scroll.setWidget(config_widget)
        
        # Grupo de configuração do post
        post_group = QGroupBox("Post Alvo")
        post_layout = QGridLayout(post_group)
        
        # URL do post
        url_post_label = QLabel("URL do Post:")
        self.post_url_input = QLineEdit()
        self.post_url_input.setPlaceholderText("https://www.instagram.com/p/XXXXXXX/")
        
        # Configuração de layout para URL
        post_layout.setHorizontalSpacing(50)
        post_layout.addWidget(url_post_label, 0, 0)
        post_layout.addWidget(self.post_url_input, 0, 1)
        
        # Adicionar o grupo ao layout das configurações
        config_layout.addWidget(post_group)
        
        # Grupo de texto dos comentários
        comentarios_group = QGroupBox("Comentários")
        comentarios_layout = QVBoxLayout(comentarios_group)
        
        # Explicação
        comentarios_info = QLabel("Digite um comentário por linha. Um comentário aleatório será escolhido para cada ação.")
        comentarios_info.setWordWrap(True)
        comentarios_info.setStyleSheet("font-size: 10pt; color: #cccccc;")
        comentarios_layout.addWidget(comentarios_info)
        
        # Área de texto para os comentários
        self.comentario_input = QTextEdit()
        self.comentario_input.setMinimumHeight(120)
        self.comentario_input.setPlaceholderText("Digite seus comentários aqui, um por linha:\n\nExemplo:\nLindo post! 😍\nAmei! ❤️\nIncredível! 👏")
        comentarios_layout.addWidget(self.comentario_input)
        
        # Adicionar o grupo ao layout das configurações
        config_layout.addWidget(comentarios_group)
        
        # Grupo das configurações da automação
        self.automacao_group = QGroupBox("Configurações da Automação")
        self.automacao_group.setMinimumHeight(300)  # Garantir altura mínima para o grupo
        automacao_layout = QGridLayout(self.automacao_group)
        automacao_layout.setHorizontalSpacing(50)
        automacao_layout.setVerticalSpacing(15)  # Espaçamento vertical reduzido
        automacao_layout.setContentsMargins(10, 15, 10, 15)  # Margens menores
        
        # Quantidade de ações
        acoes_label = QLabel("Quantidade de ações:")
        acoes_label.setStyleSheet("font-size: 12pt; font-weight: bold;")
        self.acoes_spinbox = QSpinBox()
        self.acoes_spinbox.setMinimum(1)
        self.acoes_spinbox.setMaximum(1000)
        self.acoes_spinbox.setValue(10)
        self.acoes_spinbox.setFixedHeight(60)
        self.acoes_spinbox.setStyleSheet("font-size: 20pt; font-weight: bold; color: white; background-color: #666666; border: 2px solid #aaaaaa;")
        automacao_layout.addWidget(acoes_label, 0, 0)
        automacao_layout.addWidget(self.acoes_spinbox, 0, 1)
        
        # Perfis simultâneos
        perfis_simult_label = QLabel("Perfis simultâneos:")
        perfis_simult_label.setStyleSheet("font-size: 12pt; font-weight: bold;")
        self.perfis_simult_spinbox = QSpinBox()
        self.perfis_simult_spinbox.setMinimum(1)
        self.perfis_simult_spinbox.setMaximum(10)
        self.perfis_simult_spinbox.setValue(2)
        self.perfis_simult_spinbox.setFixedHeight(60)
        self.perfis_simult_spinbox.setStyleSheet("font-size: 20pt; font-weight: bold; color: white; background-color: #666666; border: 2px solid #aaaaaa;")
        automacao_layout.addWidget(perfis_simult_label, 1, 0)
        automacao_layout.addWidget(self.perfis_simult_spinbox, 1, 1)
        
        # Tempo entre ações
        tempo_acoes_label = QLabel("Tempo entre ações (seg):")
        tempo_acoes_label.setStyleSheet("font-size: 12pt; font-weight: bold;")
        self.tempo_acoes_spinbox = QSpinBox()
        self.tempo_acoes_spinbox.setMinimum(10)
        self.tempo_acoes_spinbox.setMaximum(300)
        self.tempo_acoes_spinbox.setValue(30)
        self.tempo_acoes_spinbox.setFixedHeight(60)
        self.tempo_acoes_spinbox.setStyleSheet("font-size: 20pt; font-weight: bold; color: white; background-color: #666666; border: 2px solid #aaaaaa;")
        automacao_layout.addWidget(tempo_acoes_label, 2, 0)
        automacao_layout.addWidget(self.tempo_acoes_spinbox, 2, 1)
        
        # Manter navegador aberto
        self.manter_navegador_checkbox = QCheckBox("Manter navegador aberto após comentar")
        automacao_layout.addWidget(self.manter_navegador_checkbox, 3, 0, 1, 2)
        
        # Adicionar o grupo ao layout das configurações
        config_layout.addWidget(self.automacao_group)
        
        # Barra de progresso e botão de iniciar
        progress_layout = QVBoxLayout()
        
        # Layout informativo
        info_layout = QHBoxLayout()
        self.progresso_automacao_label = QLabel("0/0 ações concluídas")
        info_layout.addWidget(self.progresso_automacao_label)
        info_layout.addStretch()
        
        progress_layout.addLayout(info_layout)
        
        # Barra de progresso
        self.barra_progresso = QProgressBar()
        self.barra_progresso.setMinimum(0)
        self.barra_progresso.setMaximum(100)
        self.barra_progresso.setValue(0)
        progress_layout.addWidget(self.barra_progresso)
        
        # Botão de iniciar automação
        self.iniciar_automacao_button = QPushButton("▶️ Iniciar Automação")
        self.iniciar_automacao_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 12pt;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #888;
            }
        """)
        self.iniciar_automacao_button.clicked.connect(self._iniciar_automacao_comentarios)
        progress_layout.addWidget(self.iniciar_automacao_button)
        
        # Adicionar layout de progresso às configurações
        config_layout.addLayout(progress_layout)
        
        # Adicionar espaçador para empurrar elementos para cima
        config_layout.addStretch()
        
        # Adicionar widgets ao splitter
        splitter.addWidget(perfis_widget)
        splitter.addWidget(config_scroll)  # Usar o ScrollArea em vez do widget direto
        
        # Definir proporções do splitter (30% para lista de perfis, 70% para configurações)
        splitter.setSizes([300, 700])
        
        # Adicionar splitter ao layout principal da aba
        layout.addWidget(splitter)
    
    def adicionar_log(self, mensagem):
        """Adiciona uma mensagem ao log com timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {mensagem}"
        
        # Adicionar ao QTextEdit de log
        self.status_text.append(log_entry)
        
        # Rolar para o final
        cursor = self.status_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.status_text.setTextCursor(cursor)
        
        # Atualizar a barra de status
        self.status_label.setText(mensagem)
        
        # Print para debug no console (opcional)
        print(log_entry)
        
    def carregar_perfis(self):
        """Carrega os perfis de usuário do Dolphin Anty"""
        self.adicionar_log("Carregando perfis do Dolphin Anty...")
        self.lista_perfis.clear()
        
        try:
            # Obter todos os perfis e metadados
            perfis_metadados = self.dolphin_manager.get_all_profiles_metadata()
            
            if not perfis_metadados:
                self.adicionar_log("Nenhum perfil encontrado. Verifique o diretório de perfis.")
                self.perfis_status_label.setText("0 perfis carregados")
                return
            
            # Adicionar cada perfil à lista
            for nome_perfil, metadados in perfis_metadados.items():
                # Criar item da lista
                item = QListWidgetItem(nome_perfil)
                
                # Definir cor conforme status de login
                status = metadados.get('bot_login_status', 'desconhecido')
                
                if status == 'conectado' or status == 'success':
                    item.setForeground(QColor('#27ae60'))  # Verde para conectado
                    item.setToolTip(f"Perfil conectado: {nome_perfil}")
                elif status == 'falhou' or status == 'failed' or status == 'erro':
                    item.setForeground(QColor('#e74c3c'))  # Vermelho para erro
                    item.setToolTip(f"Erro no perfil: {nome_perfil}")
                elif status == 'desconectado':
                    item.setForeground(QColor('#f39c12'))  # Laranja para desconectado
                    item.setToolTip(f"Perfil desconectado: {nome_perfil}")
                else:
                    item.setForeground(QColor('#bdc3c7'))  # Cinza para desconhecido
                    item.setToolTip(f"Status desconhecido: {nome_perfil}")
                
                # Adicionar à lista
                self.lista_perfis.addItem(item)
            
            total_perfis = len(perfis_metadados)
            self.adicionar_log(f"{total_perfis} perfis carregados com sucesso.")
            self.perfis_status_label.setText(f"{total_perfis} perfis carregados")
            
        except Exception as e:
            self.adicionar_log(f"Erro ao carregar perfis: {str(e)}")
            self.perfis_status_label.setText("Erro ao carregar perfis")
    
    def atualizar_perfis_selecionados(self):
        """Atualiza a lista de perfis selecionados"""
        self.perfis_selecionados = [item.text() for item in self.lista_perfis.selectedItems()]
        num_selecionados = len(self.perfis_selecionados)
        
        self.info_selecao_label.setText(f"{num_selecionados} perfis selecionados")
        
        # Habilitar/desabilitar botão de iniciar automação com base na seleção
        url_valida = "instagram.com/p/" in self.post_url_input.text()
        comentarios_validos = len(self.comentario_input.toPlainText().strip()) > 0
        
        self.iniciar_automacao_button.setEnabled(
            num_selecionados > 0 and 
            url_valida and 
            comentarios_validos and 
            not self.automacao_em_execucao
        )
    
    def selecionar_todos_perfis(self):
        """Seleciona todos os perfis na lista"""
        try:
            # Bloquear sinais temporariamente para evitar múltiplas chamadas ao método de atualização
            self.lista_perfis.blockSignals(True)
            
            # Selecionar todos os itens
            for i in range(self.lista_perfis.count()):
                item = self.lista_perfis.item(i)
                item.setSelected(True)
                
            # Desbloquear sinais
            self.lista_perfis.blockSignals(False)
            
            # Atualizar informações de seleção
            self.atualizar_perfis_selecionados()
            
            # Adicionar ao log
            self.adicionar_log(f"Todos os {self.lista_perfis.count()} perfis foram selecionados")
        except Exception as e:
            self.adicionar_log(f"Erro ao selecionar todos os perfis: {str(e)}")
    
    def desmarcar_todos_perfis(self):
        """Desmarca todos os perfis na lista"""
        try:
            # Bloquear sinais temporariamente
            self.lista_perfis.blockSignals(True)
            
            # Desmarcar todos os itens
            for i in range(self.lista_perfis.count()):
                item = self.lista_perfis.item(i)
                item.setSelected(False)
                
            # Desbloquear sinais
            self.lista_perfis.blockSignals(False)
            
            # Atualizar informações de seleção
            self.atualizar_perfis_selecionados()
            
            # Adicionar ao log
            self.adicionar_log("Todos os perfis foram desmarcados")
        except Exception as e:
            self.adicionar_log(f"Erro ao desmarcar perfis: {str(e)}")
    
    def _iniciar_automacao_comentarios(self):
        """Inicia a automação de comentários nos perfis selecionados"""
        try:
            self.adicionar_log("Preparando início da automação...")
            
            # Verificar se há perfis selecionados
            if not self.perfis_selecionados:
                self.adicionar_log("Erro: Nenhum perfil selecionado")
                QMessageBox.warning(self, "Nenhum perfil selecionado", "Selecione pelo menos um perfil para iniciar a automação.")
                return
            
            # Verificar URL do post
            post_url = self.post_url_input.text().strip()
            if not post_url or "instagram.com/p/" not in post_url:
                self.adicionar_log("Erro: URL inválida")
                QMessageBox.warning(self, "URL inválida", "Digite uma URL válida do Instagram.\nExemplo: https://www.instagram.com/p/XXXXXXX/")
                return
            
            # Verificar comentários
            texto_comentarios = self.comentario_input.toPlainText().strip()
            if not texto_comentarios:
                self.adicionar_log("Erro: Nenhum comentário digitado")
                QMessageBox.warning(self, "Sem comentários", "Digite pelo menos um comentário.")
                return
                
            self.adicionar_log(f"Dados validados: {len(self.perfis_selecionados)} perfis selecionados, URL válida e comentários prontos.")
        except Exception as e:
            self.adicionar_log(f"Erro na validação de dados: {str(e)}")
            QMessageBox.critical(self, "Erro", f"Ocorreu um erro ao validar os dados: {str(e)}")
            return
        
        try:
            # Confirmar início da automação
            total_acoes = self.acoes_spinbox.value()
            perfis_simult = self.perfis_simult_spinbox.value()
            tempo_acoes = self.tempo_acoes_spinbox.value()
            manter_navegador = self.manter_navegador_checkbox.isChecked()
            
            msg = f"Iniciar automação com as seguintes configurações?\n\n"
            msg += f"• URL: {post_url}\n"
            msg += f"• Perfis selecionados: {len(self.perfis_selecionados)}\n"
            msg += f"• Quantidade de ações: {total_acoes}\n"
            msg += f"• Perfis simultâneos: {perfis_simult}\n"
            msg += f"• Tempo entre ações: {tempo_acoes} segundos\n"
            msg += f"• Manter navegador aberto: {'Sim' if manter_navegador else 'Não'}"
            
            confirmar = QMessageBox.question(self, "Confirmar automação", msg, QMessageBox.Yes | QMessageBox.No)
            if confirmar != QMessageBox.Yes:
                self.adicionar_log("Automação cancelada pelo usuário")
                return
                
            self.adicionar_log(f"Configurações confirmadas: {total_acoes} ações com {perfis_simult} perfis simultâneos")
            
            # Iniciar automação
            self.automacao_em_execucao = True
            self.iniciar_automacao_button.setText("⏸️ Parar Automação")
            self.iniciar_automacao_button.setStyleSheet("""
                QPushButton {
                    background-color: #e74c3c;
                    color: white;
                    padding: 8px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #c0392b;
                }
            """)
            
            self.adicionar_log("Alterando comportamento do botão para parar automação...")
            
            # Desconectar e reconectar o clique para mudar a ação
            try:
                self.iniciar_automacao_button.clicked.disconnect()
            except Exception:
                self.adicionar_log("Aviso: Não foi possível desconectar o sinal do botão, isso é normal na primeira execução")
                
            self.iniciar_automacao_button.clicked.connect(self._parar_automacao_comentarios)
            
            # Desabilitar campos de configuração
            self._toggle_campos_automacao(False)
            
            # Configurar barra de progresso
            self.barra_progresso.setMaximum(total_acoes)
            self.barra_progresso.setValue(0)
            self.progresso_automacao_label.setText(f"0/{total_acoes} ações concluídas")
            
            self.adicionar_log("Instanciando worker para automação...")
            
            # Verificar se o dolphin_manager está inicializado
            if not hasattr(self, 'dolphin_manager') or self.dolphin_manager is None:
                from dolphin_anty_manager import DolphinAntyManager
                self.adicionar_log("Inicializando gerenciador Dolphin Anty...")
                self.dolphin_manager = DolphinAntyManager()
            
            # Criar worker para automação
            self.automacao_worker = AutomacaoComentariosWorker(
                self.dolphin_manager,
                post_url,
                self.perfis_selecionados,
                total_acoes,
                perfis_simult,
                tempo_acoes,
                texto_comentarios,
                self,
                manter_navegador
            )
            
            # Conectar sinais
            self.adicionar_log("Conectando sinais do worker...")
            self.automacao_worker.status_update.connect(self.adicionar_log)
            self.automacao_worker.progresso_atualizado.connect(self._atualizar_progresso_automacao)
            self.automacao_worker.acao_concluida.connect(self._on_acao_automacao_concluida)
            self.automacao_worker.automacao_concluida.connect(self._on_automacao_concluida)
            
            # Iniciar worker
            self.adicionar_log("Iniciando automação de comentários...")
            self.automacao_worker.start()
            self.adicionar_log("Worker iniciado com sucesso! Automacao em andamento...")
            
        except Exception as e:
            self.adicionar_log(f"Erro crítico ao iniciar automação: {str(e)}")
            QMessageBox.critical(self, "Erro", f"Ocorreu um erro ao iniciar a automação: {str(e)}")
            self.automacao_em_execucao = False
            # Resetar o botão para estado inicial
            self.iniciar_automacao_button.setText("▶️ Iniciar Automação")
            self.iniciar_automacao_button.setStyleSheet("""
                QPushButton {
                    background-color: #27ae60;
                    color: white;
                    padding: 8px;
                    border-radius: 4px;
                    font-weight: bold;
                    font-size: 12pt;
                }
                QPushButton:hover {
                    background-color: #2ecc71;
                }
                QPushButton:disabled {
                    background-color: #555;
                    color: #888;
                }
            """)
            try:
                self.iniciar_automacao_button.clicked.disconnect()
            except Exception:
                pass
            self.iniciar_automacao_button.clicked.connect(self._iniciar_automacao_comentarios)
    
    def _parar_automacao_comentarios(self):
        """Para a automação de comentários em andamento"""
        if not self.automacao_worker:
            return
            
        # Confirmar parada
        confirmar = QMessageBox.question(
            self, 
            "Confirmar parada", 
            "Deseja realmente parar a automação?\nAs ações em andamento serão concluídas antes da parada completa.", 
            QMessageBox.Yes | QMessageBox.No
        )
        
        if confirmar != QMessageBox.Yes:
            return
            
        # Parar worker
        self.adicionar_log("Parando automação... Aguarde a conclusão das ações em andamento.")
        self.automacao_worker.stop()
        
        # Desabilitar botão de parar
        self.iniciar_automacao_button.setEnabled(False)
        self.iniciar_automacao_button.setText("Parando...")
    
    def _toggle_campos_automacao(self, enabled):
        """Habilita ou desabilita os campos de configuração da automação."""
        self.post_url_input.setEnabled(enabled)
        self.comentario_input.setEnabled(enabled)
        self.acoes_spinbox.setEnabled(enabled)
        self.perfis_simult_spinbox.setEnabled(enabled)
        self.tempo_acoes_spinbox.setEnabled(enabled)
        self.manter_navegador_checkbox.setEnabled(enabled)
        self.lista_perfis.setEnabled(enabled)
    
    def _atualizar_progresso_automacao(self, concluidas, total):
        """Atualiza o progresso da automação na interface."""
        self.progresso_automacao_label.setText(f"{concluidas}/{total} ações concluídas")
        self.barra_progresso.setMaximum(total)
        self.barra_progresso.setValue(concluidas)
    
    def _on_acao_automacao_concluida(self, username, acao, sucesso, mensagem):
        """Chamado quando uma ação de automação é concluída."""
        # Implementar lógica adicional se necessário
        status = "✅" if sucesso else "❌"
        self.adicionar_log(f"{status} Perfil '{username}': {mensagem}")
    
    def _on_automacao_concluida(self):
        """Chamado quando toda a automação é concluída."""
        # Restaura a interface
        self.iniciar_automacao_button.setText("▶️ Iniciar Automação")
        self.iniciar_automacao_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #888;
            }
        """)
        self.iniciar_automacao_button.clicked.disconnect()
        self.iniciar_automacao_button.clicked.connect(self._iniciar_automacao_comentarios)
        self.iniciar_automacao_button.setEnabled(True)
        
        # Habilita os campos de configuração
        self._toggle_campos_automacao(True)
        
        # Atualiza o flag de execução
        self.automacao_em_execucao = False
        
        # Adiciona mensagem ao log
        self.adicionar_log("Automação de comentários concluída!")
        
        # Atualiza a lista de perfis para refletir possíveis mudanças de status
        self.carregar_perfis()
        
    def init_tab_personalizacao(self):
        """Inicializa a aba de personalização da interface"""
        # Layout principal da aba
        layout = QVBoxLayout(self.tab_personalizacao)
        
        # Título da aba
        titulo = QLabel("Personalização da Interface")
        titulo.setStyleSheet("font-size: 16pt; font-weight: bold; color: white;")
        layout.addWidget(titulo)
        
        # Área de rolagem para os controles de personalização
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        # Container para os controles
        container = QWidget()
        container_layout = QVBoxLayout(container)
        
        # 1. Seção de cores
        cores_group = QGroupBox("Cores da Interface")
        cores_layout = QGridLayout(cores_group)
        cores_layout.setVerticalSpacing(10)
        
        # Cores principais
        cores_principais_label = QLabel("Cores Principais")
        cores_principais_label.setStyleSheet("font-weight: bold; font-size: 12pt; color: white;")
        cores_layout.addWidget(cores_principais_label, 0, 0, 1, 3)
        
        # Cor de fundo principal
        bg_color_label = QLabel("Cor de fundo:")
        self.bg_color_button = QPushButton()
        self.bg_color_button.setFixedSize(100, 30)
        self.bg_color_button.setStyleSheet("background-color: #333333;")
        self.bg_color_button.clicked.connect(lambda: self.escolher_cor('background'))
        cores_layout.addWidget(bg_color_label, 1, 0)
        cores_layout.addWidget(self.bg_color_button, 1, 1)
        
        # Cor dos controles
        ctrl_color_label = QLabel("Cor dos controles:")
        self.ctrl_color_button = QPushButton()
        self.ctrl_color_button.setFixedSize(100, 30)
        self.ctrl_color_button.setStyleSheet("background-color: #555555;")
        self.ctrl_color_button.clicked.connect(lambda: self.escolher_cor('controls'))
        cores_layout.addWidget(ctrl_color_label, 2, 0)
        cores_layout.addWidget(self.ctrl_color_button, 2, 1)
        
        # Cor dos botões
        btn_color_label = QLabel("Cor dos botões:")
        self.btn_color_button = QPushButton()
        self.btn_color_button.setFixedSize(100, 30)
        self.btn_color_button.setStyleSheet("background-color: #27ae60;")
        self.btn_color_button.clicked.connect(lambda: self.escolher_cor('buttons'))
        cores_layout.addWidget(btn_color_label, 3, 0)
        cores_layout.addWidget(self.btn_color_button, 3, 1)
        
        # Cor do texto
        text_color_label = QLabel("Cor do texto:")
        self.text_color_button = QPushButton()
        self.text_color_button.setFixedSize(100, 30)
        self.text_color_button.setStyleSheet("background-color: white;")
        self.text_color_button.clicked.connect(lambda: self.escolher_cor('text'))
        cores_layout.addWidget(text_color_label, 4, 0)
        cores_layout.addWidget(self.text_color_button, 4, 1)
        
        # Cores secundárias
        cores_secundarias_label = QLabel("Cores de Destaques")
        cores_secundarias_label.setStyleSheet("font-weight: bold; font-size: 12pt; color: white;")
        cores_layout.addWidget(cores_secundarias_label, 5, 0, 1, 3)
        
        # Cor de destaque
        highlight_color_label = QLabel("Cor de destaque:")
        self.highlight_color_button = QPushButton()
        self.highlight_color_button.setFixedSize(100, 30)
        self.highlight_color_button.setStyleSheet("background-color: #2980b9;")
        self.highlight_color_button.clicked.connect(lambda: self.escolher_cor('highlight'))
        cores_layout.addWidget(highlight_color_label, 6, 0)
        cores_layout.addWidget(self.highlight_color_button, 6, 1)
        
        # Cor de seleção
        selection_color_label = QLabel("Cor de seleção:")
        self.selection_color_button = QPushButton()
        self.selection_color_button.setFixedSize(100, 30)
        self.selection_color_button.setStyleSheet("background-color: #3498db;")
        self.selection_color_button.clicked.connect(lambda: self.escolher_cor('selection'))
        cores_layout.addWidget(selection_color_label, 7, 0)
        cores_layout.addWidget(self.selection_color_button, 7, 1)
        
        # Cor de hover
        hover_color_label = QLabel("Cor de hover:")
        self.hover_color_button = QPushButton()
        self.hover_color_button.setFixedSize(100, 30)
        self.hover_color_button.setStyleSheet("background-color: #666666;")
        self.hover_color_button.clicked.connect(lambda: self.escolher_cor('hover'))
        cores_layout.addWidget(hover_color_label, 8, 0)
        cores_layout.addWidget(self.hover_color_button, 8, 1)
        
        # Cores de status
        cores_status_label = QLabel("Cores de Status")
        cores_status_label.setStyleSheet("font-weight: bold; font-size: 12pt; color: white;")
        cores_layout.addWidget(cores_status_label, 9, 0, 1, 3)
        
        # Cor de sucesso
        success_color_label = QLabel("Cor de sucesso:")
        self.success_color_button = QPushButton()
        self.success_color_button.setFixedSize(100, 30)
        self.success_color_button.setStyleSheet("background-color: #27ae60;")
        self.success_color_button.clicked.connect(lambda: self.escolher_cor('success'))
        cores_layout.addWidget(success_color_label, 10, 0)
        cores_layout.addWidget(self.success_color_button, 10, 1)
        
        # Cor de erro
        error_color_label = QLabel("Cor de erro:")
        self.error_color_button = QPushButton()
        self.error_color_button.setFixedSize(100, 30)
        self.error_color_button.setStyleSheet("background-color: #e74c3c;")
        self.error_color_button.clicked.connect(lambda: self.escolher_cor('error'))
        cores_layout.addWidget(error_color_label, 11, 0)
        cores_layout.addWidget(self.error_color_button, 11, 1)
        
        # Cor de aviso
        warning_color_label = QLabel("Cor de aviso:")
        self.warning_color_button = QPushButton()
        self.warning_color_button.setFixedSize(100, 30)
        self.warning_color_button.setStyleSheet("background-color: #f39c12;")
        self.warning_color_button.clicked.connect(lambda: self.escolher_cor('warning'))
        cores_layout.addWidget(warning_color_label, 12, 0)
        cores_layout.addWidget(self.warning_color_button, 12, 1)
        
        # Cores de elementos
        cores_elem_label = QLabel("Cores de Elementos")
        cores_elem_label.setStyleSheet("font-weight: bold; font-size: 12pt; color: white;")
        cores_layout.addWidget(cores_elem_label, 13, 0, 1, 3)
        
        # Cor de borda
        border_color_label = QLabel("Cor de borda:")
        self.border_color_button = QPushButton()
        self.border_color_button.setFixedSize(100, 30)
        self.border_color_button.setStyleSheet("background-color: #777777;")
        self.border_color_button.clicked.connect(lambda: self.escolher_cor('border'))
        cores_layout.addWidget(border_color_label, 14, 0)
        cores_layout.addWidget(self.border_color_button, 14, 1)
        
        # Cor das abas
        tab_color_label = QLabel("Cor das abas:")
        self.tab_color_button = QPushButton()
        self.tab_color_button.setFixedSize(100, 30)
        self.tab_color_button.setStyleSheet("background-color: #444444;")
        self.tab_color_button.clicked.connect(lambda: self.escolher_cor('tab'))
        cores_layout.addWidget(tab_color_label, 15, 0)
        cores_layout.addWidget(self.tab_color_button, 15, 1)
        
        # Cor da barra de progresso
        progress_color_label = QLabel("Cor da barra de progresso:")
        self.progress_color_button = QPushButton()
        self.progress_color_button.setFixedSize(100, 30)
        self.progress_color_button.setStyleSheet("background-color: #2ecc71;")
        self.progress_color_button.clicked.connect(lambda: self.escolher_cor('progress'))
        cores_layout.addWidget(progress_color_label, 16, 0)
        cores_layout.addWidget(self.progress_color_button, 16, 1)
        
        # Adicionar separador visual
        separador = QFrame()
        separador.setFrameShape(QFrame.HLine)
        separador.setFrameShadow(QFrame.Sunken)
        separador.setStyleSheet("background-color: #555555;")
        separador.setFixedHeight(2)
        cores_layout.addWidget(separador, 17, 0, 1, 3)
        
        # Seleção de cor por clique
        picker_label = QLabel("Modo de Seleção Direta de Cores")
        picker_label.setStyleSheet("font-weight: bold; font-size: 14pt; color: white;")
        cores_layout.addWidget(picker_label, 18, 0, 1, 3)
        
        # Checkbox para ativar o modo de seleção de cores
        self.modo_selecao_cores_checkbox = QCheckBox("Ativar modo de seleção por clique")
        self.modo_selecao_cores_checkbox.setStyleSheet("""
            QCheckBox {
                color: white;
                font-weight: bold;
                font-size: 12pt;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
            }
            QCheckBox::indicator:unchecked {
                border: 2px solid #2980b9;
                background-color: #444444;
            }
            QCheckBox::indicator:checked {
                border: 2px solid #2980b9;
                background-color: #2980b9;
            }
        """)
        self.modo_selecao_cores_checkbox.stateChanged.connect(self.ativar_modo_selecao_cores)
        cores_layout.addWidget(self.modo_selecao_cores_checkbox, 19, 0, 1, 3)
        
        # Texto explicativo sobre o modo de seleção
        explicacao_selector = QLabel("Quando ativado, você pode clicar em qualquer elemento da interface para alterar sua cor. Use essa função para personalizar partes específicas da interface que não estão disponíveis nos controles acima.")
        explicacao_selector.setWordWrap(True)
        explicacao_selector.setStyleSheet("color: #cccccc; font-style: italic;")
        cores_layout.addWidget(explicacao_selector, 20, 0, 1, 3)
        
        # Adicionar outro separador visual
        separador2 = QFrame()
        separador2.setFrameShape(QFrame.HLine)
        separador2.setFrameShadow(QFrame.Sunken)
        separador2.setStyleSheet("background-color: #555555;")
        separador2.setFixedHeight(2)
        cores_layout.addWidget(separador2, 21, 0, 1, 3)
        
        # Templates de cores predefinidos
        templates_label = QLabel("Templates de Cores")
        templates_label.setStyleSheet("font-weight: bold; font-size: 14pt; color: white;")
        cores_layout.addWidget(templates_label, 22, 0, 1, 3)
        
        # Explicação sobre os templates
        templates_info = QLabel("Clique em um dos botões abaixo para aplicar um tema de cores completo.")
        templates_info.setWordWrap(True)
        templates_info.setStyleSheet("color: #cccccc; font-style: italic;")
        cores_layout.addWidget(templates_info, 23, 0, 1, 3)
        
        # Grades de templates
        templates_grid = QGridLayout()
        templates_grid.setHorizontalSpacing(10)
        templates_grid.setVerticalSpacing(10)
        
        # Template 1: Dark Pro
        dark_pro_btn = QPushButton("Dark Pro")
        dark_pro_btn.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #2c3e50, stop:1 #1a1a2e); "
            "color: white; padding: 8px; border-radius: 5px; font-weight: bold;"
        )
        dark_pro_btn.clicked.connect(lambda: self.aplicar_template('dark_pro'))
        templates_grid.addWidget(dark_pro_btn, 0, 0)
        
        # Template 2: Teal Elegance
        teal_elegance_btn = QPushButton("Teal Elegance")
        teal_elegance_btn.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #004d40, stop:1 #00796b); "
            "color: white; padding: 8px; border-radius: 5px; font-weight: bold;"
        )
        teal_elegance_btn.clicked.connect(lambda: self.aplicar_template('teal_elegance'))
        templates_grid.addWidget(teal_elegance_btn, 0, 1)
        
        # Template 3: Purple Haze
        purple_haze_btn = QPushButton("Purple Haze")
        purple_haze_btn.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4a148c, stop:1 #7b1fa2); "
            "color: white; padding: 8px; border-radius: 5px; font-weight: bold;"
        )
        purple_haze_btn.clicked.connect(lambda: self.aplicar_template('purple_haze'))
        templates_grid.addWidget(purple_haze_btn, 0, 2)
        
        # Template 4: Sunset Gold
        sunset_gold_btn = QPushButton("Sunset Gold")
        sunset_gold_btn.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #bf360c, stop:1 #ff9800); "
            "color: white; padding: 8px; border-radius: 5px; font-weight: bold;"
        )
        sunset_gold_btn.clicked.connect(lambda: self.aplicar_template('sunset_gold'))
        templates_grid.addWidget(sunset_gold_btn, 0, 3)
        
        # Template 5: Ocean Blue
        ocean_blue_btn = QPushButton("Ocean Blue")
        ocean_blue_btn.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #01579b, stop:1 #0288d1); "
            "color: white; padding: 8px; border-radius: 5px; font-weight: bold;"
        )
        ocean_blue_btn.clicked.connect(lambda: self.aplicar_template('ocean_blue'))
        templates_grid.addWidget(ocean_blue_btn, 1, 0)
        
        # Template 6: Forest Green
        forest_green_btn = QPushButton("Forest Green")
        forest_green_btn.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1b5e20, stop:1 #388e3c); "
            "color: white; padding: 8px; border-radius: 5px; font-weight: bold;"
        )
        forest_green_btn.clicked.connect(lambda: self.aplicar_template('forest_green'))
        templates_grid.addWidget(forest_green_btn, 1, 1)
        
        # Template 7: Cherry Blossom
        cherry_blossom_btn = QPushButton("Cherry Blossom")
        cherry_blossom_btn.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #880e4f, stop:1 #e91e63); "
            "color: white; padding: 8px; border-radius: 5px; font-weight: bold;"
        )
        cherry_blossom_btn.clicked.connect(lambda: self.aplicar_template('cherry_blossom'))
        templates_grid.addWidget(cherry_blossom_btn, 1, 2)
        
        # Template 8: Midnight
        midnight_btn = QPushButton("Midnight")
        midnight_btn.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0d47a1, stop:1 #000000); "
            "color: white; padding: 8px; border-radius: 5px; font-weight: bold;"
        )
        midnight_btn.clicked.connect(lambda: self.aplicar_template('midnight'))
        templates_grid.addWidget(midnight_btn, 1, 3)
        
        # Template 9: Classic Light
        classic_light_btn = QPushButton("Classic Light")
        classic_light_btn.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #e0e0e0, stop:1 #f5f5f5); "
            "color: #212121; padding: 8px; border-radius: 5px; font-weight: bold;"
        )
        classic_light_btn.clicked.connect(lambda: self.aplicar_template('classic_light'))
        templates_grid.addWidget(classic_light_btn, 2, 0)
        
        # Template 10: Neon Cyberpunk
        neon_cyberpunk_btn = QPushButton("Neon Cyberpunk")
        neon_cyberpunk_btn.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0d0221, stop:1 #261447); "
            "color: #00ff9f; padding: 8px; border-radius: 5px; font-weight: bold;"
        )
        neon_cyberpunk_btn.clicked.connect(lambda: self.aplicar_template('neon_cyberpunk'))
        templates_grid.addWidget(neon_cyberpunk_btn, 2, 1)
        
        # Template 11: Monochrome
        monochrome_btn = QPushButton("Monochrome")
        monochrome_btn.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #212121, stop:1 #424242); "
            "color: white; padding: 8px; border-radius: 5px; font-weight: bold;"
        )
        monochrome_btn.clicked.connect(lambda: self.aplicar_template('monochrome'))
        templates_grid.addWidget(monochrome_btn, 2, 2)
        
        # Template 12: Royal Purple
        royal_purple_btn = QPushButton("Royal Purple")
        royal_purple_btn.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4a0072, stop:1 #9c27b0); "
            "color: white; padding: 8px; border-radius: 5px; font-weight: bold;"
        )
        royal_purple_btn.clicked.connect(lambda: self.aplicar_template('royal_purple'))
        templates_grid.addWidget(royal_purple_btn, 2, 3)
        
        cores_layout.addLayout(templates_grid, 20, 0, 1, 3)
        
        container_layout.addWidget(cores_group)
        
        # 2. Seção de espaçamentos
        espacamento_group = QGroupBox("Espaçamentos")
        espacamento_layout = QGridLayout(espacamento_group)
        
        # Espaçamento vertical entre campos
        v_spacing_label = QLabel("Espaçamento vertical:")
        self.v_spacing_slider = QSlider(Qt.Horizontal)
        self.v_spacing_slider.setMinimum(5)
        self.v_spacing_slider.setMaximum(100)
        self.v_spacing_slider.setValue(60)  # Valor atual
        self.v_spacing_slider.setTickPosition(QSlider.TicksBelow)
        self.v_spacing_slider.setTickInterval(10)
        self.v_spacing_value = QLabel("60px")
        self.v_spacing_slider.valueChanged.connect(self.atualizar_espacamento_vertical)
        espacamento_layout.addWidget(v_spacing_label, 0, 0)
        espacamento_layout.addWidget(self.v_spacing_slider, 0, 1)
        espacamento_layout.addWidget(self.v_spacing_value, 0, 2)
        
        # Espaçamento horizontal entre campos
        h_spacing_label = QLabel("Espaçamento horizontal:")
        self.h_spacing_slider = QSlider(Qt.Horizontal)
        self.h_spacing_slider.setMinimum(5)
        self.h_spacing_slider.setMaximum(100)
        self.h_spacing_slider.setValue(50)  # Valor atual
        self.h_spacing_slider.setTickPosition(QSlider.TicksBelow)
        self.h_spacing_slider.setTickInterval(10)
        self.h_spacing_value = QLabel("50px")
        self.h_spacing_slider.valueChanged.connect(self.atualizar_espacamento_horizontal)
        espacamento_layout.addWidget(h_spacing_label, 1, 0)
        espacamento_layout.addWidget(self.h_spacing_slider, 1, 1)
        espacamento_layout.addWidget(self.h_spacing_value, 1, 2)
        
        # Margem interna dos grupos
        margin_label = QLabel("Margem interna:")
        self.margin_slider = QSlider(Qt.Horizontal)
        self.margin_slider.setMinimum(5)
        self.margin_slider.setMaximum(50)
        self.margin_slider.setValue(30)  # Valor atual
        self.margin_slider.setTickPosition(QSlider.TicksBelow)
        self.margin_slider.setTickInterval(5)
        self.margin_value = QLabel("30px")
        self.margin_slider.valueChanged.connect(self.atualizar_margens)
        espacamento_layout.addWidget(margin_label, 2, 0)
        espacamento_layout.addWidget(self.margin_slider, 2, 1)
        espacamento_layout.addWidget(self.margin_value, 2, 2)
        
        container_layout.addWidget(espacamento_group)
        
        # 3. Seção de tamanhos
        tamanhos_group = QGroupBox("Tamanhos dos Elementos")
        tamanhos_layout = QGridLayout(tamanhos_group)
        tamanhos_layout.setVerticalSpacing(15)
        
        # Altura dos campos
        altura_campos_label = QLabel("Altura dos campos:")
        self.altura_campos_slider = QSlider(Qt.Horizontal)
        self.altura_campos_slider.setMinimum(30)
        self.altura_campos_slider.setMaximum(100)
        self.altura_campos_slider.setValue(60)  # Valor atual
        self.altura_campos_slider.setTickPosition(QSlider.TicksBelow)
        self.altura_campos_slider.setTickInterval(10)
        self.altura_campos_value = QLabel("60px")
        self.altura_campos_slider.valueChanged.connect(self.atualizar_altura_campos)
        tamanhos_layout.addWidget(altura_campos_label, 0, 0)
        tamanhos_layout.addWidget(self.altura_campos_slider, 0, 1)
        tamanhos_layout.addWidget(self.altura_campos_value, 0, 2)
        
        # Tamanho da fonte
        tamanho_fonte_label = QLabel("Tamanho da fonte:")
        self.tamanho_fonte_slider = QSlider(Qt.Horizontal)
        self.tamanho_fonte_slider.setMinimum(8)
        self.tamanho_fonte_slider.setMaximum(30)
        self.tamanho_fonte_slider.setValue(20)  # Valor atual
        self.tamanho_fonte_slider.setTickPosition(QSlider.TicksBelow)
        self.tamanho_fonte_slider.setTickInterval(2)
        self.tamanho_fonte_value = QLabel("20pt")
        self.tamanho_fonte_slider.valueChanged.connect(self.atualizar_tamanho_fonte)
        tamanhos_layout.addWidget(tamanho_fonte_label, 1, 0)
        tamanhos_layout.addWidget(self.tamanho_fonte_slider, 1, 1)
        tamanhos_layout.addWidget(self.tamanho_fonte_value, 1, 2)
        
        # Largura dos rótulos (labels)
        largura_rotulos_label = QLabel("Largura dos rótulos:")
        self.largura_rotulos_slider = QSlider(Qt.Horizontal)
        self.largura_rotulos_slider.setMinimum(80)
        self.largura_rotulos_slider.setMaximum(300)
        self.largura_rotulos_slider.setValue(150)  # Valor atual
        self.largura_rotulos_slider.setTickPosition(QSlider.TicksBelow)
        self.largura_rotulos_slider.setTickInterval(20)
        self.largura_rotulos_value = QLabel("150px")
        self.largura_rotulos_slider.valueChanged.connect(self.atualizar_largura_rotulos)
        tamanhos_layout.addWidget(largura_rotulos_label, 2, 0)
        tamanhos_layout.addWidget(self.largura_rotulos_slider, 2, 1)
        tamanhos_layout.addWidget(self.largura_rotulos_value, 2, 2)
        
        container_layout.addWidget(tamanhos_group)
        
        # 4. Seção de layout avançado
        layout_group = QGroupBox("Layout Avançado")
        layout_avancado = QGridLayout(layout_group)
        layout_avancado.setVerticalSpacing(15)
        
        # Proporção entre colunas (esquerda/direita)
        proporcao_label = QLabel("Proporção colunas (esq/dir):")
        self.proporcao_slider = QSlider(Qt.Horizontal)
        self.proporcao_slider.setMinimum(10)
        self.proporcao_slider.setMaximum(90)
        self.proporcao_slider.setValue(30)  # 30% esquerda, 70% direita
        self.proporcao_slider.setTickPosition(QSlider.TicksBelow)
        self.proporcao_slider.setTickInterval(10)
        self.proporcao_value = QLabel("30/70%")
        self.proporcao_slider.valueChanged.connect(self.atualizar_proporcao_colunas)
        layout_avancado.addWidget(proporcao_label, 0, 0)
        layout_avancado.addWidget(self.proporcao_slider, 0, 1)
        layout_avancado.addWidget(self.proporcao_value, 0, 2)
        
        # Espaçamento entre linhas
        linha_spacing_label = QLabel("Espaço entre linhas:")
        self.linha_spacing_slider = QSlider(Qt.Horizontal)
        self.linha_spacing_slider.setMinimum(0)
        self.linha_spacing_slider.setMaximum(50)
        self.linha_spacing_slider.setValue(5)  # Valor atual
        self.linha_spacing_slider.setTickPosition(QSlider.TicksBelow)
        self.linha_spacing_slider.setTickInterval(5)
        self.linha_spacing_value = QLabel("5px")
        self.linha_spacing_slider.valueChanged.connect(self.atualizar_espacamento_linhas)
        layout_avancado.addWidget(linha_spacing_label, 1, 0)
        layout_avancado.addWidget(self.linha_spacing_slider, 1, 1)
        layout_avancado.addWidget(self.linha_spacing_value, 1, 2)
        
        # Altura da barra de progresso
        altura_progresso_label = QLabel("Altura da barra de progresso:")
        self.altura_progresso_slider = QSlider(Qt.Horizontal)
        self.altura_progresso_slider.setMinimum(10)
        self.altura_progresso_slider.setMaximum(50)
        self.altura_progresso_slider.setValue(20)  # Valor atual
        self.altura_progresso_slider.setTickPosition(QSlider.TicksBelow)
        self.altura_progresso_slider.setTickInterval(5)
        self.altura_progresso_value = QLabel("20px")
        self.altura_progresso_slider.valueChanged.connect(self.atualizar_altura_progresso)
        layout_avancado.addWidget(altura_progresso_label, 2, 0)
        layout_avancado.addWidget(self.altura_progresso_slider, 2, 1)
        layout_avancado.addWidget(self.altura_progresso_value, 2, 2)
        
        # Altura mínima do grupo de configurações
        altura_grupo_label = QLabel("Altura do grupo de config:")
        self.altura_grupo_slider = QSlider(Qt.Horizontal)
        self.altura_grupo_slider.setMinimum(200)
        self.altura_grupo_slider.setMaximum(600)
        self.altura_grupo_slider.setValue(300)  # Valor atual
        self.altura_grupo_slider.setTickPosition(QSlider.TicksBelow)
        self.altura_grupo_slider.setTickInterval(50)
        self.altura_grupo_value = QLabel("300px")
        self.altura_grupo_slider.valueChanged.connect(self.atualizar_altura_grupo)
        layout_avancado.addWidget(altura_grupo_label, 3, 0)
        layout_avancado.addWidget(self.altura_grupo_slider, 3, 1)
        layout_avancado.addWidget(self.altura_grupo_value, 3, 2)
        
        container_layout.addWidget(layout_group)
        
        # Botão para restaurar padrões
        restaurar_button = QPushButton("Restaurar Configurações Padrão")
        restaurar_button.clicked.connect(self.restaurar_configuracoes_padrao)
        restaurar_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                padding: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        container_layout.addWidget(restaurar_button)
        
        # Botão para salvar configuração atual
        salvar_button = QPushButton("Salvar Configuração Atual")
        salvar_button.clicked.connect(self.salvar_configuracao)
        salvar_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        container_layout.addWidget(salvar_button)
        
        # Adicionar espaçador para empurrar elementos para cima
        container_layout.addStretch()
        
        # Configurar o scroll area com o container
        scroll.setWidget(container)
        layout.addWidget(scroll)
        
    def escolher_cor(self, elemento):
        """Abre um seletor de cores e aplica a cor escolhida ao elemento especificado"""
        try:
            # Obter a cor atual do botão correspondente
            botoes_cor = {
                'background': self.bg_color_button,
                'controls': self.ctrl_color_button,
                'buttons': self.btn_color_button,
                'text': self.text_color_button,
                'highlight': self.highlight_color_button,
                'selection': self.selection_color_button,
                'hover': self.hover_color_button,
                'success': self.success_color_button,
                'error': self.error_color_button,
                'warning': self.warning_color_button,
                'border': self.border_color_button,
                'tab': self.tab_color_button,
                'progress': self.progress_color_button
            }
            
            # Obter a cor atual do botão
            botao = botoes_cor.get(elemento)
            if not botao:
                self.adicionar_log(f"Erro: elemento de cor desconhecido: {elemento}")
                return
                
            cor_atual = QColor(botao.styleSheet().split('background-color: ')[1].split(';')[0])
            
            # Abrir diálogo de cores
            cor = QColorDialog.getColor(cor_atual, self, "Escolha uma cor")
            if not cor.isValid():
                return
                
            # Atualizar o botão com a nova cor
            botao.setStyleSheet(f"background-color: {cor.name()};")
            
            # Aplicar a cor à interface
            metodos_aplicacao = {
                'background': self.aplicar_cor_fundo,
                'controls': self.aplicar_cor_controles,
                'buttons': self.aplicar_cor_botoes,
                'text': self.aplicar_cor_texto,
                'highlight': self.aplicar_cor_destaque,
                'selection': self.aplicar_cor_selecao,
                'hover': self.aplicar_cor_hover,
                'success': self.aplicar_cor_sucesso,
                'error': self.aplicar_cor_erro,
                'warning': self.aplicar_cor_aviso,
                'border': self.aplicar_cor_borda,
                'tab': self.aplicar_cor_abas,
                'progress': self.aplicar_cor_progresso
            }
            
            # Chamar o método correspondente para aplicar a cor
            metodo = metodos_aplicacao.get(elemento)
            if metodo:
                metodo(cor.name())
            else:
                self.adicionar_log(f"Erro: método de aplicação não encontrado para {elemento}")
        except Exception as e:
            self.adicionar_log(f"Erro ao escolher cor: {str(e)}")
    
    def aplicar_cor_fundo(self, cor):
        """Aplica a cor de fundo à interface"""
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background-color: {cor};
            }}
        """ + self.styleSheet())
        self.adicionar_log(f"Cor de fundo alterada para {cor}")
    
    def aplicar_cor_controles(self, cor):
        """Aplica a cor aos controles da interface"""
        # Aplicar a cor a todos os QSpinBox, QLineEdit, etc.
        novo_estilo = f"""
            QSpinBox, QLineEdit, QTextEdit, QComboBox {{
                background-color: {cor};
                border: 2px solid #aaaaaa;
            }}
        """
        self.setStyleSheet(self.styleSheet() + novo_estilo)
        self.adicionar_log(f"Cor dos controles alterada para {cor}")
    
    def aplicar_cor_botoes(self, cor):
        """Aplica a cor aos botões da interface"""
        # Aplicar a cor a todos os botões, exceto os especiais
        novo_estilo = f"""
            QPushButton {{
                background-color: {cor};
            }}
        """
        self.setStyleSheet(self.styleSheet() + novo_estilo)
        
        # Reconfigurar o botão de iniciar automação que é especial
        self.iniciar_automacao_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {cor};
                color: white;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.lighten_color(cor, 0.2)};
            }}
        """)
        self.adicionar_log(f"Cor dos botões alterada para {cor}")
    
    def aplicar_cor_texto(self, cor):
        """Aplica a cor do texto à interface"""
        novo_estilo = f"""
            QLabel, QPushButton, QCheckBox, QGroupBox, QSpinBox, QLineEdit, QTextEdit {{
                color: {cor};
            }}
        """
        self.setStyleSheet(self.styleSheet() + novo_estilo)
        self.adicionar_log(f"Cor do texto alterada para {cor}")
        
    def aplicar_cor_destaque(self, cor):
        """Aplica a cor de destaque a elementos selecionados da interface"""
        novo_estilo = f"""
            QTabBar::tab:selected {{
                background-color: {cor};
            }}
            QListWidget::item:selected {{
                background-color: {cor};
            }}
        """
        self.setStyleSheet(self.styleSheet() + novo_estilo)
        self.adicionar_log(f"Cor de destaque alterada para {cor}")
    
    def aplicar_cor_selecao(self, cor):
        """Aplica a cor de seleção aos elementos selecionáveis"""
        novo_estilo = f"""
            QListWidget::item:selected, QTableWidget::item:selected {{
                background-color: {cor};
                color: white;
            }}
        """
        self.setStyleSheet(self.styleSheet() + novo_estilo)
        self.adicionar_log(f"Cor de seleção alterada para {cor}")
    
    def aplicar_cor_hover(self, cor):
        """Aplica a cor de hover aos elementos interativos"""
        novo_estilo = f"""
            QPushButton:hover {{
                background-color: {cor};
            }}
            QTabBar::tab:hover {{
                background-color: {cor};
            }}
        """
        self.setStyleSheet(self.styleSheet() + novo_estilo)
        self.adicionar_log(f"Cor de hover alterada para {cor}")
    
    def aplicar_cor_sucesso(self, cor):
        """Aplica a cor de sucesso aos elementos da interface"""
        # Atualizar o botão de iniciar automação
        if hasattr(self, 'iniciar_automacao_button'):
            self.iniciar_automacao_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {cor};
                    color: white;
                    padding: 8px;
                    border-radius: 4px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {self.lighten_color(cor, 0.2)};
                }}
            """)
        self.adicionar_log(f"Cor de sucesso alterada para {cor}")
    
    def aplicar_cor_erro(self, cor):
        """Aplica a cor de erro aos elementos da interface"""
        novo_estilo = f"""
            QPushButton[error=true] {{
                background-color: {cor};
            }}
        """
        self.setStyleSheet(self.styleSheet() + novo_estilo)
        self.adicionar_log(f"Cor de erro alterada para {cor}")
    
    def aplicar_cor_aviso(self, cor):
        """Aplica a cor de aviso aos elementos da interface"""
        novo_estilo = f"""
            QPushButton[warning=true] {{
                background-color: {cor};
            }}
        """
        self.setStyleSheet(self.styleSheet() + novo_estilo)
        self.adicionar_log(f"Cor de aviso alterada para {cor}")
    
    def aplicar_cor_borda(self, cor):
        """Aplica a cor de borda aos elementos da interface"""
        novo_estilo = f"""
            QGroupBox, QLineEdit, QTextEdit, QSpinBox {{
                border: 1px solid {cor};
            }}
        """
        self.setStyleSheet(self.styleSheet() + novo_estilo)
        self.adicionar_log(f"Cor de borda alterada para {cor}")
    
    def aplicar_cor_abas(self, cor):
        """Aplica a cor das abas na interface"""
        novo_estilo = f"""
            QTabBar::tab {{
                background-color: {cor};
            }}
        """
        self.setStyleSheet(self.styleSheet() + novo_estilo)
        self.adicionar_log(f"Cor das abas alterada para {cor}")
    
    def aplicar_cor_progresso(self, cor):
        """Aplica a cor à barra de progresso"""
        if hasattr(self, 'barra_progresso'):
            self.barra_progresso.setStyleSheet(f"""
                QProgressBar {{
                    border: 1px solid #777777;
                    border-radius: 3px;
                    text-align: center;
                }}
                QProgressBar::chunk {{
                    background-color: {cor};
                    width: 10px;
                    margin: 0.5px;
                }}
            """)
        self.adicionar_log(f"Cor da barra de progresso alterada para {cor}")
    
    def aplicar_template(self, template_nome):
        """Aplica um template de cores predefinido à interface"""
        try:
            # Definição dos templates de cores
            templates = {
                'dark_pro': {
                    'background': '#1a1a2e',
                    'controls': '#16213e',
                    'buttons': '#0f3460',
                    'text': '#ffffff',
                    'highlight': '#2c3e50',
                    'selection': '#34495e',
                    'hover': '#4a6272',
                    'success': '#2ecc71',
                    'error': '#e74c3c',
                    'warning': '#f39c12',
                    'border': '#444444',
                    'tab': '#2c3e50',
                    'progress': '#3498db'
                },
                'teal_elegance': {
                    'background': '#004d40',
                    'controls': '#00695c',
                    'buttons': '#00796b',
                    'text': '#e0f2f1',
                    'highlight': '#009688',
                    'selection': '#26a69a',
                    'hover': '#4db6ac',
                    'success': '#00bfa5',
                    'error': '#f44336',
                    'warning': '#ffa000',
                    'border': '#b2dfdb',
                    'tab': '#00897b',
                    'progress': '#26a69a'
                },
                'purple_haze': {
                    'background': '#4a148c',
                    'controls': '#6a1b9a',
                    'buttons': '#7b1fa2',
                    'text': '#f3e5f5',
                    'highlight': '#9c27b0',
                    'selection': '#ab47bc',
                    'hover': '#ba68c8',
                    'success': '#66bb6a',
                    'error': '#ef5350',
                    'warning': '#ffc107',
                    'border': '#ce93d8',
                    'tab': '#8e24aa',
                    'progress': '#ab47bc'
                },
                'sunset_gold': {
                    'background': '#bf360c',
                    'controls': '#d84315',
                    'buttons': '#e64a19',
                    'text': '#fff8e1',
                    'highlight': '#ff5722',
                    'selection': '#ff7043',
                    'hover': '#ff8a65',
                    'success': '#4caf50',
                    'error': '#d32f2f',
                    'warning': '#ff9800',
                    'border': '#ffab91',
                    'tab': '#f4511e',
                    'progress': '#ff7043'
                },
                'ocean_blue': {
                    'background': '#01579b',
                    'controls': '#0277bd',
                    'buttons': '#0288d1',
                    'text': '#e1f5fe',
                    'highlight': '#039be5',
                    'selection': '#03a9f4',
                    'hover': '#29b6f6',
                    'success': '#00c853',
                    'error': '#d50000',
                    'warning': '#ffab00',
                    'border': '#81d4fa',
                    'tab': '#0288d1',
                    'progress': '#03a9f4'
                },
                'forest_green': {
                    'background': '#1b5e20',
                    'controls': '#2e7d32',
                    'buttons': '#388e3c',
                    'text': '#f1f8e9',
                    'highlight': '#43a047',
                    'selection': '#4caf50',
                    'hover': '#66bb6a',
                    'success': '#00e676',
                    'error': '#ff1744',
                    'warning': '#ffab00',
                    'border': '#a5d6a7',
                    'tab': '#388e3c',
                    'progress': '#4caf50'
                },
                'cherry_blossom': {
                    'background': '#880e4f',
                    'controls': '#ad1457',
                    'buttons': '#c2185b',
                    'text': '#fce4ec',
                    'highlight': '#d81b60',
                    'selection': '#e91e63',
                    'hover': '#ec407a',
                    'success': '#00c853',
                    'error': '#d50000',
                    'warning': '#ffab00',
                    'border': '#f48fb1',
                    'tab': '#c2185b',
                    'progress': '#ec407a'
                },
                'midnight': {
                    'background': '#000000',
                    'controls': '#0d47a1',
                    'buttons': '#1565c0',
                    'text': '#e3f2fd',
                    'highlight': '#1976d2',
                    'selection': '#1e88e5',
                    'hover': '#42a5f5',
                    'success': '#00c853',
                    'error': '#d50000',
                    'warning': '#ffab00',
                    'border': '#666666',
                    'tab': '#1565c0',
                    'progress': '#2196f3'
                },
                'classic_light': {
                    'background': '#f5f5f5',
                    'controls': '#e0e0e0',
                    'buttons': '#bdbdbd',
                    'text': '#212121',
                    'highlight': '#9e9e9e',
                    'selection': '#757575',
                    'hover': '#616161',
                    'success': '#4caf50',
                    'error': '#f44336',
                    'warning': '#ff9800',
                    'border': '#9e9e9e',
                    'tab': '#e0e0e0',
                    'progress': '#2196f3'
                },
                'neon_cyberpunk': {
                    'background': '#0d0221',
                    'controls': '#261447',
                    'buttons': '#530075',
                    'text': '#00ff9f',
                    'highlight': '#6f0fff',
                    'selection': '#9700cc',
                    'hover': '#bd00ff',
                    'success': '#00ff9f',
                    'error': '#ff124f',
                    'warning': '#ff00a0',
                    'border': '#fe75fe',
                    'tab': '#530075',
                    'progress': '#00ff9f'
                },
                'monochrome': {
                    'background': '#212121',
                    'controls': '#424242',
                    'buttons': '#616161',
                    'text': '#f5f5f5',
                    'highlight': '#757575',
                    'selection': '#9e9e9e',
                    'hover': '#bdbdbd',
                    'success': '#9e9e9e',
                    'error': '#9e9e9e',
                    'warning': '#9e9e9e',
                    'border': '#757575',
                    'tab': '#424242',
                    'progress': '#9e9e9e'
                },
                'royal_purple': {
                    'background': '#4a0072',
                    'controls': '#6a0dad',
                    'buttons': '#9c27b0',
                    'text': '#f3e5f5',
                    'highlight': '#aa00ff',
                    'selection': '#b388ff',
                    'hover': '#d1c4e9',
                    'success': '#00c853',
                    'error': '#ff1744',
                    'warning': '#ffab00',
                    'border': '#e1bee7',
                    'tab': '#9c27b0',
                    'progress': '#d500f9'
                }
            }
            
            # Verificar se o template existe
            if template_nome not in templates:
                self.adicionar_log(f"Template de cores '{template_nome}' não encontrado.")
                return
                
            # Obter as cores do template
            cores = templates[template_nome]
            
            # Atualizar os botões de cores na interface
            self.bg_color_button.setStyleSheet(f"background-color: {cores['background']};")
            self.ctrl_color_button.setStyleSheet(f"background-color: {cores['controls']};")
            self.btn_color_button.setStyleSheet(f"background-color: {cores['buttons']};")
            self.text_color_button.setStyleSheet(f"background-color: {cores['text']};")
            self.highlight_color_button.setStyleSheet(f"background-color: {cores['highlight']};")
            self.selection_color_button.setStyleSheet(f"background-color: {cores['selection']};")
            self.hover_color_button.setStyleSheet(f"background-color: {cores['hover']};")
            self.success_color_button.setStyleSheet(f"background-color: {cores['success']};")
            self.error_color_button.setStyleSheet(f"background-color: {cores['error']};")
            self.warning_color_button.setStyleSheet(f"background-color: {cores['warning']};")
            self.border_color_button.setStyleSheet(f"background-color: {cores['border']};")
            self.tab_color_button.setStyleSheet(f"background-color: {cores['tab']};")
            self.progress_color_button.setStyleSheet(f"background-color: {cores['progress']};")
            
            # Aplicar as cores à interface
            self.aplicar_cor_fundo(cores['background'])
            self.aplicar_cor_controles(cores['controls'])
            self.aplicar_cor_botoes(cores['buttons'])
            self.aplicar_cor_texto(cores['text'])
            self.aplicar_cor_destaque(cores['highlight'])
            self.aplicar_cor_selecao(cores['selection'])
            self.aplicar_cor_hover(cores['hover'])
            self.aplicar_cor_sucesso(cores['success'])
            self.aplicar_cor_erro(cores['error'])
            self.aplicar_cor_aviso(cores['warning'])
            self.aplicar_cor_borda(cores['border'])
            self.aplicar_cor_abas(cores['tab'])
            self.aplicar_cor_progresso(cores['progress'])
            
            self.adicionar_log(f"Template de cores '{template_nome}' aplicado com sucesso!")
            
        except Exception as e:
            self.adicionar_log(f"Erro ao aplicar template: {str(e)}")
    
    def lighten_color(self, color, factor=0.2):
        """Clareia uma cor hexadecimal pelo fator especificado"""
        try:
            # Converter a cor hexadecimal para RGB
            if color.startswith('#'):
                color = color[1:]
            rgb = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
            
            # Clarear cada componente
            rgb_claro = tuple(min(255, int(c + (255 - c) * factor)) for c in rgb)
            
            # Converter de volta para hexadecimal
            return f"#{rgb_claro[0]:02x}{rgb_claro[1]:02x}{rgb_claro[2]:02x}"
        except Exception as e:
            self.adicionar_log(f"Erro ao processar cor: {str(e)}")
            return color
    
    def atualizar_espacamento_vertical(self):
        """Atualiza o espaçamento vertical entre os campos"""
        try:
            valor = self.v_spacing_slider.value()
            self.v_spacing_value.setText(f"{valor}px")
            
            # Aplicar o novo espaçamento
            if hasattr(self, 'automacao_group') and self.automacao_group.layout():
                automacao_layout = self.automacao_group.layout()
                automacao_layout.setVerticalSpacing(valor)
                self.adicionar_log(f"Espaçamento vertical alterado para {valor}px")
        except Exception as e:
            self.adicionar_log(f"Erro ao atualizar espaçamento vertical: {str(e)}")
    
    def atualizar_espacamento_horizontal(self):
        """Atualiza o espaçamento horizontal entre os campos"""
        try:
            valor = self.h_spacing_slider.value()
            self.h_spacing_value.setText(f"{valor}px")
            
            # Aplicar o novo espaçamento
            if hasattr(self, 'automacao_group') and self.automacao_group.layout():
                automacao_layout = self.automacao_group.layout()
                automacao_layout.setHorizontalSpacing(valor)
                self.adicionar_log(f"Espaçamento horizontal alterado para {valor}px")
        except Exception as e:
            self.adicionar_log(f"Erro ao atualizar espaçamento horizontal: {str(e)}")
    
    def atualizar_margens(self):
        """Atualiza as margens internas dos grupos"""
        try:
            valor = self.margin_slider.value()
            self.margin_value.setText(f"{valor}px")
            
            # Aplicar as novas margens
            if hasattr(self, 'automacao_group') and self.automacao_group.layout():
                automacao_layout = self.automacao_group.layout()
                automacao_layout.setContentsMargins(valor, valor, valor, valor)
                self.adicionar_log(f"Margens internas alteradas para {valor}px")
        except Exception as e:
            self.adicionar_log(f"Erro ao atualizar margens: {str(e)}")
    
    def atualizar_altura_campos(self):
        """Atualiza a altura dos campos de entrada"""
        try:
            valor = self.altura_campos_slider.value()
            self.altura_campos_value.setText(f"{valor}px")
            
            # Aplicar a nova altura aos campos
            if hasattr(self, 'acoes_spinbox'):
                self.acoes_spinbox.setFixedHeight(valor)
            if hasattr(self, 'perfis_simult_spinbox'):
                self.perfis_simult_spinbox.setFixedHeight(valor)
            if hasattr(self, 'tempo_acoes_spinbox'):
                self.tempo_acoes_spinbox.setFixedHeight(valor)
            self.adicionar_log(f"Altura dos campos alterada para {valor}px")
        except Exception as e:
            self.adicionar_log(f"Erro ao atualizar altura dos campos: {str(e)}")
    
    def atualizar_tamanho_fonte(self):
        """Atualiza o tamanho da fonte dos campos de entrada"""
        try:
            valor = self.tamanho_fonte_slider.value()
            self.tamanho_fonte_value.setText(f"{valor}pt")
            
            # Aplicar o novo tamanho de fonte aos campos
            novo_estilo = f"font-size: {valor}pt; font-weight: bold; color: white; background-color: #666666; border: 2px solid #aaaaaa;"
            if hasattr(self, 'acoes_spinbox'):
                self.acoes_spinbox.setStyleSheet(novo_estilo)
            if hasattr(self, 'perfis_simult_spinbox'):
                self.perfis_simult_spinbox.setStyleSheet(novo_estilo)
            if hasattr(self, 'tempo_acoes_spinbox'):
                self.tempo_acoes_spinbox.setStyleSheet(novo_estilo)
            self.adicionar_log(f"Tamanho da fonte alterado para {valor}pt")
        except Exception as e:
            self.adicionar_log(f"Erro ao atualizar tamanho da fonte: {str(e)}")
    
    def atualizar_largura_rotulos(self):
        """Atualiza a largura dos rótulos (labels) na interface"""
        try:
            valor = self.largura_rotulos_slider.value()
            self.largura_rotulos_value.setText(f"{valor}px")
            
            # Encontrar todos os QLabels nas áreas de configuração
            if hasattr(self, 'automacao_group'):
                for widget in self.automacao_group.findChildren(QLabel):
                    widget.setMinimumWidth(valor)
                    widget.setMaximumWidth(valor)
            
            self.adicionar_log(f"Largura dos rótulos alterada para {valor}px")
        except Exception as e:
            self.adicionar_log(f"Erro ao atualizar largura dos rótulos: {str(e)}")
    
    def atualizar_proporcao_colunas(self):
        """Atualiza a proporção entre as colunas (esquerda/direita)"""
        try:
            valor = self.proporcao_slider.value()
            self.proporcao_value.setText(f"{valor}/{100-valor}%")
            
            # Atualizar o splitter entre as colunas
            if hasattr(self, 'tab_automacao'):
                # Procurar o splitter na tab de automação
                splitters = self.tab_automacao.findChildren(QSplitter)
                if splitters and len(splitters) > 0:
                    splitter = splitters[0]
                    # Calcular as dimensões do splitter na proporção definida
                    largura_total = splitter.width()
                    nova_largura_esq = int(largura_total * valor / 100)
                    nova_largura_dir = largura_total - nova_largura_esq
                    splitter.setSizes([nova_largura_esq, nova_largura_dir])
            
            self.adicionar_log(f"Proporção das colunas alterada para {valor}/{100-valor}%")
        except Exception as e:
            self.adicionar_log(f"Erro ao atualizar proporção das colunas: {str(e)}")
    
    def atualizar_espacamento_linhas(self):
        """Atualiza o espaçamento entre linhas na interface"""
        try:
            valor = self.linha_spacing_slider.value()
            self.linha_spacing_value.setText(f"{valor}px")
            
            # Aplicar o novo espaçamento às listagens e áreas de texto
            if hasattr(self, 'lista_perfis'):
                self.lista_perfis.setStyleSheet(f"QListWidget::item {{ padding: {valor}px; }}")
            
            if hasattr(self, 'status_text'):
                self.status_text.setStyleSheet(f"QTextEdit {{ line-height: {100 + valor}%; }}")
                
            self.adicionar_log(f"Espaçamento entre linhas alterado para {valor}px")
        except Exception as e:
            self.adicionar_log(f"Erro ao atualizar espaçamento entre linhas: {str(e)}")
    
    def atualizar_altura_progresso(self):
        """Atualiza a altura da barra de progresso"""
        try:
            valor = self.altura_progresso_slider.value()
            self.altura_progresso_value.setText(f"{valor}px")
            
            # Aplicar a nova altura à barra de progresso
            if hasattr(self, 'barra_progresso'):
                self.barra_progresso.setFixedHeight(valor)
                
            self.adicionar_log(f"Altura da barra de progresso alterada para {valor}px")
        except Exception as e:
            self.adicionar_log(f"Erro ao atualizar altura da barra de progresso: {str(e)}")
    
    def atualizar_altura_grupo(self):
        """Atualiza a altura mínima do grupo de configurações"""
        try:
            valor = self.altura_grupo_slider.value()
            self.altura_grupo_value.setText(f"{valor}px")
            
            # Aplicar a nova altura ao grupo de configurações
            if hasattr(self, 'automacao_group'):
                self.automacao_group.setMinimumHeight(valor)
                
            self.adicionar_log(f"Altura do grupo de configurações alterada para {valor}px")
        except Exception as e:
            self.adicionar_log(f"Erro ao atualizar altura do grupo: {str(e)}")
    
    def restaurar_configuracoes_padrao(self):
        """Restaura todas as configurações para os valores padrão"""
        try:
            # Restaurar cores
            self.bg_color_button.setStyleSheet("background-color: #333333;")
            self.ctrl_color_button.setStyleSheet("background-color: #555555;")
            self.btn_color_button.setStyleSheet("background-color: #27ae60;")
            self.text_color_button.setStyleSheet("background-color: white;")
            
            # Restaurar espaçamentos
            self.v_spacing_slider.setValue(60)
            self.h_spacing_slider.setValue(50)
            self.margin_slider.setValue(30)
            
            # Restaurar tamanhos
            self.altura_campos_slider.setValue(60)
            self.tamanho_fonte_slider.setValue(20)
            
            # Restaurar configurações de layout avançado
            if hasattr(self, 'largura_rotulos_slider'):
                self.largura_rotulos_slider.setValue(150)
            if hasattr(self, 'proporcao_slider'):
                self.proporcao_slider.setValue(30)
            if hasattr(self, 'linha_spacing_slider'):
                self.linha_spacing_slider.setValue(5)
            if hasattr(self, 'altura_progresso_slider'):
                self.altura_progresso_slider.setValue(20)
            if hasattr(self, 'altura_grupo_slider'):
                self.altura_grupo_slider.setValue(300)
            
            # Aplicar todas as configurações padrão
            self.aplicar_cor_fundo("#333333")
            self.aplicar_cor_controles("#555555")
            self.aplicar_cor_botoes("#27ae60")
            self.aplicar_cor_texto("white")
            self.atualizar_espacamento_vertical()
            self.atualizar_espacamento_horizontal()
            self.atualizar_margens()
            self.atualizar_altura_campos()
            self.atualizar_tamanho_fonte()
            
            # Aplicar configurações avançadas
            if hasattr(self, 'atualizar_largura_rotulos'):
                self.atualizar_largura_rotulos()
            if hasattr(self, 'atualizar_proporcao_colunas'):
                self.atualizar_proporcao_colunas()
            if hasattr(self, 'atualizar_espacamento_linhas'):
                self.atualizar_espacamento_linhas()
            if hasattr(self, 'atualizar_altura_progresso'):
                self.atualizar_altura_progresso()
            if hasattr(self, 'atualizar_altura_grupo'):
                self.atualizar_altura_grupo()
            
            self.adicionar_log("Configurações restauradas para valores padrão")
        except Exception as e:
            self.adicionar_log(f"Erro ao restaurar configurações: {str(e)}")
    
    def salvar_configuracao(self):
        """Salva a configuração atual em um arquivo JSON"""
        try:
            config = {
                "cores": {
                    "fundo": self.bg_color_button.styleSheet().split('background-color: ')[1].split(';')[0],
                    "controles": self.ctrl_color_button.styleSheet().split('background-color: ')[1].split(';')[0],
                    "botoes": self.btn_color_button.styleSheet().split('background-color: ')[1].split(';')[0],
                    "texto": self.text_color_button.styleSheet().split('background-color: ')[1].split(';')[0],
                    "highlight": self.highlight_color_button.styleSheet().split('background-color: ')[1].split(';')[0],
                    "selection": self.selection_color_button.styleSheet().split('background-color: ')[1].split(';')[0],
                    "hover": self.hover_color_button.styleSheet().split('background-color: ')[1].split(';')[0],
                    "success": self.success_color_button.styleSheet().split('background-color: ')[1].split(';')[0],
                    "error": self.error_color_button.styleSheet().split('background-color: ')[1].split(';')[0],
                    "warning": self.warning_color_button.styleSheet().split('background-color: ')[1].split(';')[0],
                    "border": self.border_color_button.styleSheet().split('background-color: ')[1].split(';')[0],
                    "tab": self.tab_color_button.styleSheet().split('background-color: ')[1].split(';')[0],
                    "progress": self.progress_color_button.styleSheet().split('background-color: ')[1].split(';')[0]
                },
                "espacamentos": {
                    "vertical": self.v_spacing_slider.value(),
                    "horizontal": self.h_spacing_slider.value(),
                    "margens": self.margin_slider.value()
                },
                "tamanhos": {
                    "altura_campos": self.altura_campos_slider.value(),
                    "tamanho_fonte": self.tamanho_fonte_slider.value()
                }
            }
            
            # Salvar em um arquivo
            with open('configuracao_interface.json', 'w') as f:
                json.dump(config, f, indent=4)
                
            self.adicionar_log("Configuração salva com sucesso!")
            QMessageBox.information(self, "Configuração Salva", "As configurações de personalização foram salvas com sucesso.")
        except Exception as e:
            self.adicionar_log(f"Erro ao salvar configuração: {str(e)}")
            QMessageBox.warning(self, "Erro", f"Ocorreu um erro ao salvar a configuração: {str(e)}")
            
    def carregar_configuracao(self):
        """Carrega a configuração salva a partir de um arquivo JSON"""
        try:
            arquivo_config = 'configuracao_interface.json'
            
            # Verificar se o arquivo existe
            if not os.path.exists(arquivo_config):
                self.adicionar_log("Nenhuma configuração salva encontrada. Usando valores padrão.")
                return False
                
            # Carregar arquivo
            with open(arquivo_config, 'r') as f:
                config = json.load(f)
                
            # Aplicar configurações de cores
            if "cores" in config:
                # Atualizar os botões de cores
                cores = config["cores"]
                
                # Cores principais
                if "fundo" in cores:
                    self.bg_color_button.setStyleSheet(f"background-color: {cores['fundo']};")
                    self.aplicar_cor_fundo(cores['fundo'])
                    
                if "controles" in cores:
                    self.ctrl_color_button.setStyleSheet(f"background-color: {cores['controles']};")
                    self.aplicar_cor_controles(cores['controles'])
                    
                if "botoes" in cores:
                    self.btn_color_button.setStyleSheet(f"background-color: {cores['botoes']};")
                    self.aplicar_cor_botoes(cores['botoes'])
                    
                if "texto" in cores:
                    self.text_color_button.setStyleSheet(f"background-color: {cores['texto']};")
                    self.aplicar_cor_texto(cores['texto'])
                
                # Cores adicionais
                if "highlight" in cores:
                    self.highlight_color_button.setStyleSheet(f"background-color: {cores['highlight']};")
                    self.aplicar_cor_destaque(cores['highlight'])
                    
                if "selection" in cores:
                    self.selection_color_button.setStyleSheet(f"background-color: {cores['selection']};")
                    self.aplicar_cor_selecao(cores['selection'])
                    
                if "hover" in cores:
                    self.hover_color_button.setStyleSheet(f"background-color: {cores['hover']};")
                    self.aplicar_cor_hover(cores['hover'])
                    
                if "success" in cores:
                    self.success_color_button.setStyleSheet(f"background-color: {cores['success']};")
                    self.aplicar_cor_sucesso(cores['success'])
                    
                if "error" in cores:
                    self.error_color_button.setStyleSheet(f"background-color: {cores['error']};")
                    self.aplicar_cor_erro(cores['error'])
                    
                if "warning" in cores:
                    self.warning_color_button.setStyleSheet(f"background-color: {cores['warning']};")
                    self.aplicar_cor_aviso(cores['warning'])
                    
                if "border" in cores:
                    self.border_color_button.setStyleSheet(f"background-color: {cores['border']};")
                    self.aplicar_cor_borda(cores['border'])
                    
                if "tab" in cores:
                    self.tab_color_button.setStyleSheet(f"background-color: {cores['tab']};")
                    self.aplicar_cor_abas(cores['tab'])
                    
                if "progress" in cores:
                    self.progress_color_button.setStyleSheet(f"background-color: {cores['progress']};")
                    self.aplicar_cor_progresso(cores['progress'])
            
            # Aplicar configurações de espaçamentos
            if "espacamentos" in config:
                espacamentos = config["espacamentos"]
                if "vertical" in espacamentos:
                    self.v_spacing_slider.setValue(espacamentos["vertical"])
                if "horizontal" in espacamentos:
                    self.h_spacing_slider.setValue(espacamentos["horizontal"])
                if "margens" in espacamentos:
                    self.margin_slider.setValue(espacamentos["margens"])
                
            # Aplicar configurações de tamanhos
            if "tamanhos" in config:
                tamanhos = config["tamanhos"]
                if "altura_campos" in tamanhos:
                    self.altura_campos_slider.setValue(tamanhos["altura_campos"])
                if "tamanho_fonte" in tamanhos:
                    self.tamanho_fonte_slider.setValue(tamanhos["tamanho_fonte"])
                    
            self.adicionar_log("Configuração carregada com sucesso!")
            return True
            
        except Exception as e:
            self.adicionar_log(f"Erro ao carregar configuração: {str(e)}")
            return False
    
    def ativar_modo_selecao_cores(self, estado):
        """Ativa ou desativa o modo de seleção de cores por clique"""
        try:
            self.modo_selecao_cores_ativo = (estado == Qt.Checked)
            
            # Desativar outros modos de seleção se este estiver ativo
            if self.modo_selecao_cores_ativo:
                self.adicionar_log("Modo de seleção direta de cores ativado! Clique em qualquer elemento da interface.")
                self.setCursor(Qt.CrossCursor)  # Muda o cursor para uma cruz
                
                # Instalar filtro de eventos para capturar cliques do mouse
                self.installEventFilter(self)
            else:
                self.adicionar_log("Modo de seleção direta de cores desativado.")
                self.setCursor(Qt.ArrowCursor)  # Restaura o cursor normal
                
                # Remover filtro de eventos
                self.removeEventFilter(self)
        except Exception as e:
            self.adicionar_log(f"Erro ao ativar modo de seleção de cores: {str(e)}")
    
    def eventFilter(self, obj, event):
        """Filtro de eventos para capturar cliques do mouse quando o modo de seleção de cores está ativo"""
        try:
            if self.modo_selecao_cores_ativo and event.type() == event.MouseButtonPress:
                # Capturar a posição do clique
                pos = event.pos()
                
                # Descobrir qual elemento foi clicado
                widget = self.childAt(pos)
                if widget:
                    # Abrir o seletor de cores
                    self.selecionar_cor_para_widget(widget)
                    
                    # Consumir o evento para que ele não continue a propagação normal
                    return True
        except Exception as e:
            self.adicionar_log(f"Erro ao processar evento de clique: {str(e)}")
            
        # Deixar que outros eventos sejam processados normalmente
        return super().eventFilter(obj, event)
    
    def selecionar_cor_para_widget(self, widget):
        """Abre um seletor de cores para o widget clicado"""
        try:
            # Verificar se o widget tem estilo definido
            estilo_atual = widget.styleSheet()
            
            # Tentar extrair a cor de fundo atual se existir
            cor_atual = QColor("#333333")  # Cor padrão
            try:
                if "background-color:" in estilo_atual:
                    cor_bg = estilo_atual.split("background-color:")[1].split(";")[0].strip()
                    cor_atual = QColor(cor_bg)
                elif "background:" in estilo_atual:
                    cor_bg = estilo_atual.split("background:")[1].split(";")[0].strip()
                    if "#" in cor_bg:
                        cor_atual = QColor(cor_bg.split("#")[1].split(" ")[0].strip())
            except:
                pass
            
            # Abrir o seletor de cores
            cor = QColorDialog.getColor(cor_atual, self, f"Escolha a cor para {widget.__class__.__name__}")
            if not cor.isValid():
                return
                
            # Aplicar a nova cor ao widget
            nome_classe = widget.__class__.__name__
            widget_info = f"{nome_classe}"
            
            if hasattr(widget, 'text'):
                try:
                    texto = widget.text()
                    if texto:
                        widget_info += f" - '{texto}'"
                except:
                    pass
            
            # Aplicar a cor ao widget
            novo_estilo = estilo_atual
            if "background-color:" in estilo_atual:
                novo_estilo = re.sub(r'background-color:[^;]+;', f"background-color: {cor.name()};" , estilo_atual)
            else:
                novo_estilo = f"background-color: {cor.name()};" + estilo_atual
                
            widget.setStyleSheet(novo_estilo)
            self.adicionar_log(f"Cor {cor.name()} aplicada ao elemento {widget_info}")
        except Exception as e:
            self.adicionar_log(f"Erro ao selecionar cor para widget: {str(e)}")
    
    def closeEvent(self, event):
        """Manipulador para o evento de fechamento da janela"""
        if self.automacao_em_execucao:
            # Perguntar ao usuário se deseja realmente sair
            confirmar = QMessageBox.question(
                self, 
                "Automação em andamento", 
                "Existe uma automação em andamento. Deseja realmente sair?\nTodas as operações serão interrompidas.", 
                QMessageBox.Yes | QMessageBox.No
            )
            
            if confirmar == QMessageBox.Yes:
                # Parar todos os workers antes de sair
                if self.automacao_worker:
                    self.automacao_worker.stop()
                    
                # Fechar todos os navegadores abertos
                for perfil, driver in self.dolphin_manager.profile_drivers.items():
                    try:
                        driver.quit()
                    except:
                        pass
                        
                event.accept()
            else:
                event.ignore()
        else:
            # Se não há automação em andamento, simplesmente fecha
            event.accept()
