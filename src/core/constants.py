from enum import Enum, auto

class VideoStatus(Enum):
    """動画の処理状態を表す列挙型"""
    UNPROCESSED = "UNPROCESSED"  # 未処理
    PENDING = "PENDING"      # 処理待ち
    PROCESSING = "PROCESSING"    # 処理中
    FIX = "FIX"                 # 完了
    ERROR = "ERROR"             # エラー
    CANCELED = "CANCELED"       # キャンセル

    @classmethod
    def get_default(cls) -> str:
        """デフォルトのステータスを取得"""
        return cls.UNPROCESSED.value

    @classmethod
    def is_valid(cls, status: str) -> bool:
        """有効なステータスかどうかを確認"""
        return status in [member.value for member in cls] 