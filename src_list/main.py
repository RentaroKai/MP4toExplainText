import sys
from PySide6.QtWidgets import QApplication
from src_list.ui.main_window import MainWindow

def main():
    """
    モーションリスト管理アプリケーションのメインエントリーポイント
    """
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 