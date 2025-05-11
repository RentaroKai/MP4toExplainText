import os
import time
import logging
import httplib2
import json
import re
from pathlib import Path
from typing import Dict, Optional, Union, List, Any
import google.generativeai as genai
from google.ai.generativelanguage_v1beta.types import content
from src.core.config_manager import ConfigManager
from src.core.prompt_manager import PromptManager
import certifi

class GeminiAPI:
    """Gemini APIを使用して動画解析を行うクラス - 改善版：柔軟なレスポンス処理"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config = ConfigManager()
        self.prompt_manager = PromptManager()
        self._setup_api()
        self._setup_model()

    def _setup_api(self):
        """APIの初期設定"""
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            self.logger.error("環境変数 'GOOGLE_API_KEY' が設定されていません")
            raise ValueError("APIキーが設定されていません")

        # SSL証明書の設定
        cert_path = os.environ.get('SSL_CERT_FILE')
        if cert_path:
            httplib2.CA_CERTS = cert_path
            self.logger.info(f"SSL証明書を設定しました: {cert_path}")
        else:
            # フォールバック: システムのデフォルト証明書を使用
            os.environ['SSL_CERT_FILE'] = certifi.where()
            os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
            self.logger.info("システムのデフォルト証明書を使用します")

        # トランスポート方式の指定を追加
        genai.configure(
            api_key=api_key,
            transport='rest'  # 安定性向上のため
        )
        self.logger.info("Gemini APIの設定が完了しました")

    # def _setup_model(self):
    #     """Geminiモデルの設定"""
    #     generation_config = {
    #         "temperature": 1,
    #         "top_p": 0.95,
    #         "top_k": 40,
    #         "max_output_tokens": 8192,
    #         "response_mime_type": "application/json",
    #     }

    #     self.model = genai.GenerativeModel(
    #         model_name="gemini-2.0-flash",
    #         generation_config=generation_config,
    #         system_instruction="Analyze the actions of people in the video and return the results in JSON format."
    #     )

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
                    "param_01": content.Schema(
                        type=content.Type.STRING,
                    ),
                    "param_02": content.Schema(
                        type=content.Type.STRING,
                    ),
                    "param_03": content.Schema(
                        type=content.Type.STRING,
                    ),
                },
            ),
            "response_mime_type": "application/json",
        }

        # FIRST_EDIT: Use model_name from config
        model_name = self.config.get_model_name()
        self.logger.info(f"Using Gemini model: {model_name}")
        self.model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=generation_config,
            system_instruction="""
            Analyze the actions of people in the video and return the results in JSON format.
            Keep the response concise and avoid unnecessary details.
            # Required Fields:
            - Animation File Name
            - character_gender
            - character_age_group
            - character_body_type
            - Overall Movement Description
            - Initial Pose
            - Final Pose
            - Appropriate Scene
            - Loopable
            - Tempo Speed
            - Intensity Force
            - Posture Detail
            - param_01 (HandyItem)
            - param_02 (CommunicationParam: e.g., Neutral, Agree, Deny, etc.)
            - param_03 (Emotion: e.g., Neutral, Happy, Sad, Angry, etc.)
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

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """AIからの応答テキストをパースして辞書に変換する
        
        複数のフォーマットに対応する柔軟なパース処理
        """
        try:
            # まずJSON.parseを試みる
            try:
                return json.loads(response_text)
            except json.JSONDecodeError:
                self.logger.warning("標準JSONパースに失敗しました。代替パース処理を試みます。")
            
            # Python evalを試みる
            try:
                # evalは危険な可能性があるので、単純な辞書のみを想定
                if re.match(r"^\s*\{.*\}\s*$", response_text, re.DOTALL):
                    result = eval(response_text)
                    if isinstance(result, dict):
                        return result
            except Exception as e:
                self.logger.warning(f"Pythonスタイルの辞書評価に失敗しました: {str(e)}")
            
            # 正規表現ベースの抽出を試みる
            result = {}
            
            # キーと値のペアを抽出する正規表現
            pattern = r'["\']?([^"\']+)["\']?\s*:\s*["\']?([^"\'{}][^",\'{}]*)["\']?[,}]'
            matches = re.findall(pattern, response_text)
            for key, value in matches:
                key = key.strip()
                value = value.strip()
                result[key] = value
            
            if result:
                self.logger.info("正規表現ベースの抽出で部分的な結果を得ました")
                return result
            
            # 全て失敗した場合は、テキスト全体を1つのフィールドとして扱う
            self.logger.warning("構造化パースに失敗しました。テキスト全体を1つのフィールドとして扱います")
            return {"raw_text": response_text}
        
        except Exception as e:
            self.logger.error(f"レスポンスパース中に予期せぬエラーが発生: {str(e)}")
            return {"error": str(e), "raw_text": response_text}

    def analyze_video(self, video_path: str, config_name: str = "default") -> Dict:
        """動画を解析して結果を返す - 改善版：より柔軟なレスポンス処理"""
        try:
            # プロンプト設定の読み込み
            self.prompt_manager.load_config(config_name)

            # 動画のアップロード
            video_file = self.upload_video(video_path)

            # 処理完了を待機
            self.wait_for_processing(video_file)

            # プロンプトの生成
            prompt = self.prompt_manager.generate_prompt(video_path)
            if not prompt:
                raise ValueError("プロンプトの生成に失敗しました")

            # チャットセッションの開始と解析
            chat = self.model.start_chat()
            response = chat.send_message([video_file, prompt])

            # レスポンスの解析（柔軟なパース処理）
            result = self._parse_response(response.text)
            
            # ログに記録（デバッグ用）
            self.logger.info(f"AIレスポンスの生テキスト: {response.text}")
            self.logger.info(f"AIレスポンスのパース結果: {result}")
            
            # カスタムパラメータの確認 - 詳細ログ追加
            self.logger.info(f"カスタムパラメータ - param_01: {result.get('param_01')}")
            self.logger.info(f"カスタムパラメータ - param_02: {result.get('param_02')}")
            self.logger.info(f"カスタムパラメータ - param_03: {result.get('param_03')}")
            
            # 必須フィールドの確認
            required_fields = ["Name of AnimationFile", "Overall Movement Description", 
                               "Appropriate Scene", "Posture Detail"]
            missing_fields = [field for field in required_fields if field not in result]
            
            if missing_fields:
                self.logger.warning(f"AIの応答に不足しているフィールドがあります: {missing_fields}")
            
            self.logger.info(f"動画の解析が完了しました: {video_path}")
            return result

        except Exception as e:
            self.logger.error(f"動画の解析中にエラーが発生しました: {str(e)}")
            raise

    def extract_tags(self, analysis_result: Dict) -> List[str]:
        """解析結果からタグを抽出 - 改善版：より柔軟な抽出処理"""
        tags = []

        # 様々なキー名に対応
        scene_keys = ["Appropriate Scene", "scene", "Scene", "appropriate_scene"]
        tempo_keys = ["Tempo Speed", "tempo", "Speed", "tempo_speed"]
        intensity_keys = ["Intensity Force", "intensity", "Force", "intensity_force"]
        loopable_keys = ["Loopable", "loopable", "can_loop", "IsLoopable"]
        
        # シーンタグ
        for key in scene_keys:
            if key in analysis_result and analysis_result[key]:
                tags.append(f"scene:{analysis_result[key]}")
                break
        
        # テンポタグ
        for key in tempo_keys:
            if key in analysis_result and analysis_result[key]:
                tags.append(f"tempo:{analysis_result[key]}")
                break
        
        # 強度タグ
        for key in intensity_keys:
            if key in analysis_result and analysis_result[key]:
                tags.append(f"intensity:{analysis_result[key]}")
                break
        
        # ループ可能タグ
        for key in loopable_keys:
            if key in analysis_result and analysis_result[key]:
                tags.append(f"loopable:{analysis_result[key]}")
                break
        
        # キャラクター特性タグ
        if "character_gender" in analysis_result and analysis_result["character_gender"]:
            tags.append(f"gender:{analysis_result['character_gender']}")
        
        if "character_age_group" in analysis_result and analysis_result["character_age_group"]:
            tags.append(f"age:{analysis_result['character_age_group']}")
        
        if "character_body_type" in analysis_result and analysis_result["character_body_type"]:
            tags.append(f"body:{analysis_result['character_body_type']}")
        
        return tags