from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel, QMessageBox,
    QFileDialog
)
from PySide6.QtCore import Qt
from .table_widget import CustomTableWidget
from ..core.data_manager import DataManager
from ..models.table_item import TableItem
import os
import logging
import datetime

class MainWindow(QMainWindow):
    def __init__(self, db_path=None):
        super().__init__()
        
        # ログ設定
        self._setup_logging()
        
        self.setWindowTitle("モーションリスト管理")
        self.setGeometry(100, 100, 1200, 800)
        
        # データマネージャーの初期化
        self.data_manager = None
        
        # UIの初期化
        self._setup_ui()
        
        # データベース接続
        if db_path:
            self._connect_database(db_path)

    def _setup_logging(self):
        """ログ設定を初期化"""
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        log_file = os.path.join(log_dir, f"motion_list_{datetime.datetime.now().strftime('%Y%m%d')}.log")
        
        # ログフォーマットの設定
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # ファイルハンドラの設定
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        
        # コンソールハンドラの設定
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO)
        
        # ルートロガーの設定
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
        
        # このクラス用のロガー
        self.logger = logging.getLogger(__name__)
        self.logger.info("ログ設定を初期化しました")

    def _setup_ui(self):
        """UIの初期設定"""
        # メインウィジェット
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # 上部コントロール
        control_layout = QHBoxLayout()
        
        # データベース接続ボタン
        self.connect_db_btn = QPushButton("DB接続")
        self.connect_db_btn.clicked.connect(self._connect_database)
        control_layout.addWidget(self.connect_db_btn)
        
        # 検索ボックス
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("ファイル名またはタグで検索...")
        self.search_box.textChanged.connect(self._on_search)
        control_layout.addWidget(self.search_box)
        
        # 更新ボタン
        refresh_btn = QPushButton("更新")
        refresh_btn.clicked.connect(self._refresh_data)
        control_layout.addWidget(refresh_btn)
        
        layout.addLayout(control_layout)

        # テーブル
        self.table = CustomTableWidget()
        self.table.doubleClicked.connect(self._on_table_double_clicked)
        self.table.tag_edited.connect(self._on_tag_edited)
        self.table.character_info_edited.connect(self._on_character_info_edited)
        layout.addWidget(self.table)

        # ステータスバー
        self.statusBar().showMessage("準備完了")

    def _connect_database(self, db_path=None):
        """
        データベースに接続
        Args:
            db_path (str, optional): データベースファイルのパス
        """
        try:
            if not db_path:
                # データベースファイルを選択
                db_path, _ = QFileDialog.getOpenFileName(
                    self,
                    "データベースファイルを選択",
                    "",
                    "SQLite DB (*.db);;All Files (*)"
                )
            
            if db_path:
                self.data_manager = DataManager(db_path)
                self._refresh_data()
                self.statusBar().showMessage(f"データベース接続成功: {db_path}")
                self.connect_db_btn.setEnabled(False)
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "エラー",
                f"データベース接続エラー: {str(e)}"
            )

    def _refresh_data(self):
        """データを更新"""
        if self.data_manager:
            try:
                print("=== データ更新開始 ===")
                print(f"更新前の選択行: {[item.row() for item in self.table.selectedItems()]}")
                videos = self.data_manager.load_all_videos()
                items = [TableItem.from_dict(video) for video in videos]
                self.table.update_data(items)
                print(f"更新後の選択行: {[item.row() for item in self.table.selectedItems()]}")
                self.statusBar().showMessage("データ更新完了")
                print("=== データ更新完了 ===")
            except Exception as e:
                print(f"データ更新エラー: {str(e)}")
                QMessageBox.warning(
                    self,
                    "警告",
                    f"データ更新エラー: {str(e)}"
                )

    def _on_search(self, text: str):
        """
        検索実行
        Args:
            text (str): 検索テキスト
        """
        if self.data_manager:
            results = self.data_manager.search_videos(text)
            items = [TableItem.from_dict(result) for result in results]
            self.table.update_data(items)

    def _on_table_double_clicked(self, index):
        """
        テーブルダブルクリック時の処理
        Args:
            index (QModelIndex): クリックされた位置
        """
        column = index.column()
        if column in [5, 6, 7, 8, 9, 10, 11, 12]:  # シーン、強度、テンポ、ループ可能、動作概要、姿勢詳細、開始姿勢、終了姿勢
            item = self.table.item(index.row(), column)
            if item:
                item.setFlags(item.flags() | Qt.ItemIsEditable)
                self.table.editItem(item)
        elif column == 13:  # その他タグ
            self.table.edit_tags(index.row())

    def _on_tag_edited(self, video_id: int, new_tags: list):
        """
        タグ編集時の処理
        Args:
            video_id (int): 動画ID
            new_tags (list): 新しいタグリスト
        """
        print(f"=== タグ編集開始: video_id={video_id} ===")
        print(f"編集前の選択行: {[item.row() for item in self.table.selectedItems()]}")
        if self.data_manager:
            success = self.data_manager.update_video_tags(video_id, new_tags)
            if success:
                print("タグ更新成功")
                self.statusBar().showMessage("タグを更新しました")
            else:
                print("タグ更新失敗")
                QMessageBox.warning(
                    self,
                    "警告",
                    "タグの更新に失敗しました"
                )
        print(f"編集後の選択行: {[item.row() for item in self.table.selectedItems()]}")
        print("=== タグ編集完了 ===")

    def _on_character_info_edited(self, video_id: int, gender: str, age_group: str, body_type: str):
        """
        キャラクター情報が編集された時の処理
        Args:
            video_id (int): 動画ID
            gender (str): 性別
            age_group (str): 年齢層
            body_type (str): 体型
        """
        if self.data_manager:
            success = self.data_manager.update_character_info(video_id, gender, age_group, body_type)
            if success:
                self.statusBar().showMessage("キャラクター情報を更新しました")
            else:
                QMessageBox.warning(
                    self,
                    "警告",
                    "キャラクター情報の更新に失敗しました"
                ) 