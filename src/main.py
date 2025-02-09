import sys
import os
import logging
from pathlib import Path

# プロジェクトのルートディレクトリをPYTHONPATHに追加
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from PySide6.QtWidgets import QApplication
from src.ui.main_window import MainWindow
from src.core.config_manager import ConfigManager
from src.core.logger import setup_logger

def init_directories():
    """必要なディレクトリ構造を初期化"""
    config = ConfigManager()
    paths = config.get_paths()
    
    # データベースファイルのパスを除外
    for key, path in paths.items():
        if key != "db_path":  # データベースファイルは除外
            Path(path).mkdir(parents=True, exist_ok=True)
        else:  # データベースファイルの親ディレクトリは作成
            Path(path).parent.mkdir(parents=True, exist_ok=True)

def main():
    # ロガーのセットアップ
    setup_logger()
    logger = logging.getLogger(__name__)
    
    try:
        # 必要なディレクトリの初期化
        init_directories()
        
        # アプリケーションの作成
        app = QApplication(sys.argv)
        
        # メインウィンドウの作成
        window = MainWindow()
        window.show()
        
        # アプリケーションの実行
        sys.exit(app.exec())
        
    except Exception as e:
        logger.error(f"アプリケーション起動中にエラーが発生しました: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main() 