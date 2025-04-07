from pathlib import Path
import json
import logging
from typing import Dict, List, Optional

class PromptManager:
    """プロンプト設定を管理するクラス"""
    
    def __init__(self, config_dir: Path = Path("config/prompts")):
        self.logger = logging.getLogger(__name__)
        self.config_dir = config_dir
        self.current_config: Optional[Dict] = None
        
        # 設定ディレクトリが存在しない場合は作成
        if not self.config_dir.exists():
            self.config_dir.mkdir(parents=True)
    
    def get_available_configs(self) -> List[str]:
        """利用可能な設定ファイルの一覧を取得"""
        try:
            return [f.stem for f in self.config_dir.glob("*.json")]
        except Exception as e:
            self.logger.error(f"設定ファイルの一覧取得に失敗: {str(e)}")
            return []
    
    def get_config_path(self, config_name: str) -> Optional[Path]:
        """指定された設定名のファイルパスを取得する"""
        if not config_name:
            self.logger.warning("設定名が空です。")
            return None
        try:
            path = self.config_dir / f"{config_name}.json"
            return path
        except Exception as e:
            self.logger.error(f"設定パスの取得中にエラー: {str(e)}")
            return None
    
    def load_config(self, config_name: str = "default") -> Dict:
        """指定された設定ファイルを読み込む"""
        try:
            config_path = self.config_dir / f"{config_name}.json"
            if not config_path.exists():
                if config_name == "default":
                    self.logger.warning("デフォルト設定が見つかりません")
                    return {}
                else:
                    self.logger.error(f"設定ファイルが見つかりません: {config_name}")
                    return self.load_config("default")
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            if self._validate_config(config):
                self.current_config = config
                return config
            else:
                self.logger.error(f"設定ファイルの形式が不正: {config_name}")
                return self.load_config("default") if config_name != "default" else {}
                
        except Exception as e:
            self.logger.error(f"設定ファイルの読み込みに失敗: {str(e)}")
            return {}
    
    def _validate_config(self, config: Dict) -> bool:
        """設定ファイルの形式を検証"""
        try:
            # 必須のトップレベルキーをチェック
            if "fields" not in config:
                self.logger.error("設定ファイルに 'fields' キーがありません")
                return False
            
            # 各フィールドの形式をチェック
            for field_name, field_config in config["fields"].items():
                if not all(key in field_config for key in ["description", "type", "required"]):
                    self.logger.error(f"フィールド '{field_name}' に必須キーが不足しています")
                    return False
                
                # オプションフィールドの形式をチェック
                if "options" in field_config and not isinstance(field_config["options"], list):
                    self.logger.error(f"フィールド '{field_name}' の options が配列ではありません")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"設定ファイルの検証中にエラー: {str(e)}")
            return False
    
    def get_current_config(self) -> Dict:
        """現在読み込まれている設定を取得"""
        return self.current_config or self.load_config("default")
    
    def generate_prompt(self, video_path: str) -> str:
        """プロンプトを生成"""
        config = self.get_current_config()
        if not config:
            self.logger.error("設定が読み込まれていません")
            return ""
        
        # ファイル名を抽出
        video_file = Path(video_path)
        file_name = video_file.name  # 拡張子付きファイル名
        file_stem = video_file.stem  # 拡張子なしファイル名
        
        # プロンプトのベース部分
        prompt = f"この動画（ファイル名: {file_stem}）の動作を解析して、以下の情報を含むJSONで返してください：\n"
        
        # 各フィールドの説明を追加
        for field_name, field_config in config["fields"].items():
            description = field_config["description"]
            if "options" in field_config:
                options = ", ".join(field_config["options"])
                description = f"{description}（選択肢: {options}）"
            prompt += f"- {field_name}: {description}\n"
        
        return prompt 