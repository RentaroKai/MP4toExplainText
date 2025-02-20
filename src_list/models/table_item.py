from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

# ロガーの設定
logger = logging.getLogger(__name__)

@dataclass
class TableItem:
    """テーブル表示用のデータモデル"""
    id: int
    file_path: str
    file_name: str
    character_gender: Optional[str] = None
    character_age_group: Optional[str] = None
    character_body_type: Optional[str] = None
    scene: Optional[str] = None
    movement_description: Optional[str] = None
    posture_detail: Optional[str] = None
    initial_pose: Optional[str] = None
    final_pose: Optional[str] = None
    intensity: Optional[str] = None
    tempo: Optional[str] = None
    loopable: Optional[str] = None
    animation_file_name: Optional[str] = None
    tags: List[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TableItem':
        """
        辞書からTableItemインスタンスを作成
        Args:
            data (Dict[str, Any]): データベースから取得した辞書データ
        Returns:
            TableItem: 新しいTableItemインスタンス
        """
        logger.info("=== TableItem変換開始 ===")
        logger.info(f"入力データ型: {type(data)}")
        logger.info(f"入力データ: {data}")
        
        if not isinstance(data, dict):
            logger.error(f"入力データが辞書型ではありません: {type(data)}")
            return None
        
        # タグ文字列を配列に変換
        tags = []
        try:
            if isinstance(data.get('tags'), str):
                tags = [tag.strip() for tag in data['tags'].split(',') if tag.strip()]
                logger.info(f"変換後のタグ: {tags}")
            else:
                logger.warning(f"タグデータが文字列ではありません: {type(data.get('tags'))}")
        except Exception as e:
            logger.error(f"タグ変換中にエラーが発生: {str(e)}")

        # 動作関連の情報をJSONから取得
        result_json = {}
        try:
            result_json_raw = data.get('result_json')
            logger.info(f"生のresult_json: {result_json_raw}")
            logger.info(f"result_jsonの型: {type(result_json_raw)}")

            if isinstance(result_json_raw, str):
                import json
                try:
                    # シングルクォートをダブルクォートに置換して解析
                    result_json_str = result_json_raw.replace("'", '"')
                    logger.info(f"JSON解析前の文字列: {result_json_str}")
                    
                    parsed_json = json.loads(result_json_str)
                    logger.info(f"JSON解析結果: {parsed_json}")
                    
                    # リストの場合は最初の要素を使用
                    if isinstance(parsed_json, list):
                        logger.info("JSONがリスト形式です。最初の要素を使用します。")
                        result_json = parsed_json[0] if parsed_json else {}
                    else:
                        result_json = parsed_json
                    
                except json.JSONDecodeError as e:
                    logger.error(f"JSON解析エラー: {str(e)}")
                    logger.error(f"解析対象の文字列: {result_json_raw}")
            else:
                logger.warning(f"result_jsonが文字列ではありません: {type(result_json_raw)}")

        except Exception as e:
            logger.error(f"result_json処理中に予期せぬエラーが発生: {str(e)}")

        logger.info(f"解析後のResult JSON: {result_json}")
        logger.info(f"キャラクター情報: gender={data.get('character_gender')}, age={data.get('character_age_group')}, body={data.get('character_body_type')}")

        try:
            instance = cls(
                id=data.get('id', 0),
                file_path=data.get('file_path', ''),
                file_name=data.get('file_name', ''),
                character_gender=data.get('character_gender'),
                character_age_group=data.get('character_age_group'),
                character_body_type=data.get('character_body_type'),
                # 動作関連の情報を正しく取得
                scene=result_json.get('Appropriate Scene', ''),
                movement_description=result_json.get('Overall Movement Description', ''),
                posture_detail=result_json.get('Posture Detail', ''),
                initial_pose=result_json.get('Initial Pose', ''),
                final_pose=result_json.get('Final Pose', ''),
                intensity=result_json.get('Intensity Force', ''),
                tempo=result_json.get('Tempo Speed', ''),
                loopable=result_json.get('Loopable', ''),
                animation_file_name=result_json.get('Name of AnimationFile', ''),
                tags=tags
            )
            logger.info(f"生成されたインスタンス: {instance}")
            return instance
        except Exception as e:
            logger.error(f"インスタンス生成中にエラーが発生: {str(e)}")
            return None

    def to_dict(self) -> Dict[str, Any]:
        """
        TableItemインスタンスを辞書に変換
        Returns:
            Dict[str, Any]: 辞書形式のデータ
        """
        try:
            return {
                'id': self.id,
                'file_path': self.file_path,
                'file_name': self.file_name,
                'character_gender': self.character_gender,
                'character_age_group': self.character_age_group,
                'character_body_type': self.character_body_type,
                'scene': self.scene,
                'movement_description': self.movement_description,
                'posture_detail': self.posture_detail,
                'initial_pose': self.initial_pose,
                'final_pose': self.final_pose,
                'intensity': self.intensity,
                'tempo': self.tempo,
                'loopable': self.loopable,
                'animation_file_name': self.animation_file_name,
                'tags': ','.join(self.tags) if self.tags else ''
            }
        except Exception as e:
            logger.error(f"辞書変換中にエラーが発生: {str(e)}")
            return {} 