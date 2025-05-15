import sys
from PyQt5.QtWidgets import QApplication

# Importa a classe da interface gráfica do arquivo gui.py
from gui import BotComentariosInterface

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Cria uma instância da nossa interface
    janela_principal = BotComentariosInterface()
    janela_principal.show()

    # Inicia o loop de eventos da aplicação
    sys.exit(app.exec_())
