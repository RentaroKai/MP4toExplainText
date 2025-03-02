from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
from PySide6.QtCore import Qt, Signal
from typing import List, Dict, Any
from ..models.table_item import TableItem
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class CustomTableWidget(QTableWidget):
    tag_edited = Signal(int, list)  # video_id, new_tags
    character_info_edited = Signal(int, str, str, str)  # video_id, gender, age_group, body_type

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._current_items = []
        self.itemChanged.connect(self.on_item_changed)

    def _setup_ui(self):
        """テーブルUIの初期設定"""
        # カラム設定
        columns = [
            "ID", "ファイル名", 
            "性別", "年齢層", "体型",
            "シーン", "強度", "テンポ", "ループ可能",
            "動作概要", "姿勢詳細",
            "開始姿勢", "終了姿勢",
            "アニメーションファイル名",
            "カスタム1", "カスタム2", "カスタム3",  # 新しいカラム
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
        for i in range(9, 13):  # 動作概要から終了姿勢まで
            header.setSectionResizeMode(i, QHeaderView.Interactive)  # ユーザーが幅を調整可能
        header.setSectionResizeMode(13, QHeaderView.ResizeToContents)  # アニメーションファイル名
        for i in range(14, 17):  # カスタムパラメータ1〜3
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(17, QHeaderView.Stretch)  # その他タグ
        
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
        current_time = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        print(f"=== テーブル更新開始 [{current_time}] ===")
        print(f"現在選択されている行: {[item.row() for item in self.selectedItems()]}")
        
        # ソート機能を一時的に無効化
        self.setSortingEnabled(False)
        
        # シグナルを一時的に切断
        self.itemChanged.disconnect(self.on_item_changed)
        
        self._current_items = items
        self.setRowCount(len(items))
        
        try:
            for row, item in enumerate(items):
                # 基本情報
                self.setItem(row, 0, self._create_item(str(item.id)))
                self.setItem(row, 1, self._create_item(item.file_name))
                # 性別、年齢、体型は編集可能に
                self.setItem(row, 2, self._create_item(item.character_gender or '', True))
                self.setItem(row, 3, self._create_item(item.character_age_group or '', True))
                self.setItem(row, 4, self._create_item(item.character_body_type or '', True))

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
                self.setItem(row, 9, self._create_item(item.movement_description or ''))
                self.setItem(row, 10, self._create_item(item.posture_detail or ''))
                self.setItem(row, 11, self._create_item(item.initial_pose or ''))
                self.setItem(row, 12, self._create_item(item.final_pose or ''))
                self.setItem(row, 13, self._create_item(item.animation_file_name or ''))
                self.setItem(row, 14, self._create_item(item.param_01 or '', True))
                self.setItem(row, 15, self._create_item(item.param_02 or '', True))
                self.setItem(row, 16, self._create_item(item.param_03 or '', True))
                self.setItem(row, 17, self._create_item(', '.join(other_tags)))
        finally:
            current_time = datetime.now().strftime('%H:%M:%S.%f')[:-3]
            print(f"=== テーブル更新完了 [{current_time}] ===")
            print(f"更新後の選択されている行: {[item.row() for item in self.selectedItems()]}")
            # シグナルを再接続
            self.itemChanged.connect(self.on_item_changed)
            # ソート機能を再度有効化
            self.setSortingEnabled(True)

    def _create_item(self, text: str, editable: bool = False) -> QTableWidgetItem:
        """
        テーブルアイテムを作成
        Args:
            text (str): 表示するテキスト
            editable (bool): 編集可能かどうか
        Returns:
            QTableWidgetItem: 作成されたアイテム
        """
        item = QTableWidgetItem(text)
        if not editable:
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        return item

    def edit_tags(self, row: int):
        """
        指定行のタグを編集モードに
        Args:
            row (int): 編集する行
        """
        item = self.item(row, 14)  # その他タグカラム
        if item:
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            self.editItem(item)

    def on_item_changed(self, item):
        """
        アイテムが変更された時の処理
        Args:
            item (QTableWidgetItem): 変更されたアイテム
        """
        if not item:
            return
            
        row = item.row()
        column = item.column()
        
        if column in [2, 3, 4]:  # 性別、年齢、体型の列
            try:
                video_id = int(self.item(row, 0).text() if self.item(row, 0) else 0)
                if video_id == 0:
                    return
                    
                # 現在の値を取得（Noneの場合は空文字を使用）
                gender = self.item(row, 2).text() if self.item(row, 2) else ''
                age_group = self.item(row, 3).text() if self.item(row, 3) else ''
                body_type = self.item(row, 4).text() if self.item(row, 4) else ''
                
                # 編集された列の値を更新
                if column == 2:
                    gender = item.text()
                elif column == 3:
                    age_group = item.text()
                elif column == 4:
                    body_type = item.text()
                
                print(f"キャラクター情報を更新: ID={video_id}, 性別={gender}, 年齢={age_group}, 体型={body_type}")
                self.character_info_edited.emit(video_id, gender, age_group, body_type)
                
            except (ValueError, AttributeError) as e:
                print(f"キャラクター情報の更新中にエラーが発生: {e}")
            
        elif column == 14:  # その他タグカラム
            try:
                video_id = int(self.item(row, 0).text() if self.item(row, 0) else 0)
                if video_id == 0:
                    return
                    
                # 既存のタグを保持
                scene = f"scene:{self.item(row, 5).text()}" if self.item(row, 5) and self.item(row, 5).text() else ''
                intensity = f"intensity:{self.item(row, 6).text()}" if self.item(row, 6) and self.item(row, 6).text() else ''
                tempo = f"tempo:{self.item(row, 7).text()}" if self.item(row, 7) and self.item(row, 7).text() else ''
                loopable = f"loopable:{self.item(row, 8).text()}" if self.item(row, 8) and self.item(row, 8).text() else ''
                
                # その他タグを追加
                other_tags = [tag.strip() for tag in item.text().split(',') if tag.strip()]
                
                # すべてのタグを結合
                new_tags = [tag for tag in [scene, intensity, tempo, loopable] + other_tags if tag]
                
                print(f"タグを更新: ID={video_id}, タグ={new_tags}")
                self.tag_edited.emit(video_id, new_tags)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)  # 編集モードを解除
                
            except (ValueError, AttributeError) as e:
                print(f"タグの更新中にエラーが発生: {e}") 

    def refresh_table(self):
        """テーブルの定期更新"""
        try:
            current_time = datetime.now().strftime('%H:%M:%S.%f')[:-3]
            print(f"=== テーブル再描画開始 [{current_time}] ===")
            print(f"再描画前の選択行: {[item.row() for item in self.selectedItems()]}")
            videos = self.db.get_all_videos()
            
            # 現在のテーブルの状態を保存
            selected_rows = [item.row() for item in self.selectedItems()]
            scroll_position = self.table.verticalScrollBar().value()
            
            print(f"保存した選択行: {selected_rows}")
            self.update_data(videos)
            
            # 選択状態を復元
            for row in selected_rows:
                if row < self.table.rowCount():
                    self.table.selectRow(row)
            
            print(f"再描画後の選択行: {[item.row() for item in self.selectedItems()]}")
            # スクロール位置を復元
            self.table.verticalScrollBar().setValue(scroll_position)
        except Exception as e:
            print(f"テーブルの再描画中にエラーが発生: {e}") 