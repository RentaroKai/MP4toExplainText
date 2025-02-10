from typing import List, Dict, Any
from .db_manager import DatabaseManager

class DataManager:
    def __init__(self, db_path: str):
        """
        データ管理クラスの初期化
        Args:
            db_path (str): データベースファイルのパス
        """
        self.db_path = db_path
        self._db_manager = DatabaseManager(db_path)
        self._cache = {}

    def load_all_videos(self) -> List[Dict[str, Any]]:
        """
        全ての動画情報を読み込む
        Returns:
            List[Dict[str, Any]]: 動画情報のリスト
        """
        with self._db_manager as db:
            videos = db.get_all_videos()
            self._cache['videos'] = videos
            return videos

    def update_video_tags(self, video_id: int, tags: List[str]) -> bool:
        """
        動画のタグを更新
        Args:
            video_id (int): 動画ID
            tags (List[str]): 新しいタグのリスト
        Returns:
            bool: 更新が成功したかどうか
        """
        try:
            with self._db_manager as db:
                db.update_tags(video_id, tags)
            
            # キャッシュを更新
            if 'videos' in self._cache:
                for video in self._cache['videos']:
                    if video['id'] == video_id:
                        video['tags'] = ','.join(tags)
                        break
            
            return True
        except Exception as e:
            print(f"タグ更新中にエラーが発生しました: {e}")
            return False

    def search_videos(self, query: str) -> List[Dict[str, Any]]:
        """
        動画を検索
        Args:
            query (str): 検索クエリ
        Returns:
            List[Dict[str, Any]]: 検索結果のリスト
        """
        if not self._cache.get('videos'):
            self.load_all_videos()
        
        query = query.lower()
        return [
            video for video in self._cache['videos']
            if query in video['file_name'].lower() or
               (video.get('tags') and query in video['tags'].lower())
        ]

    def filter_videos(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        動画をフィルタリング
        Args:
            filters (Dict[str, Any]): フィルター条件
        Returns:
            List[Dict[str, Any]]: フィルタリング結果のリスト
        """
        if not self._cache.get('videos'):
            self.load_all_videos()
        
        filtered_videos = self._cache['videos']
        
        for key, value in filters.items():
            if value:
                filtered_videos = [
                    video for video in filtered_videos
                    if str(video.get(key, '')).lower() == str(value).lower()
                ]
        
        return filtered_videos

    def update_character_info(self, video_id: int, gender: str, age_group: str, body_type: str) -> bool:
        """
        キャラクター情報を更新
        Args:
            video_id (int): 動画ID
            gender (str): 性別
            age_group (str): 年齢層
            body_type (str): 体型
        Returns:
            bool: 更新が成功したかどうか
        """
        try:
            with self._db_manager as db:
                db.update_character_info(video_id, gender, age_group, body_type)
            
            # キャッシュを更新
            if 'videos' in self._cache:
                for video in self._cache['videos']:
                    if video['id'] == video_id:
                        video['character_gender'] = gender
                        video['character_age_group'] = age_group
                        video['character_body_type'] = body_type
                        break
            
            return True
        except Exception as e:
            print(f"キャラクター情報更新中にエラーが発生しました: {e}")
            return False 