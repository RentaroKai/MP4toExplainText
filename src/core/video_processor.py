import logging
import asyncio
from typing import List, Optional, Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from src.core.database import Database
from src.core.gemini_api import GeminiAPI
from src.core.config_manager import ConfigManager
from src.core.constants import VideoStatus

class VideoProcessor:
    """動画処理を管理するクラス"""
    
    def __init__(self, database=None):
        self.logger = logging.getLogger(__name__)
        self.config = ConfigManager()
        # 外部からデータベースインスタンスを受け取れるように修正
        if database is None:
            self.db = Database()
        else:
            self.db = database
        self.gemini = GeminiAPI()
        self.executor = ThreadPoolExecutor(
            max_workers=1  # 同時処理数を1に制限
        )
        self._processing = set()  # 処理中の動画ID
        self._cancel_requested = set()  # キャンセルが要求された動画ID
        self.current_prompt_config = "default"  # 現在のプロンプト設定
    
    def set_prompt_config(self, config_name: str):
        """プロンプト設定を変更"""
        self.logger.info(f"プロンプト設定を変更: {config_name}")
        self.current_prompt_config = config_name
    
    async def process_video(self, video_path: str, progress_callback: Optional[Callable] = None, status_callback: Optional[Callable] = None) -> bool:
        """動画を非同期で処理"""
        try:
            print(f"動画処理が開始されました - file_path: {video_path}")
            self.logger.info(f"動画処理が開始されました - file_path: {video_path}")
            
            # データベースに動画を追加
            video_id = self.db.add_video(video_path)
            print(f"データベースに動画が追加されました - video_id: {video_id}")
            
            # 既に処理中の場合は待機
            if video_id in self._processing:
                self.logger.debug(f"この動画は既に処理中です - video_id: {video_id}")
                return False
                
            # 他の動画の処理完了を待機
            if len(self._processing) > 0:
                self.logger.info(f"他の動画の処理完了を待機中 - 待機中の動画ID: {video_id}")
                # 待機開始時に一度だけステータス更新
                self.db.update_video_status(video_id, VideoStatus.PENDING.value)
                if status_callback:
                    status_callback(video_id, VideoStatus.PENDING.value)
                
                # 待機ループ（ステータス更新なし）
                while len(self._processing) > 0:
                    await asyncio.sleep(5)  # 待機間隔を5秒に延長
            
            print(f"処理を開始します - video_id: {video_id}")
            self._processing.add(video_id)
            print(f"処理中リストに追加されました - 現在の処理中: {self._processing}")
            self.db.update_video_status(video_id, VideoStatus.PROCESSING.value, 0)
            if status_callback:
                status_callback(video_id, VideoStatus.PROCESSING.value)
            if progress_callback:
                progress_callback(video_id, 0)
            
            try:
                # 動画の解析（スレッドプールで実行）
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    self.executor,
                    lambda: self.gemini.analyze_video(video_path, self.current_prompt_config)
                )
                
                # キャンセルされた場合
                if video_id in self._cancel_requested:
                    self.db.update_video_status(video_id, VideoStatus.CANCELED.value)
                    if status_callback:
                        status_callback(video_id, VideoStatus.CANCELED.value)
                    self._cancel_requested.remove(video_id)
                    return False
                
                # 進捗更新（50%）
                self.db.update_video_status(video_id, VideoStatus.PROCESSING.value, 50)
                if status_callback:
                    status_callback(video_id, VideoStatus.PROCESSING.value)
                if progress_callback:
                    progress_callback(video_id, 50)
                
                # タグの抽出と保存
                tags = self.gemini.extract_tags(result)
                await loop.run_in_executor(
                    self.executor,
                    self.db.add_tags,
                    video_id,
                    tags
                )
                
                # 解析結果の保存
                await loop.run_in_executor(
                    self.executor,
                    self.db.add_analysis_result,
                    video_id,
                    result,
                    "1.0"  # バージョン情報
                )
                
                # 処理完了
                self.db.update_video_status(video_id, VideoStatus.FIX.value, 100)
                if status_callback:
                    status_callback(video_id, VideoStatus.FIX.value)
                if progress_callback:
                    progress_callback(video_id, 100)
                
                self.logger.info(f"動画ID {video_id} の処理が完了しました")
                return True
                
            except Exception as e:
                self.logger.error(f"動画ID {video_id} の処理中にエラーが発生しました: {str(e)}")
                self.db.update_video_status(video_id, VideoStatus.ERROR.value)
                if status_callback:
                    status_callback(video_id, VideoStatus.ERROR.value)
                raise
                
            finally:
                self._processing.remove(video_id)
                
        except Exception as e:
            self.logger.error(f"動画の処理中にエラーが発生しました: {str(e)}")
            return False
    
    async def process_multiple_videos(self, video_paths: List[str], progress_callback: Optional[Callable] = None, status_callback: Optional[Callable] = None):
        """複数の動画を順次処理"""
        results = []
        for path in video_paths:
            result = await self.process_video(path, progress_callback, status_callback)
            results.append(result)
        return results
    
    def cancel_processing(self, video_id: int):
        """動画処理のキャンセルを要求"""
        if video_id in self._processing:
            self._cancel_requested.add(video_id)
            self.logger.info(f"動画ID {video_id} の処理キャンセルが要求されました")
    
    def is_processing(self, video_id: int) -> bool:
        """動画が処理中かどうかを確認"""
        return video_id in self._processing 