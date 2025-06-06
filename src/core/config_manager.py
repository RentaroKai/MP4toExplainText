import json
import os
import logging
from pathlib import Path
from typing import Dict, Any

class ConfigManager:
    """
    アプリケーションの設定を管理するクラス
    
    変更点:
    - 設定更新メソッドの追加（update_config）
    - 最近使用したデータベースの管理機能
    - アクティブなデータベースパスの記憶機能
    """
    
    def __init__(self):
        """初期化"""
        self.logger = logging.getLogger(__name__)
        
        # 基本ディレクトリ構造を設定
        self.base_dir = Path.home() / "MP4toExplainText"
        self.data_dir = Path(__file__).parent.parent.parent / "data"
        self.config_dir = self.data_dir / "config"
        
        # 設定ファイルのパス
        self.config_file = self.config_dir / "config.json"
        
        # 設定ディレクトリが存在しない場合は作成
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # 設定ファイルが存在しない場合はデフォルト設定を作成
        if not self.config_file.exists():
            default_config = {
                "active_database": str(self.data_dir / "db" / "abab.db"),
                "recent_databases": [],
                "ui": {
                    "theme": "light",
                    "font_size": 12
                },
                "performance": {
                    "batch_size": 5
                },
                "cleanup": {
                    "auto_delete_temp": True
                },
                "api": {
                    "use_default_cert": True
                }
            }
            self._save_json(self.config_file, default_config)
        
        # 設定を読み込み
        self._config = self._load_json(self.config_file)
        
        self.paths_file = self.config_dir / "paths.json"
        
        # パス設定ファイルが存在しない場合はデフォルト設定を作成
        if not self.paths_file.exists():
            default_paths = {
                "db_path": str(self.data_dir / "db" / "abab.db"),
                "export_path": str(self.data_dir / "exports"),
                "temp_path": str(self.data_dir / "temp"),
                "log_path": str(self.data_dir / "logs")
            }
            self._save_json(self.paths_file, default_paths)
        
        # パス設定を読み込み
        self._paths = self._load_json(self.paths_file)
        
        # 設定が空の場合はデフォルト値を設定
        if not self._config:
            self._config = {
                "recent_databases": [],
                "active_database": None
            }
            self._save_json(self.config_file, self._config)
    
    def _load_json(self, file_path: Path) -> dict:
        """JSONファイルを読み込む"""
        try:
            if not file_path.exists():
                return {}
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"設定ファイルの読み込みに失敗しました: {file_path} - {str(e)}")
            return {}
    
    def _save_json(self, file_path: Path, data: dict):
        """JSONファイルを保存する"""
        try:
            self.logger.debug(f"JSONファイル保存開始: {file_path}")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            self.logger.debug(f"JSONファイル保存完了")
        except Exception as e:
            self.logger.error(f"JSONファイル保存エラー: {file_path} - {str(e)}")
            raise Exception(f"設定ファイルの保存に失敗しました: {file_path} - {str(e)}")
    
    def get_paths(self) -> dict:
        """パス設定を取得"""
        return self._paths
    
    def get_config(self) -> dict:
        """アプリケーション設定を取得"""
        return self._config
    
    def get_api_config(self) -> dict:
        """API関連の設定を取得"""
        return self._config.get("api", {})
    
    def update_config(self, new_config: dict):
        """
        アプリケーション設定を更新
        
        Args:
            new_config: 新しい設定データ
        """
        self.logger.debug(f"設定更新開始: {new_config}")
        self._config = new_config
        try:
            self._save_json(self.config_file, self._config)
            self.logger.debug(f"設定ファイルを保存しました: {self.config_file}")
        except Exception as e:
            self.logger.error(f"設定更新中にエラーが発生しました: {str(e)}", exc_info=True)
    
    def get_recent_databases(self) -> list:
        """最近使用したデータベースのリストを取得"""
        recent_dbs = self._config.get("recent_databases", [])
        self.logger.debug(f"get_recent_databases: {recent_dbs}")
        return recent_dbs
    
    def set_active_database(self, db_path: str):
        """
        現在アクティブなデータベースを設定
        
        Args:
            db_path: データベースファイルのパス
        """
        self.logger.debug(f"アクティブデータベース設定: {db_path}")
        # 現在の設定を再読み込みして最新の状態を取得
        self._config = self._load_json(self.config_file)
        # active_databaseのみを更新
        self._config["active_database"] = db_path
        # 更新した設定を保存
        self._save_json(self.config_file, self._config)
        self.logger.debug(f"アクティブデータベース設定完了、最近使用したDBリスト: {self._config.get('recent_databases', [])}")
    
    def get_active_database(self) -> str:
        """
        現在アクティブなデータベースのパスを取得
        
        Returns:
            str: データベースファイルのパス、設定されていない場合はデフォルトのパス
        """
        active_db = self._config.get("active_database")
        if active_db:
            return active_db
        return self._paths.get("db_path")
    
    def get_ui_config(self) -> dict:
        """UI関連の設定を取得"""
        return self._config.get("ui", {})
    
    def get_performance_config(self) -> dict:
        """パフォーマンス関連の設定を取得"""
        return self._config.get("performance", {})
    
    def get_cleanup_config(self) -> dict:
        """クリーンアップ関連の設定を取得"""
        return self._config.get("cleanup", {})
    
    def get_api_key(self) -> str:
        """APIキーを取得
        
        環境変数 GOOGLE_API_KEY が設定されている場合は、それを優先して返します。
        環境変数が設定されていない場合は、設定ファイルから読み込みます。
        
        Returns:
            str: APIキー
        """
        # 環境変数を優先
        env_api_key = os.getenv("GOOGLE_API_KEY")
        if env_api_key:
            return env_api_key
        
        # 環境変数がない場合は設定ファイルから
        api_key = self._config.get("api_key", "")
        if not api_key:
            self.logger.warning("APIキーが設定されていません。環境変数 'GOOGLE_API_KEY' を設定するか、設定画面から入力してください。")
        return api_key
    
    def set_api_key(self, api_key: str):
        """APIキーを設定
        
        Note:
            このメソッドは設定ファイルにのみ保存します。
            環境変数 GOOGLE_API_KEY が設定されている場合、get_api_key() は
            環境変数の値を優先して返すため、このメソッドでの設定は反映されません。
        
        Args:
            api_key (str): 設定するAPIキー
        """
        # APIキーを暗号化して保存（実際のプロダクションでは適切な暗号化が必要）
        self._config["api_key"] = api_key
        self._save_json(self.config_file, self._config)
        self.logger.info("APIキーを設定ファイルに保存しました")
    
    def get_model_name(self) -> str:
        """Get the configured Gemini model name by reloading config file, fallback to default."""
        # Reload configuration to reflect any updates
        config_data = self._load_json(self.config_file)
        api_conf = config_data.get("api", {})
        model_name = api_conf.get("model_name")
        if model_name:
            return model_name
        default_model = "gemini-2.5-pro-preview-05-06"
        self.logger.info(f"No model_name in config, using default: {default_model}")
        return default_model

    def set_model_name(self, model_name: str):
        """Set the Gemini model name in config."""
        if "api" not in self._config or not isinstance(self._config.get("api"), dict):
            self._config["api"] = {}
        self._config["api"]["model_name"] = model_name
        self._save_json(self.config_file, self._config)
        self.logger.info(f"Gemini model name set to: {model_name}") 