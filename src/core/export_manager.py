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
        """解析結果のJSONをパース"""
        try:
            # 文字列がすでにdictの場合はastを使用
            return ast.literal_eval(result_json)
        except:
            # 通常のJSONとしてパース
            return json.loads(result_json)
    
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
                "ファイル名",
                "アニメーション名（英語）",
                "推奨キャラクタープロフィール",
                "動作の説明",
                "初期ポーズ",
                "最終ポーズ",
                "適切なシーン",
                "ループ可能",
                "テンポ",
                "動きの強さ",
                "姿勢の詳細",
                "ステータス",
                "作成日時",
                "更新日時"
            ]
            
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                
                for video_id in video_ids:
                    video_info = self.database.get_video_info(video_id)
                    if not video_info:
                        continue
                    
                    result = self.database.get_latest_analysis_result(video_id)
                    if not result:
                        # 解析結果がない場合は基本情報のみ出力
                        row = [
                            video_info["file_name"],
                            "", "", "", "", "", "", "", "", "", "",
                            video_info["status"],
                            video_info["created_at"],
                            video_info["updated_at"]
                        ]
                    else:
                        # 解析結果がある場合は全情報を出力
                        result_data = self._parse_result_json(result["result_json"])
                        row = [
                            video_info["file_name"],
                            result_data.get("Name of AnimationFile", ""),
                            result_data.get("Recommended Character Profile", ""),
                            result_data.get("Overall Movement Description", ""),
                            result_data.get("Initial Pose", ""),
                            result_data.get("Final Pose", ""),
                            result_data.get("Appropriate Scene", ""),
                            result_data.get("Loopable", ""),
                            result_data.get("Tempo Speed", ""),
                            result_data.get("Intensity Force", ""),
                            result_data.get("Posture Detail", ""),
                            video_info["status"],
                            video_info["created_at"],
                            video_info["updated_at"]
                        ]
                    writer.writerow(row)
            
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
            
            export_data = []
            for video_id in video_ids:
                video_info = self.database.get_video_info(video_id)
                if not video_info:
                    continue
                
                result = self.database.get_latest_analysis_result(video_id)
                if not result:
                    # 解析結果がない場合は基本情報のみ出力
                    export_data.append({
                        "file_info": {
                            "file_name": video_info["file_name"],
                            "file_path": video_info["file_path"],
                            "status": video_info["status"],
                            "created_at": video_info["created_at"],
                            "updated_at": video_info["updated_at"]
                        }
                    })
                else:
                    # 解析結果がある場合は全情報を出力
                    result_data = self._parse_result_json(result["result_json"])
                    export_data.append({
                        "file_info": {
                            "file_name": video_info["file_name"],
                            "file_path": video_info["file_path"],
                            "status": video_info["status"],
                            "created_at": video_info["created_at"],
                            "updated_at": video_info["updated_at"]
                        },
                        "analysis_result": result_data,
                        "analysis_version": result["version"],
                        "analysis_date": result["created_at"]
                    })
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"JSONファイルを作成しました: {filepath}")
            return str(filepath)
            
        except Exception as e:
            self.logger.error(f"JSONエクスポート中にエラーが発生しました: {str(e)}")
            raise 