from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
from PySide6.QtCore import Qt, Signal
from typing import List, Dict, Any
from ..models.table_item import TableItem

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
            "ID", "ファイル名", 
            "性別", "年齢層", "体型",
            "シーン", "強度", "テンポ", "ループ可能",
            "その他タグ"
        ]
        self.setColumnCount(len(columns))
        self.setHorizontalHeaderLabels(columns)

        # カラムの幅を設定
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # ID
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # ファイル名
        for i in range(2, 9):  # 性別からループ可能まで
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(9, QHeaderView.Stretch)  # その他タグ
        
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
            # 基本情報
            self.setItem(row, 0, self._create_item(str(item.id)))
            self.setItem(row, 1, self._create_item(item.file_name))
            self.setItem(row, 2, self._create_item(item.character_gender or ''))
            self.setItem(row, 3, self._create_item(item.character_age_group or ''))
            self.setItem(row, 4, self._create_item(item.character_body_type or ''))

            # タグから情報を抽出
            scene = ''
            intensity = ''
            tempo = ''
            loopable = ''
            other_tags = []

            if item.tags:
                for tag in item.tags:
                    if tag.startswith('scene:'):
                        scene = tag.replace('scene:', '')
                    elif tag.startswith('intensity:'):
                        intensity = tag.replace('intensity:', '')
                    elif tag.startswith('tempo:'):
                        tempo = tag.replace('tempo:', '')
                    elif tag.startswith('loopable:'):
                        loopable = tag.replace('loopable:', '')
                    else:
                        other_tags.append(tag)

            # 抽出した情報を設定
            self.setItem(row, 5, self._create_item(scene))
            self.setItem(row, 6, self._create_item(intensity))
            self.setItem(row, 7, self._create_item(tempo))
            self.setItem(row, 8, self._create_item(loopable))
            self.setItem(row, 9, self._create_item(', '.join(other_tags)))

            # ツールチップを設定（動作の詳細情報を表示）
            if item.movement_description or item.posture_detail:
                tooltip = []
                if item.movement_description:
                    tooltip.append(f"動作概要: {item.movement_description}")
                if item.posture_detail:
                    tooltip.append(f"姿勢詳細: {item.posture_detail}")
                if item.initial_pose:
                    tooltip.append(f"開始姿勢: {item.initial_pose}")
                if item.final_pose:
                    tooltip.append(f"終了姿勢: {item.final_pose}")
                
                for col in range(self.columnCount()):
                    cell_item = self.item(row, col)
                    if cell_item:
                        cell_item.setToolTip('\n'.join(tooltip))

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
        item = self.item(row, 9)  # その他タグカラム
        if item:
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            self.editItem(item)

    def on_item_changed(self, item):
        """
        アイテムが変更された時の処理
        Args:
            item (QTableWidgetItem): 変更されたアイテム
        """
        if item.column() == 9:  # その他タグカラム
            row = item.row()
            video_id = int(self.item(row, 0).text())
            # 既存のタグを保持
            scene = f"scene:{self.item(row, 5).text()}" if self.item(row, 5).text() else ''
            intensity = f"intensity:{self.item(row, 6).text()}" if self.item(row, 6).text() else ''
            tempo = f"tempo:{self.item(row, 7).text()}" if self.item(row, 7).text() else ''
            loopable = f"loopable:{self.item(row, 8).text()}" if self.item(row, 8).text() else ''
            
            # その他タグを追加
            other_tags = [tag.strip() for tag in item.text().split(',') if tag.strip()]
            
            # すべてのタグを結合
            new_tags = [tag for tag in [scene, intensity, tempo, loopable] + other_tags if tag]
            
            self.tag_edited.emit(video_id, new_tags)
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)  # 編集モードを解除 