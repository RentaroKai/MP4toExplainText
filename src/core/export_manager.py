import json
import csv
from datetime import datetime
from pathlib import Path
from typing import List, Dict
import logging
import ast

class ExportManager:
    """エクスポートを管理するクラス"""
    
    def __init__(self, config_manager, database):
        self.config_manager = config_manager
        self.database = database
        self.logger = logging.getLogger(__name__)
        
        # エクスポートディレクトリの設定
        paths = self.config_manager.get_paths()
        self.export_dir = Path(paths.get("export_dir", "./exports"))
        self.csv_dir = self.export_dir / "csv"
        self.json_dir = self.export_dir / "json"
        
        # ディレクトリの作成
        self._ensure_export_dirs()
    
    def _ensure_export_dirs(self):
        """エクスポートディレクトリの存在確認と作成"""
        for directory in [self.export_dir, self.csv_dir, self.json_dir]:
            directory.mkdir(parents=True, exist_ok=True)
    
    def _generate_filename(self, prefix: str, extension: str) -> str:
        """タイムスタンプ付きのファイル名を生成"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{timestamp}.{extension}"

    def _get_all_video_ids(self) -> List[int]:
        """全ての動画IDを取得"""
        videos = self.database.get_all_videos()
        return [video["id"] for video in videos]
    
    def _parse_result_json(self, result_json: str) -> dict:
        """
        解析結果のJSONをパース
        
        複数の形式に対応するよう強化：
        - 文字列形式のJSON
        - Pythonの辞書形式の文字列
        - すでに変換済みの辞書オブジェクト
        """
        if result_json is None:
            return {}
            
        # すでに辞書の場合はそのまま返す
        if isinstance(result_json, dict):
            return result_json
            
        # 文字列の場合は変換を試みる
        if isinstance(result_json, str):
            result_json = result_json.strip()
            try:
                # 通常のJSONとしてパース
                return json.loads(result_json)
            except json.JSONDecodeError:
                try:
                    # Pythonの辞書リテラルとしてパース
                    return ast.literal_eval(result_json)
                except (SyntaxError, ValueError):
                    # 両方失敗した場合は空の辞書を返す
                    self.logger.error(f"JSONパースに失敗しました。不正な形式です: {result_json[:100]}...")
                    return {}
        
        # その他の型の場合は空の辞書を返す
        self.logger.warning(f"予期しない型のデータ: {type(result_json)}")
        return {}
    
    def export_to_csv(self, video_ids: List[int] = None) -> str:
        """解析結果をCSVファイルにエクスポート"""
        try:
            # video_idsが指定されていない場合は全件取得
            if not video_ids:
                video_ids = self._get_all_video_ids()

            filename = self._generate_filename("analysis_results", "csv")
            filepath = self.csv_dir / filename
            
            # ヘッダーの定義
            headers = [
                "filename",
                "animation_name_en",
                "character_gender",
                "character_age_group",
                "character_body_type",
                "motion_description",
                "initial_pose",
                "final_pose",
                "suitable_scenes",
                "can_loop",
                "tempo",
                "motion_intensity",
                "posture_details",
                "status",
                "created_at",
                "updated_at",
                "prompt_name"  # プロンプト名も出力に追加
            ]
            
            # データベースの解析結果JSONフィールドとCSVヘッダーのマッピング
            field_mapping = {
                "Name of AnimationFile": "animation_name_en",
                "character_gender": "character_gender",
                "character_age_group": "character_age_group", 
                "character_body_type": "character_body_type",
                "Overall Movement Description": "motion_description",
                "Initial Pose": "initial_pose",
                "Final Pose": "final_pose",
                "Appropriate Scene": "suitable_scenes",
                "Loopable": "can_loop",
                "Tempo Speed": "tempo",
                "Intensity Force": "motion_intensity",
                "Posture Detail": "posture_details"
            }
            
            self.logger.info(f"CSVエクスポート開始: {len(video_ids)}件のビデオを処理")
            
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                
                for video_id in video_ids:
                    try:
                        video_info = self.database.get_video_info(video_id)
                        if not video_info:
                            self.logger.warning(f"ビデオID {video_id} の情報が見つかりません")
                            continue
                        
                        # プロンプト名を取得（存在しない場合は空文字）
                        prompt_name = video_info.get("prompt_name", "")
                        
                        result = self.database.get_latest_analysis_result(video_id)
                        if not result:
                            # 解析結果がない場合は基本情報のみ出力
                            row = [
                                video_info["file_name"],
                                "", "", "", "", "", "", "", "", "", "", "", "",
                                video_info["status"],
                                video_info["created_at"],
                                video_info["updated_at"],
                                prompt_name
                            ]
                            writer.writerow(row)
                            continue
                        
                        # 解析結果がある場合は全情報を出力
                        try:
                            if isinstance(result["result_json"], str):
                                result_data = self._parse_result_json(result["result_json"])
                            else:
                                result_data = result["result_json"]
                            
                            # 各フィールドを取得（存在しない場合は空文字）
                            field_values = {}
                            for src_field, dest_field in field_mapping.items():
                                field_values[dest_field] = result_data.get(src_field, "")
                            
                            row = [
                                video_info["file_name"],
                                field_values["animation_name_en"],
                                field_values["character_gender"],
                                field_values["character_age_group"],
                                field_values["character_body_type"],
                                field_values["motion_description"],
                                field_values["initial_pose"],
                                field_values["final_pose"],
                                field_values["suitable_scenes"],
                                field_values["can_loop"],
                                field_values["tempo"],
                                field_values["motion_intensity"],
                                field_values["posture_details"],
                                video_info["status"],
                                video_info["created_at"],
                                video_info["updated_at"],
                                prompt_name
                            ]
                            writer.writerow(row)
                            
                        except Exception as parse_error:
                            self.logger.error(f"ビデオID {video_id} の解析結果解析中にエラー: {str(parse_error)}")
                            # エラーが発生しても中断せず、基本情報だけ出力
                            row = [
                                video_info["file_name"],
                                "", "", "", "", "", "", "", "", "", "", "", "",
                                video_info["status"],
                                video_info["created_at"],
                                video_info["updated_at"],
                                prompt_name
                            ]
                            writer.writerow(row)
                            
                    except Exception as e:
                        self.logger.error(f"ビデオID {video_id} の処理中にエラー: {str(e)}")
                        # 続行
            
            self.logger.info(f"CSVファイルを作成しました: {filepath}")
            return str(filepath)
            
        except Exception as e:
            self.logger.error(f"CSVエクスポート中にエラーが発生しました: {str(e)}")
            raise
    
    def export_to_json(self, video_ids: List[int] = None) -> str:
        """解析結果をJSONファイルにエクスポート"""
        try:
            # video_idsが指定されていない場合は全件取得
            if not video_ids:
                video_ids = self._get_all_video_ids()

            filename = self._generate_filename("analysis_results", "json")
            filepath = self.json_dir / filename
            
            self.logger.info(f"JSONエクスポート開始: {len(video_ids)}件のビデオを処理")
            export_data = []
            
            for video_id in video_ids:
                try:
                    video_info = self.database.get_video_info(video_id)
                    if not video_info:
                        self.logger.warning(f"ビデオID {video_id} の情報が見つかりません")
                        continue
                    
                    # プロンプト名を取得
                    prompt_name = video_info.get("prompt_name", "")
                    
                    # 基本情報を取得
                    file_info = {
                        "file_name": video_info["file_name"],
                        "file_path": video_info["file_path"],
                        "status": video_info["status"],
                        "created_at": video_info["created_at"],
                        "updated_at": video_info["updated_at"],
                        "prompt_name": prompt_name
                    }
                    
                    result = self.database.get_latest_analysis_result(video_id)
                    if not result:
                        # 解析結果がない場合は基本情報のみ出力
                        export_data.append({
                            "file_info": file_info
                        })
                    else:
                        # 解析結果がある場合は全情報を出力
                        try:
                            if isinstance(result["result_json"], str):
                                result_data = self._parse_result_json(result["result_json"])
                            else:
                                result_data = result["result_json"]
                                
                            export_data.append({
                                "file_info": file_info,
                                "analysis_result": result_data,
                                "analysis_version": result["version"],
                                "analysis_date": result["created_at"]
                            })
                        except Exception as parse_error:
                            self.logger.error(f"ビデオID {video_id} のJSON解析中にエラー: {str(parse_error)}")
                            # エラーが発生しても基本情報だけ出力
                            export_data.append({
                                "file_info": file_info,
                                "parse_error": str(parse_error)
                            })
                except Exception as e:
                    self.logger.error(f"ビデオID {video_id} の処理中にエラー: {str(e)}")
                    # 続行
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"JSONファイルを作成しました: {filepath}")
            return str(filepath)
            
        except Exception as e:
            self.logger.error(f"JSONエクスポート中にエラーが発生しました: {str(e)}")
            raise 