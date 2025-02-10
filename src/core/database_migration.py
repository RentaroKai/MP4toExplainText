import sqlite3
import logging
from pathlib import Path
from src.core.config_manager import ConfigManager

def migrate_database():
    """データベースのマイグレーションを実行する"""
    logger = logging.getLogger(__name__)
    config = ConfigManager()
    db_path = Path(config.get_paths()["db_path"])

    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # 一時テーブルの作成
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS analysis_results_new (
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

            # 既存データの移行
            cursor.execute("""
            INSERT INTO analysis_results_new (
                id, video_id, result_json, version, created_at
            )
            SELECT id, video_id, result_json, version, created_at
            FROM analysis_results
            """)

            # 古いテーブルの削除
            cursor.execute("DROP TABLE analysis_results")

            # 新しいテーブルの名前を変更
            cursor.execute("ALTER TABLE analysis_results_new RENAME TO analysis_results")

            conn.commit()
            logger.info("データベースのマイグレーションが完了しました")

    except Exception as e:
        logger.error(f"マイグレーション中にエラーが発生しました: {str(e)}")
        raise

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    migrate_database() 