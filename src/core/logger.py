import logging
import os
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler
from core.config_manager import ConfigManager

def setup_logger():
    """アプリケーション全体のロガーを設定"""
    config = ConfigManager()
    paths = config.get_paths()
    
    # ログディレクトリの作成
    log_dir = Path(paths["log_dir"])
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # ログファイル名の設定（日付ごと）
    log_file = log_dir / f"motion_tag_{datetime.now().strftime('%Y%m%d')}.log"
    
    # ロガーの基本設定
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # フォーマッターの作成
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # ファイルハンドラーの設定
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    
    # コンソールハンドラーの設定
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # ハンドラーの追加
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    logger.info("ロガーの初期化が完了しました") 