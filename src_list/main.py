import sys
import os
from pathlib import Path
import argparse

# プロジェクトのルートディレクトリをPYTHONPATHに追加
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from PySide6.QtWidgets import QApplication
from src_list.ui.main_window import MainWindow

def parse_args():
    """
    コマンドライン引数をパースする
    """
    parser = argparse.ArgumentParser(description='モーションリスト管理アプリケーション')
    parser.add_argument('--db-path', type=str, help='使用するデータベースファイルのパス')
    return parser.parse_args()

def main():
    """
    モーションリスト管理アプリケーションのメインエントリーポイント
    """
    args = parse_args()
    app = QApplication(sys.argv)
    window = MainWindow(db_path=args.db_path)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 