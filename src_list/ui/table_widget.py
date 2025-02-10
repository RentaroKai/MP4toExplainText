from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
from PySide6.QtCore import Qt, Signal
from typing import List, Dict, Any
from src_list.models.table_item import TableItem

class CustomTableWidget(QTableWidget):
    tag_edited = Signal(int, list)  # video_id, new_tags

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._current_items = []

    def _setup_ui(self):
        """テーブルUIの初期設定"""
        # カラム設定
        columns = [
            "ID", "ファイル名", "ステータス", "進捗",
            "性別", "年齢層", "体型", "タグ",
            "作成日時", "更新日時"
        ]
        self.setColumnCount(len(columns))
        self.setHorizontalHeaderLabels(columns)

        # カラムの幅を設定
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # ID
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # ファイル名
        header.setSectionResizeMode(7, QHeaderView.Stretch)  # タグ
        
        # その他の設定
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)

    def update_data(self, items: List[TableItem]):
        """
        テーブルデータを更新
        Args:
            items (List[TableItem]): 表示するアイテムのリスト
        """
        self._current_items = items
        self.setRowCount(len(items))
        
        for row, item in enumerate(items):
            # 各カラムにデータを設定
            self.setItem(row, 0, self._create_item(str(item.id)))
            self.setItem(row, 1, self._create_item(item.file_name))
            self.setItem(row, 2, self._create_item(item.status))
            self.setItem(row, 3, self._create_item(str(item.progress)))
            self.setItem(row, 4, self._create_item(item.character_gender or ''))
            self.setItem(row, 5, self._create_item(item.character_age_group or ''))
            self.setItem(row, 6, self._create_item(item.character_body_type or ''))
            self.setItem(row, 7, self._create_item(', '.join(item.tags) if item.tags else ''))
            self.setItem(row, 8, self._create_item(item.created_at.strftime('%Y-%m-%d %H:%M:%S')))
            self.setItem(row, 9, self._create_item(item.updated_at.strftime('%Y-%m-%d %H:%M:%S')))

    def _create_item(self, text: str) -> QTableWidgetItem:
        """
        テーブルアイテムを作成
        Args:
            text (str): 表示するテキスト
        Returns:
            QTableWidgetItem: 作成されたアイテム
        """
        item = QTableWidgetItem(text)
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)  # 編集不可に設定
        return item

    def edit_tags(self, row: int):
        """
        指定行のタグを編集モードに
        Args:
            row (int): 編集する行
        """
        item = self.item(row, 7)
        if item:
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            self.editItem(item)

    def on_item_changed(self, item):
        """
        アイテムが変更された時の処理
        Args:
            item (QTableWidgetItem): 変更されたアイテム
        """
        if item.column() == 7:  # タグカラム
            row = item.row()
            video_id = int(self.item(row, 0).text())
            new_tags = [tag.strip() for tag in item.text().split(',') if tag.strip()]
            self.tag_edited.emit(video_id, new_tags)
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)  # 編集モードを解除 