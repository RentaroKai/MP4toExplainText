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
    log_dir = Path(paths["log_path"])
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # ログファイル名の設定（日付ごと）
    log_file = log_dir / f"motion_tag_{datetime.now().strftime('%Y%m%d')}.log"
    
    # ロガーの基本設定
    logging.basicConfig(
        level=logging.DEBUG,  # DEBUGレベルに変更
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),  # コンソール出力
            RotatingFileHandler(
                log_file, 
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5
            )
        ]
    )
    
    # ルートロガーを取得
    root_logger = logging.getLogger()
    root_logger.info("ロガーの初期化が完了しました") 