import json
import os
from pathlib import Path

class ConfigManager:
    """アプリケーションの設定を管理するクラス"""
    
    def __init__(self):
        self.config_dir = Path("config")
        self.paths_file = self.config_dir / "paths.json"
        self.config_file = self.config_dir / "config.json"
        
        # 設定ディレクトリが存在しない場合は作成
        if not self.config_dir.exists():
            self.config_dir.mkdir(parents=True)
        
        # 設定の読み込み
        self._paths = self._load_json(self.paths_file)
        self._config = self._load_json(self.config_file)
    
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
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
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