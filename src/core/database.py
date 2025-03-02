import sqlite3
import logging
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Union, Any
from src.core.config_manager import ConfigManager
from src.core.constants import VideoStatus

class Database:
    """
    データベース管理クラス - 複数データベースファイル対応版
    """
    
    def __init__(self, db_path: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.config = ConfigManager()
        
        if db_path is None:
            self.db_path = Path(self.config.get_paths()["db_path"])
        else:
            self.db_path = Path(db_path)
        
        # データベースディレクトリの作成
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # データベースの初期化
        self._init_database()
        
        self.logger.info(f"データベースを初期化しました: {self.db_path}")
    
    def _init_database(self):
        """データベースの初期化とテーブルの作成 - 複数DB対応版"""
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
                
                # 解析結果テーブル - 一貫したフィールド構造に改善
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS analysis_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_id INTEGER NOT NULL,
                    result_json TEXT NOT NULL,
                    version TEXT NOT NULL,
                    
                    -- よく使用される重要なフィールドを個別のカラムとして追加
                    animation_name TEXT DEFAULT NULL,
                    character_gender TEXT DEFAULT NULL,
                    character_age_group TEXT DEFAULT NULL,
                    character_body_type TEXT DEFAULT NULL,
                    movement_description TEXT DEFAULT NULL,
                    initial_pose TEXT DEFAULT NULL,
                    final_pose TEXT DEFAULT NULL,
                    appropriate_scene TEXT DEFAULT NULL,
                    loopable TEXT DEFAULT NULL,
                    tempo_speed TEXT DEFAULT NULL,
                    intensity_force TEXT DEFAULT NULL,
                    posture_detail TEXT DEFAULT NULL,
                    
                    -- カスタムパラメータを追加
                    param_01 TEXT DEFAULT NULL,
                    param_02 TEXT DEFAULT NULL,
                    param_03 TEXT DEFAULT NULL,
                    
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
                self.logger.debug(f"データベーステーブルを初期化しました: {self.db_path}")
                
        except Exception as e:
            self.logger.error(f"データベースの初期化中にエラーが発生しました: {str(e)}")
            raise
    
    def change_database(self, new_db_path: str) -> bool:
        """
        使用するデータベースファイルを変更する
        
        Args:
            new_db_path: 新しいデータベースファイルのパス
            
        Returns:
            bool: 成功した場合はTrue、失敗した場合はFalse
        """
        try:
            # 現在のパスと同じ場合は何もしない
            if Path(new_db_path) == self.db_path:
                return True
                
            self.db_path = Path(new_db_path)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 新しいデータベースが存在しなければ初期化する
            if not self.db_path.exists() or self.db_path.stat().st_size == 0:
                self._init_database()
            
            # 最近使用したDBリストを更新
            self._update_recent_db_list(str(self.db_path))
            
            self.logger.info(f"データベースを変更しました: {self.db_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"データベース変更中にエラーが発生しました: {str(e)}")
            return False
    
    def _update_recent_db_list(self, db_path: str):
        """最近使用したデータベースリストを更新する"""
        try:
            self.logger.debug(f"_update_recent_db_list メソッドが呼び出されました。パス: {db_path}")
            
            # 設定ファイルから直接最新の設定を読み込む
            config_data = self.config._load_json(self.config.config_file)
            self.logger.debug(f"取得した設定データ: {config_data}")
            
            recent_dbs = config_data.get("recent_databases", [])
            self.logger.debug(f"更新前の最近使用したDBリスト: {recent_dbs}")
            
            # 既に同じパスが存在する場合は削除（後で先頭に追加するため）
            if db_path in recent_dbs:
                recent_dbs.remove(db_path)
                self.logger.debug(f"既存のパスを削除しました: {db_path}")
            
            # リストの先頭に追加
            recent_dbs.insert(0, db_path)
            self.logger.debug(f"リストの先頭に追加しました: {db_path}")
            
            # リストを最大10件に制限
            recent_dbs = recent_dbs[:10]
            
            # 設定を更新
            config_data["recent_databases"] = recent_dbs
            self.logger.debug(f"更新する設定データ: {config_data}")
            
            self.config.update_config(config_data)
            self.logger.debug(f"設定を更新しました。更新後のリスト: {recent_dbs}")
            
            # 更新後の設定を再確認
            updated_config = self.config._load_json(self.config.config_file)
            self.logger.debug(f"更新後の設定データを再確認: {updated_config}")
            
        except Exception as e:
            self.logger.warning(f"最近使用したDBリストの更新に失敗しました: {str(e)}")
            self.logger.debug(f"エラーの詳細: ", exc_info=True)
    
    def create_new_database(self, db_path: str) -> bool:
        """
        新しいデータベースファイルを作成する
        
        Args:
            db_path: 新しいデータベースファイルのパス
            
        Returns:
            bool: 成功した場合はTrue、失敗した場合はFalse
        """
        try:
            # 現在のパスから変更して新しいDBを初期化
            return self.change_database(db_path)
            
        except Exception as e:
            self.logger.error(f"新しいデータベース作成中にエラーが発生しました: {str(e)}")
            return False
    
    def get_database_path(self) -> str:
        """現在のデータベースファイルのパスを取得する"""
        return str(self.db_path)
    
    def _get_connection(self):
        """SQLite3データベース接続を取得 - パス動的変更対応版"""
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
    
    def _extract_fields_from_result(self, result: Union[Dict, str]) -> Dict[str, Any]:
        """AIの解析結果から各フィールドを抽出し、一貫したフォーマットに変換する
        
        AI応答の不確実性に対応するため、柔軟なフィールド抽出を実装
        """
        try:
            # 結果が文字列の場合は辞書に変換を試みる
            if isinstance(result, str):
                try:
                    result = json.loads(result)
                except json.JSONDecodeError:
                    # JSON解析に失敗した場合は元の文字列を返す
                    self.logger.warning("JSON解析に失敗しました。文字列として扱います")
                    return {
                        "raw_result": result,
                        "animation_name": None,
                        "character_gender": None,
                        "character_age_group": None,
                        "character_body_type": None,
                        "movement_description": None,
                        "initial_pose": None,
                        "final_pose": None,
                        "appropriate_scene": None,
                        "loopable": None,
                        "tempo_speed": None,
                        "intensity_force": None,
                        "posture_detail": None,
                        "param_01": None,
                        "param_02": None,
                        "param_03": None
                    }
            
            # 各フィールドの抽出（柔軟な命名規則に対応）
            field_mapping = {
                "animation_name": ["Name of AnimationFile", "Animation File Name", "AnimationFileName", "animation_name", "filename"],
                "character_gender": ["character_gender", "gender", "Gender", "CharacterGender"],
                "character_age_group": ["character_age_group", "age_group", "Age", "AgeGroup"],
                "character_body_type": ["character_body_type", "body_type", "BodyType", "build"],
                "movement_description": ["Overall Movement Description", "movement_description", "Description", "MovementDescription"],
                "initial_pose": ["Initial Pose", "initial_pose", "StartPose", "start_pose"],
                "final_pose": ["Final Pose", "final_pose", "EndPose", "end_pose"],
                "appropriate_scene": ["Appropriate Scene", "appropriate_scene", "Scene", "scene"],
                "loopable": ["Loopable", "loopable", "can_loop", "IsLoopable"],
                "tempo_speed": ["Tempo Speed", "tempo_speed", "Tempo", "Speed"],
                "intensity_force": ["Intensity Force", "intensity_force", "Intensity", "Force"],
                "posture_detail": ["Posture Detail", "posture_detail", "Posture", "PostureDetails"],
                "param_01": ["param_01", "custom_param1", "CustomParam1", "param01"],
                "param_02": ["param_02", "custom_param2", "CustomParam2", "param02"],
                "param_03": ["param_03", "custom_param3", "CustomParam3", "param03"]
            }
            
            extracted_fields = {}
            
            # 各フィールドに対して、可能性のあるキーを順番に試す
            for field, possible_keys in field_mapping.items():
                value = None
                for key in possible_keys:
                    if key in result:
                        value = result[key]
                        break
                extracted_fields[field] = value
            
            return extracted_fields
            
        except Exception as e:
            self.logger.error(f"フィールド抽出中にエラーが発生しました: {str(e)}")
            # エラーが発生した場合は空の辞書を返す
            return {k: None for k in field_mapping.keys()}

    def add_analysis_result(self, video_id: int, result: Union[Dict, str], version: str):
        """解析結果を保存 - 改善版：より柔軟なフィールド処理を実装"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # 結果が辞書の場合はJSON文字列に変換
                if isinstance(result, dict):
                    result_str = json.dumps(result, ensure_ascii=False)
                else:
                    result_str = str(result)
                
                # フィールドの抽出
                fields = self._extract_fields_from_result(result)
                
                # 解析結果の保存
                cursor.execute("""
                INSERT INTO analysis_results (
                    video_id, result_json, version, 
                    animation_name, character_gender, character_age_group, character_body_type,
                    movement_description, initial_pose, final_pose, appropriate_scene,
                    loopable, tempo_speed, intensity_force, posture_detail,
                    param_01, param_02, param_03
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    video_id, result_str, version,
                    fields["animation_name"], fields["character_gender"], 
                    fields["character_age_group"], fields["character_body_type"],
                    fields["movement_description"], fields["initial_pose"], 
                    fields["final_pose"], fields["appropriate_scene"],
                    fields["loopable"], fields["tempo_speed"], 
                    fields["intensity_force"], fields["posture_detail"],
                    fields["param_01"], fields["param_02"], fields["param_03"]
                ))
                
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
                
                # prompt_name列の存在確認
                has_prompt_column = True
                try:
                    cursor.execute("SELECT prompt_name FROM videos LIMIT 1")
                except sqlite3.OperationalError:
                    has_prompt_column = False
                    self.logger.debug("videosテーブルにprompt_name列が存在しません")
                
                # prompt_name列を含めてクエリを実行
                if has_prompt_column:
                    cursor.execute("""
                    SELECT id, file_path, file_name, status, progress, 
                           created_at, updated_at, prompt_name
                    FROM videos
                    WHERE id = ?
                    """, (video_id,))
                else:
                    cursor.execute("""
                    SELECT id, file_path, file_name, status, progress, 
                           created_at, updated_at
                    FROM videos
                    WHERE id = ?
                    """, (video_id,))
                
                row = cursor.fetchone()
                if row:
                    result = {
                        "id": row[0],
                        "file_path": row[1],
                        "file_name": row[2],
                        "status": row[3],
                        "progress": row[4],
                        "created_at": row[5],
                        "updated_at": row[6]
                    }
                    
                    # prompt_name列が存在する場合は追加
                    if has_prompt_column:
                        result["prompt_name"] = row[7] if row[7] is not None else ""
                        
                    return result
                    
                return None
                
        except Exception as e:
            self.logger.error(f"動画情報の取得中にエラーが発生しました: {str(e)}")
            raise
    
    def get_all_videos(self, page: int = 1, per_page: int = 50) -> List[Dict]:
        """全ての動画情報をページネーション付きで取得"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # prompt_name列の存在確認
                has_prompt_column = True
                try:
                    cursor.execute("SELECT prompt_name FROM videos LIMIT 1")
                except sqlite3.OperationalError:
                    has_prompt_column = False
                    self.logger.debug("videosテーブルにprompt_name列が存在しません")
                
                # オフセットとリミットの計算
                offset = (page - 1) * per_page
                
                # タグを含めたクエリの実行（LEFT JOINとGROUP BY使用）
                if has_prompt_column:
                    cursor.execute("""
                    SELECT v.id, v.file_path, v.file_name, v.status, v.progress, 
                           v.created_at, v.updated_at, v.prompt_name,
                           GROUP_CONCAT(t.tag) as tags
                    FROM videos v
                    LEFT JOIN tags t ON v.id = t.video_id
                    GROUP BY v.id
                    ORDER BY v.id DESC
                    LIMIT ? OFFSET ?
                    """, (per_page, offset))
                else:
                    cursor.execute("""
                    SELECT v.id, v.file_path, v.file_name, v.status, v.progress, 
                           v.created_at, v.updated_at,
                           GROUP_CONCAT(t.tag) as tags
                    FROM videos v
                    LEFT JOIN tags t ON v.id = t.video_id
                    GROUP BY v.id
                    ORDER BY v.id DESC
                    LIMIT ? OFFSET ?
                    """, (per_page, offset))
                
                rows = cursor.fetchall()
                videos = []
                
                for row in rows:
                    # 基本的な動画情報
                    video = {
                        "id": row[0],
                        "file_path": row[1],
                        "file_name": row[2],
                        "status": row[3],
                        "progress": row[4],
                        "created_at": row[5],
                        "updated_at": row[6]
                    }
                    
                    # prompt_name列が存在する場合
                    if has_prompt_column:
                        video["prompt_name"] = row[7] if row[7] is not None else ""
                        # タグはインデックス8
                        tags = row[8]
                    else:
                        # タグはインデックス7
                        tags = row[7]
                    
                    # タグを配列に変換
                    video["tags"] = tags.split(",") if tags else []
                    
                    videos.append(video)
                
                return videos
                
        except Exception as e:
            self.logger.error(f"全ての動画情報の取得中にエラーが発生しました: {str(e)}")
            raise
    
    def get_latest_analysis_result(self, video_id: int) -> Dict:
        """指定された動画の最新の解析結果を取得 - 改善版：構造化されたフィールドを含む"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                SELECT id, video_id, result_json, version, created_at,
                       animation_name, character_gender, character_age_group, character_body_type,
                       movement_description, initial_pose, final_pose, appropriate_scene,
                       loopable, tempo_speed, intensity_force, posture_detail,
                       param_01, param_02, param_03
                FROM analysis_results
                WHERE video_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """, (video_id,))
                
                result = cursor.fetchone()
                if result:
                    # 構造化されたフィールドを含む結果を返す
                    return {
                        "id": result[0],
                        "video_id": result[1],
                        "result_json": result[2],
                        "version": result[3],
                        "created_at": result[4],
                        # 構造化されたフィールド
                        "fields": {
                            "animation_name": result[5],
                            "character_gender": result[6],
                            "character_age_group": result[7],
                            "character_body_type": result[8],
                            "movement_description": result[9],
                            "initial_pose": result[10],
                            "final_pose": result[11],
                            "appropriate_scene": result[12],
                            "loopable": result[13],
                            "tempo_speed": result[14],
                            "intensity_force": result[15],
                            "posture_detail": result[16],
                            "param_01": result[17],
                            "param_02": result[18],
                            "param_03": result[19]
                        }
                    }
                return None
                
        except Exception as e:
            self.logger.error(f"解析結果の取得中にエラーが発生しました: {str(e)}")
            raise

    def update_video_prompt(self, video_id: int, prompt_name: str) -> bool:
        """
        ビデオに使用するプロンプト名を更新
        
        Args:
            video_id: 対象ビデオのID
            prompt_name: プロンプト名
            
        Returns:
            bool: 成功した場合はTrue、失敗した場合はFalse
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # プロンプト情報の列が存在しない場合は追加
                try:
                    cursor.execute("SELECT prompt_name FROM videos LIMIT 1")
                except sqlite3.OperationalError:
                    cursor.execute("ALTER TABLE videos ADD COLUMN prompt_name TEXT")
                    self.logger.info("videosテーブルにprompt_name列を追加しました")
                
                # プロンプト名を更新
                cursor.execute(
                    "UPDATE videos SET prompt_name = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (prompt_name, video_id)
                )
                
                conn.commit()
                
                if cursor.rowcount > 0:
                    self.logger.debug(f"ビデオID {video_id} のプロンプト設定を更新しました: {prompt_name}")
                    return True
                else:
                    self.logger.warning(f"ビデオID {video_id} が見つかりません")
                    return False
                    
        except Exception as e:
            self.logger.error(f"プロンプト設定の更新中にエラーが発生しました: {str(e)}")
            return False 