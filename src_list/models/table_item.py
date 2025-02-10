from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class TableItem:
    """テーブル表示用のデータモデル"""
    id: int
    file_path: str
    file_name: str
    status: str
    progress: int
    created_at: datetime
    updated_at: datetime
    character_gender: Optional[str] = None
    character_age_group: Optional[str] = None
    character_body_type: Optional[str] = None
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

        # 日時文字列をdatetimeオブジェクトに変換
        created_at = datetime.strptime(data['created_at'], '%Y-%m-%d %H:%M:%S')
        updated_at = datetime.strptime(data['updated_at'], '%Y-%m-%d %H:%M:%S')

        return cls(
            id=data['id'],
            file_path=data['file_path'],
            file_name=data['file_name'],
            status=data['status'],
            progress=data['progress'],
            created_at=created_at,
            updated_at=updated_at,
            character_gender=data.get('character_gender'),
            character_age_group=data.get('character_age_group'),
            character_body_type=data.get('character_body_type'),
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
            'status': self.status,
            'progress': self.progress,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
            'character_gender': self.character_gender,
            'character_age_group': self.character_age_group,
            'character_body_type': self.character_body_type,
            'tags': ','.join(self.tags) if self.tags else ''
        } 