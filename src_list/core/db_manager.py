import sqlite3
from datetime import datetime
from typing import List, Dict, Any, Optional
import json

class DatabaseManager:
    def __init__(self, db_path: str):
        """
        データベース管理クラスの初期化
        Args:
            db_path (str): データベースファイルのパス
        """
        self.db_path = db_path
        self._connection = None
        self._cursor = None

    def connect(self):
        """データベースに接続"""
        try:
            self._connection = sqlite3.connect(self.db_path)
            self._cursor = self._connection.cursor()
        except sqlite3.Error as e:
            print(f"データベース接続エラー: {e}")
            raise

    def disconnect(self):
        """データベース接続を閉じる"""
        if self._connection:
            self._connection.close()

    def get_all_videos(self) -> List[Dict[str, Any]]:
        """
        全ての動画情報を取得
        Returns:
            List[Dict[str, Any]]: 動画情報のリスト
        """
        try:
            print("=== データベース取得開始 ===")
            self._cursor.execute("""
                SELECT 
                    v.id,
                    v.file_path,
                    v.file_name,
                    json_extract(ar.result_json, '$.character_gender') as character_gender,
                    json_extract(ar.result_json, '$.character_age_group') as character_age_group,
                    json_extract(ar.result_json, '$.character_body_type') as character_body_type,
                    json_extract(ar.result_json, '$.Name of AnimationFile') as animation_file_name,
                    ar.result_json,
                    ar.param_01,
                    ar.param_02,
                    ar.param_03,
                    GROUP_CONCAT(t.tag) as tags
                FROM videos v
                LEFT JOIN analysis_results ar ON v.id = ar.video_id
                LEFT JOIN tags t ON v.id = t.video_id
                GROUP BY v.id
            """)
            columns = [description[0] for description in self._cursor.description]
            print(f"カラム名: {columns}")
            
            # デバッグ用：取得したデータの内容を確認
            rows = self._cursor.fetchall()
            result = []
            for row in rows:
                row_dict = dict(zip(columns, row))
                print(f"\n行データ: {row_dict}")
                print(f"性別: {row_dict.get('character_gender')}")
                print(f"年齢: {row_dict.get('character_age_group')}")
                print(f"体型: {row_dict.get('character_body_type')}")
                print(f"アニメーションファイル名: {row_dict.get('animation_file_name')}")
                print(f"カスタムパラメータ1: {row_dict.get('param_01')}")
                print(f"カスタムパラメータ2: {row_dict.get('param_02')}")
                print(f"カスタムパラメータ3: {row_dict.get('param_03')}")
                result.append(row_dict)
            
            print("=== データベース取得終了 ===")
            return result
            
        except sqlite3.Error as e:
            print(f"データ取得エラー: {e}")
            return []

    def update_tags(self, video_id: int, tags: List[str], source: str = 'manual'):
        """
        タグを更新
        Args:
            video_id (int): 動画ID
            tags (List[str]): 新しいタグのリスト
            source (str): タグのソース（デフォルト: 'manual'）
        """
        try:
            # 既存のタグを削除
            self._cursor.execute("DELETE FROM tags WHERE video_id = ?", (video_id,))
            
            # 新しいタグを追加
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            for tag in tags:
                self._cursor.execute(
                    "INSERT INTO tags (video_id, tag, source, created_at) VALUES (?, ?, ?, ?)",
                    (video_id, tag, source, current_time)
                )
            
            self._connection.commit()
        except sqlite3.Error as e:
            print(f"タグ更新エラー: {e}")
            self._connection.rollback()
            raise

    def update_character_info(self, video_id: int, gender: str, age_group: str, body_type: str):
        """
        キャラクター情報を更新
        Args:
            video_id (int): 動画ID
            gender (str): 性別
            age_group (str): 年齢層
            body_type (str): 体型
        """
        try:
            # 既存のresult_jsonを取得
            self._cursor.execute("""
                SELECT result_json
                FROM analysis_results
                WHERE video_id = ?
            """, (video_id,))
            
            row = self._cursor.fetchone()
            if row:
                result_json = row[0]
                if isinstance(result_json, str):
                    result_json = result_json.replace("'", '"')
                    result_json = json.loads(result_json)
                
                # キャラクター情報を更新
                result_json['character_gender'] = gender
                result_json['character_age_group'] = age_group
                result_json['character_body_type'] = body_type
                
                # 更新を実行
                self._cursor.execute("""
                    UPDATE analysis_results
                    SET result_json = ?
                    WHERE video_id = ?
                """, (json.dumps(result_json), video_id))
                
                self._connection.commit()
            else:
                print(f"video_id {video_id} の解析結果が見つかりません")
                
        except sqlite3.Error as e:
            print(f"キャラクター情報更新エラー: {e}")
            self._connection.rollback()
            raise

    def __enter__(self):
        """コンテキストマネージャーのエントリーポイント"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャーの終了処理"""
        self.disconnect() 