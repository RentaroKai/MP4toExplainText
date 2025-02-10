import sqlite3
from datetime import datetime
from typing import List, Dict, Any, Optional

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
            self._cursor.execute("""
                SELECT 
                    v.id,
                    v.file_path,
                    v.file_name,
                    ar.character_gender,
                    ar.character_age_group,
                    ar.character_body_type,
                    ar.result_json,
                    GROUP_CONCAT(t.tag) as tags
                FROM videos v
                LEFT JOIN analysis_results ar ON v.id = ar.video_id
                LEFT JOIN tags t ON v.id = t.video_id
                GROUP BY v.id
            """)
            columns = [description[0] for description in self._cursor.description]
            return [dict(zip(columns, row)) for row in self._cursor.fetchall()]
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

    def __enter__(self):
        """コンテキストマネージャーのエントリーポイント"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャーの終了処理"""
        self.disconnect() 