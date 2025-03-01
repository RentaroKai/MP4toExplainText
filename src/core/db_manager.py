import sqlite3
from typing import List, Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path: str):
        self._db_path = db_path
        self._conn = sqlite3.connect(db_path)
        self._cursor = self._conn.cursor()
        
    def get_videos(self) -> List[Dict]:
        """動画一覧を取得 - 改善版：analysis_resultsから直接データを取得"""
        try:
            query = """
            SELECT 
                v.id,
                v.file_path,
                v.file_name,
                v.status,
                v.progress,
                v.created_at,
                v.updated_at,
                ar.result_json,
                ar.animation_name,
                ar.character_gender,
                ar.character_age_group,
                ar.character_body_type,
                ar.movement_description,
                ar.initial_pose,
                ar.final_pose,
                ar.appropriate_scene,
                ar.loopable,
                ar.tempo_speed,
                ar.intensity_force,
                ar.posture_detail
            FROM videos v
            LEFT JOIN analysis_results ar ON v.id = ar.video_id
            ORDER BY v.created_at DESC
            """
            
            self._cursor.execute(query)
            rows = self._cursor.fetchall()
            
            return [{
                'id': row[0],
                'file_path': row[1],
                'file_name': row[2],
                'status': row[3],
                'progress': row[4],
                'created_at': row[5],
                'updated_at': row[6],
                'analysis_result': {
                    'result_json': row[7],
                    'animation_name': row[8],
                    'character_gender': row[9],
                    'character_age_group': row[10],
                    'character_body_type': row[11],
                    'movement_description': row[12],
                    'initial_pose': row[13],
                    'final_pose': row[14],
                    'appropriate_scene': row[15],
                    'loopable': row[16],
                    'tempo_speed': row[17],
                    'intensity_force': row[18],
                    'posture_detail': row[19]
                } if row[7] else None
            } for row in rows]
            
        except Exception as e:
            logger.error(f"動画一覧の取得に失敗: {str(e)}")
            return []
            
    def close(self):
        """データベース接続を閉じる"""
        if self._conn:
            self._conn.close() 