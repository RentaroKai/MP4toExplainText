from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

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
        # タグ文字列を配列に変換
        tags = data.get('tags', '').split(',') if data.get('tags') else []
        tags = [tag.strip() for tag in tags if tag.strip()]

        # 動作関連の情報をJSONから取得
        result_json = data.get('result_json', '{}')
        if isinstance(result_json, str):
            import json
            try:
                # シングルクォートをダブルクォートに置換して解析
                result_json = result_json.replace("'", '"')
                result_json = json.loads(result_json)
            except json.JSONDecodeError as e:
                print(f"JSON解析エラー: {e}")
                print(f"解析対象の文字列: {result_json}")
                result_json = {}

        # デバッグ用：result_jsonの内容を確認
        print(f"解析後のResult JSON: {result_json}")

        return cls(
            id=data['id'],
            file_path=data['file_path'],
            file_name=data['file_name'],
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

    def to_dict(self) -> Dict[str, Any]:
        """
        TableItemインスタンスを辞書に変換
        Returns:
            Dict[str, Any]: 辞書形式のデータ
        """
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