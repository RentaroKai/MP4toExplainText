import sys
import os
from pathlib import Path

# プロジェクトのルートディレクトリをPYTHONPATHに追加
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

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