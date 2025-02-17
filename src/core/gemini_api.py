import os
import time
import logging
from pathlib import Path
from typing import Dict, Optional
import google.generativeai as genai
from google.ai.generativelanguage_v1beta.types import content
from src.core.config_manager import ConfigManager
import certifi

class GeminiAPI:
    """Gemini APIを使用して動画解析を行うクラス"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config = ConfigManager()
        self._setup_api()
        self._setup_model()
    
    def _setup_api(self):
        """APIの初期設定"""
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            self.logger.error("環境変数 'GOOGLE_API_KEY' が設定されていません")
            raise ValueError("APIキーが設定されていません")
        
        # SSL証明書の設定
        os.environ['SSL_CERT_FILE'] = certifi.where()
        os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
        
        genai.configure(api_key=api_key)
    
    def _setup_model(self):
        """Geminiモデルの設定"""
        generation_config = {
            "temperature": 1,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8192,
            "response_schema": content.Schema(
                type=content.Type.OBJECT,
                required=["Name of AnimationFile", "Overall Movement Description", 
                         "Appropriate Scene", "Posture Detail",
                         "character_gender", "character_age_group", "character_body_type"],
                properties={
                    "Name of AnimationFile": content.Schema(
                        type=content.Type.STRING,
                    ),
                    "character_gender": content.Schema(
                        type=content.Type.STRING,
                    ),
                    "character_age_group": content.Schema(
                        type=content.Type.STRING,
                    ),
                    "character_body_type": content.Schema(
                        type=content.Type.STRING,
                    ),
                    "Overall Movement Description": content.Schema(
                        type=content.Type.STRING,
                    ),
                    "Initial Pose": content.Schema(
                        type=content.Type.STRING,
                    ),
                    "Final Pose": content.Schema(
                        type=content.Type.STRING,
                    ),
                    "Appropriate Scene": content.Schema(
                        type=content.Type.STRING,
                    ),
                    "Loopable": content.Schema(
                        type=content.Type.STRING,
                    ),
                    "Tempo Speed": content.Schema(
                        type=content.Type.STRING,
                    ),
                    "Intensity Force": content.Schema(
                        type=content.Type.STRING,
                    ),
                    "Posture Detail": content.Schema(
                        type=content.Type.STRING,
                    ),
                },
            ),
            "response_mime_type": "application/json",
        }

        self.model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            generation_config=generation_config,
            system_instruction="""
            Analyze the actions of people in the video and return the results in JSON format.
            Keep the response concise and avoid unnecessary details.
            
            # Required Fields:
            - Animation File Name (in English, around 16 characters)
            - Character Gender (suitable character_gender for the movement: male, female, both, any; if the determination is ambiguous, any is acceptable)
            - Character Age Group (suitable character_Age_Group for the movement: young, adult, elderly, child, any; if the determination is unclear, any is acceptable)
            - Character Body Type (suitable Character_Body_Type for the movement: muscular, any; if a clear assessment cannot be made, any is acceptable)
            - Overall Movement Description (a brief description of the movement, 50-120 characters)
            - Initial Pose (starting pose, up to 30 characters)
            - Final Pose (ending pose, up to 30 characters)
            - Appropriate Scene (e.g., daily life, combat, etc.)
            - Loopable (The first and last poses match exactly in position and angle, making the loop unnoticeable even when played endlessly. e.g., Yes/No)
            - Tempo Speed (e.g., Fast-paced, Moderate, Slow)
            - Intensity Force (e.g., High Impact, Subtle)
            - Posture Detail (detailed description of posture and body movement changes, 16-100 characters)
            """
        )
    
    def upload_video(self, video_path: str) -> Optional[genai.types.File]:
        """動画ファイルをGeminiにアップロード"""
        try:
            if not Path(video_path).exists():
                raise FileNotFoundError(f"ファイルが見つかりません: {video_path}")
            
            file = genai.upload_file(video_path, mime_type="video/mp4")
            self.logger.info(f"動画のアップロードが完了しました: {video_path}")
            return file
            
        except Exception as e:
            self.logger.error(f"動画のアップロード中にエラーが発生しました: {str(e)}")
            raise
    
    def wait_for_processing(self, file: genai.types.File):
        """ファイルの処理完了を待機"""
        try:
            self.logger.info("ファイル処理の完了を待機中...")
            retry_count = 30  # リトライ回数を増やす（デフォルトの3倍）
            retry_delay = 5   # 待機時間を5秒に設定
            
            for attempt in range(retry_count):
                self.logger.info(f"処理待機中... 試行回数: {attempt + 1}/{retry_count}")
                file = genai.get_file(file.name)
                if file.state.name == "ACTIVE":
                    self.logger.info("ファイル処理が完了しました")
                    return True
                elif file.state.name == "FAILED":
                    raise Exception(f"ファイル処理が失敗しました: {file.name}")
                elif file.state.name != "PROCESSING":
                    raise Exception(f"予期せぬファイル状態です: {file.state.name}")
                
                time.sleep(retry_delay)
            
            raise TimeoutError(f"ファイル処理がタイムアウトしました（{retry_count * retry_delay}秒経過）")
            
        except Exception as e:
            self.logger.error(f"ファイル処理の待機中にエラーが発生しました: {str(e)}")
            raise
    
    def analyze_video(self, video_path: str) -> Dict:
        """動画を解析して結果を返す"""
        try:
            # 動画のアップロード
            video_file = self.upload_video(video_path)
            
            # 処理完了を待機
            self.wait_for_processing(video_file)
            
            # チャットセッションの開始と解析
            chat = self.model.start_chat()
            response = chat.send_message([
                video_file,
                "この動画の動作を解析して、以下の情報を含むJSONで返してください：\n"
                "- Name of AnimationFile: 動画の名前（英語、16文字程度）\n"
                "- Character Gender: この動作に適した性別（男性、女性、両方、どちらでも可）\n"
                "- Character Age Group: この動作に適した年齢層（若者、成人、高齢者、子供）\n"
                "- Character Body Type: この動作に適した体型（平均、筋肉質、スリム）\n"
                "- Overall Movement Description: 動作の説明（50-120文字）\n"
                "- Initial Pose: 開始ポーズ（30文字以内）\n"
                "- Final Pose: 終了ポーズ（30文字以内）\n"
                "- Appropriate Scene: 適切なシーン（例：日常生活、戦闘など）\n"
                "- Loopable: ループ可能か（Yes/No）\n"
                "- Tempo Speed: テンポ（Fast-paced/Moderate/Slow）\n"
                "- Intensity Force: 動きの強さ（High Impact/Subtle）\n"
                "- Posture Detail: 姿勢の詳細（16-100文字）"
            ])
            
            # レスポンスの解析
            result = eval(response.text)  # JSON文字列を辞書に変換
            self.logger.info(f"動画の解析が完了しました: {video_path}")
            return result
            
        except Exception as e:
            self.logger.error(f"動画の解析中にエラーが発生しました: {str(e)}")
            raise
    
    def extract_tags(self, analysis_result: Dict) -> list:
        """解析結果からタグを抽出"""
        tags = []
        
        # シーンタグ
        if scene := analysis_result.get("Appropriate Scene"):
            tags.append(f"scene:{scene}")
        
        # テンポタグ
        if tempo := analysis_result.get("Tempo Speed"):
            tags.append(f"tempo:{tempo}")
        
        # 強度タグ
        if intensity := analysis_result.get("Intensity Force"):
            tags.append(f"intensity:{intensity}")
        
        # ループ可能タグ
        if loopable := analysis_result.get("Loopable"):
            tags.append(f"loopable:{loopable}")
        
        return tags 