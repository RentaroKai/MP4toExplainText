import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from src.core.config_manager import ConfigManager
from src.core.constants import VideoStatus

class Database:
    """データベース管理クラス"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config = ConfigManager()
        self.db_path = Path(self.config.get_paths()["db_path"])
        
        # データベースディレクトリの作成
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # データベースの初期化
        self._init_database()
    
    def _init_database(self):
        """データベースの初期化とテーブルの作成"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # 動画ファイル情報テーブル
                cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS videos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL UNIQUE,
                    file_name TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT '{VideoStatus.get_default()}',
                    progress INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """)
                
                # 解析結果テーブル
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS analysis_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_id INTEGER NOT NULL,
                    result_json TEXT NOT NULL,
                    version TEXT NOT NULL,
                    character_gender TEXT DEFAULT NULL,
                    character_age_group TEXT DEFAULT NULL,
                    character_body_type TEXT DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (video_id) REFERENCES videos (id)
                )
                """)
                
                # タグテーブル
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_id INTEGER NOT NULL,
                    tag TEXT NOT NULL,
                    source TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (video_id) REFERENCES videos (id)
                )
                """)
                
                conn.commit()
                self.logger.info("データベースの初期化が完了しました")
                
        except Exception as e:
            self.logger.error(f"データベースの初期化中にエラーが発生しました: {str(e)}")
            raise
    
    def _get_connection(self) -> sqlite3.Connection:
        """データベース接続を取得"""
        return sqlite3.connect(self.db_path)
    
    def add_video(self, file_path: str) -> int:
        """新しい動画ファイルをデータベースに追加"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # ファイル名の抽出
                file_name = Path(file_path).name
                
                cursor.execute("""
                INSERT INTO videos (file_path, file_name)
                VALUES (?, ?)
                """, (file_path, file_name))
                
                video_id = cursor.lastrowid
                conn.commit()
                
                self.logger.info(f"動画が追加されました: {file_path}")
                return video_id
                
        except sqlite3.IntegrityError:
            self.logger.warning(f"動画はすでに存在します: {file_path}")
            cursor.execute("SELECT id FROM videos WHERE file_path = ?", (file_path,))
            return cursor.fetchone()[0]
            
        except Exception as e:
            self.logger.error(f"動画の追加中にエラーが発生しました: {str(e)}")
            raise
    
    def update_video_status(self, video_id: int, status: str, progress: int = None):
        """動画の状態と進捗を更新"""
        try:
            # ステータスの検証
            if not VideoStatus.is_valid(status):
                raise ValueError(f"無効なステータスです: {status}")

            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                if progress is not None:
                    cursor.execute("""
                    UPDATE videos 
                    SET status = ?, progress = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """, (status, progress, video_id))
                else:
                    cursor.execute("""
                    UPDATE videos 
                    SET status = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """, (status, video_id))
                
                conn.commit()
                self.logger.info(f"動画ID {video_id} の状態が更新されました: {status}")
                
        except Exception as e:
            self.logger.error(f"動画状態の更新中にエラーが発生しました: {str(e)}")
            raise
    
    def add_analysis_result(self, video_id: int, result: dict, version: str):
        """解析結果を保存"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                INSERT INTO analysis_results (video_id, result_json, version)
                VALUES (?, ?, ?)
                """, (video_id, str(result), version))
                
                conn.commit()
                self.logger.info(f"動画ID {video_id} の解析結果が保存されました")
                
        except Exception as e:
            self.logger.error(f"解析結果の保存中にエラーが発生しました: {str(e)}")
            raise
    
    def add_tags(self, video_id: int, tags: List[str], source: str = "auto"):
        """タグを追加"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                for tag in tags:
                    cursor.execute("""
                    INSERT INTO tags (video_id, tag, source)
                    VALUES (?, ?, ?)
                    """, (video_id, tag, source))
                
                conn.commit()
                self.logger.info(f"動画ID {video_id} にタグが追加されました")
                
        except Exception as e:
            self.logger.error(f"タグの追加中にエラーが発生しました: {str(e)}")
            raise
    
    def get_video_info(self, video_id: int) -> Optional[Dict]:
        """動画情報を取得"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                SELECT id, file_path, file_name, status, progress, 
                       created_at, updated_at
                FROM videos
                WHERE id = ?
                """, (video_id,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        "id": row[0],
                        "file_path": row[1],
                        "file_name": row[2],
                        "status": row[3],
                        "progress": row[4],
                        "created_at": row[5],
                        "updated_at": row[6]
                    }
                return None
                
        except Exception as e:
            self.logger.error(f"動画情報の取得中にエラーが発生しました: {str(e)}")
            raise
    
    def get_all_videos(self, page: int = 1, per_page: int = 50) -> List[Dict]:
        """全ての動画情報をページネーション付きで取得"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                offset = (page - 1) * per_page
                cursor.execute("""
                SELECT v.id, v.file_path, v.file_name, v.status, v.progress,
                       v.created_at, v.updated_at,
                       GROUP_CONCAT(t.tag) as tags
                FROM videos v
                LEFT JOIN tags t ON v.id = t.video_id
                GROUP BY v.id
                ORDER BY v.created_at DESC
                LIMIT ? OFFSET ?
                """, (per_page, offset))
                
                rows = cursor.fetchall()
                return [{
                    "id": row[0],
                    "file_path": row[1],
                    "file_name": row[2],
                    "status": row[3],
                    "progress": row[4],
                    "created_at": row[5],
                    "updated_at": row[6],
                    "tags": row[7].split(",") if row[7] else []
                } for row in rows]
                
        except Exception as e:
            self.logger.error(f"動画一覧の取得中にエラーが発生しました: {str(e)}")
            raise
    
    def get_latest_analysis_result(self, video_id: int) -> Dict:
        """指定された動画の最新の解析結果を取得"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                SELECT * FROM analysis_results
                WHERE video_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """, (video_id,))
                
                result = cursor.fetchone()
                if result:
                    return {
                        "id": result[0],
                        "video_id": result[1],
                        "result_json": result[2],
                        "version": result[3],
                        "created_at": result[4]
                    }
                return None
                
        except Exception as e:
            self.logger.error(f"解析結果の取得中にエラーが発生しました: {str(e)}")
            raise 