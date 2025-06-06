import os
import logging
import asyncio
import threading
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QCheckBox, QTableWidget, QTableWidgetItem,
    QLabel, QProgressBar, QFileDialog, QMessageBox,
    QMenuBar, QMenu, QInputDialog, QDialog, QLineEdit, QDialogButtonBox,
    QComboBox, QAbstractItemView
)
from PySide6.QtCore import Qt, QMimeData, Signal, QObject, QTimer
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QAction
from src.core.config_manager import ConfigManager
from src.core.video_processor import VideoProcessor
from src.core.database import Database
from src.core.export_manager import ExportManager
from src.core.prompt_manager import PromptManager
from src.core.constants import VideoStatus  # VideoStatusをインポート
from typing import List
from src_list.ui.main_window import MainWindow as MotionListWindow
class SignalEmitter(QObject):
    """非同期処理からのシグナルを発行するためのクラス"""
    progress_updated = Signal(int, int)  # video_id, progress
    status_updated = Signal(int, str)    # video_id, status
    error_occurred = Signal(str)         # error_message
    database_changed = Signal()          # データベース変更シグナル（新規追加）
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.config = ConfigManager()
        
        # データの初期化
        self.signal_emitter = SignalEmitter()
        self.db = Database(self.config.get_active_database())
        self.logger.info(f"データベースを初期化しました: {self.db.get_database_path()}")
        
        self.export_manager = ExportManager(self.config, self.db)
        self.logger.info(f"ExportManagerを初期化しました。DB: {self.db.get_database_path()}")
        
        self.processor = VideoProcessor(self.db)
        self.prompt_manager = PromptManager()
        self.current_filter = ""  # フィルタ文字列を保持
        
        self.signal_emitter.progress_updated.connect(self.update_progress)
        self.signal_emitter.status_updated.connect(self.update_status)
        self.signal_emitter.error_occurred.connect(self.show_error)
        self.signal_emitter.database_changed.connect(self.refresh_after_db_change)
        
        self.update_window_title()
        
        self.setMinimumSize(800, 600)
        
        self.setup_menu_bar()
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        self.setup_prompt_selector(layout)
        self.setup_drag_drop_area(layout)
        self.setup_filter_area(layout)  # フィルタエリアを追加
        self.setup_auto_process_switch(layout)
        self.setup_table_view(layout)
        self.setup_batch_operations(layout)
        self.setup_export_buttons(layout)
        
        self.setAcceptDrops(True)
        
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        self.loop_thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self.loop_thread.start()
        
        self.load_initial_data()
        
        self.logger.info("メインウィンドウの初期化が完了しました")
    
    def _run_event_loop(self):
        """イベントループを実行"""
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()
    
    def load_initial_data(self):
        """初期データの読み込み"""
        try:
            videos = self.db.get_all_videos()
            for video in videos:
                self.add_video_to_table(
                    video["file_path"],
                    video["id"],
                    video["status"],
                    video["progress"],
                    video["tags"]  # タグ情報を追加
                )
        except Exception as e:
            self.logger.error(f"初期データの読み込み中にエラーが発生しました: {str(e)}")
            self.show_error("データの読み込みに失敗しました")
    
    def setup_prompt_selector(self, layout):
        """プロンプト設定選択用のコンボボックスを設定"""
        prompt_layout = QHBoxLayout()
        
        label = QLabel("Prompt Settings:")
        prompt_layout.addWidget(label)
        
        self.prompt_combo = QComboBox()
        self.update_prompt_list()
        self.prompt_combo.currentTextChanged.connect(self.on_prompt_changed)
        prompt_layout.addWidget(self.prompt_combo)
        
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.update_prompt_list)
        prompt_layout.addWidget(refresh_button)
        
        edit_button = QPushButton("Edit")
        edit_button.clicked.connect(self.open_prompt_json_in_editor)
        prompt_layout.addWidget(edit_button)
        
        prompt_layout.addStretch()
        
        layout.addLayout(prompt_layout)
    
    def update_prompt_list(self):
        """プロンプト設定の一覧を更新"""
        current = self.prompt_combo.currentText()
        self.prompt_combo.clear()
        
        configs = self.prompt_manager.get_available_configs()
        self.logger.info(f"利用可能なプロンプト設定: {configs}")
        self.prompt_combo.addItems(configs)
        
        # 以前選択されていた項目があれば復元
        if current in configs:
            self.prompt_combo.setCurrentText(current)
            self.logger.info(f"以前の設定を復元: {current}")
        elif "default" in configs:
            self.prompt_combo.setCurrentText("default")
            self.logger.info("デフォルト設定を選択")
    
    def on_prompt_changed(self, config_name: str):
        """プロンプト設定が変更された時の処理"""
        self.logger.info(f"プロンプト設定が変更されました: {config_name}")
        try:
            self.prompt_manager.load_config(config_name)
            self.processor.set_prompt_config(config_name)  # VideoProcessorに設定を通知
            self.logger.info(f"プロンプト設定を変更: {config_name}")
        except Exception as e:
            self.logger.error(f"プロンプト設定の読み込みに失敗: {str(e)}")
            self.show_error(f"プロンプト設定の読み込みに失敗しました:\n{str(e)}")
    
    def open_prompt_json_in_editor(self):
        """現在選択されているプロンプトのJSONファイルをデフォルトエディタで開く"""
        config_name = self.prompt_combo.currentText()
        if not config_name:
            self.logger.warning("編集するプロンプトが選択されていません。")
            return

        try:
            config_path = self.prompt_manager.get_config_path(config_name)
            if config_path and config_path.exists():
                self.logger.info(f"プロンプト設定ファイルを開きます: {config_path}")
                os.startfile(config_path)
            else:
                self.logger.error(f"プロンプト設定ファイルが見つかりません: {config_name}")
                self.show_error(f"設定ファイルが見つかりません:\n{config_path}")
        except Exception as e:
            self.logger.error(f"プロンプト設定ファイルのオープン中にエラーが発生しました: {str(e)}")
            self.show_error(f"ファイルのオープンに失敗しました:\n{str(e)}")
    
    def setup_drag_drop_area(self, parent_layout):
        """ドラッグ＆ドロップエリアの設定"""
        drop_area = QLabel("Drop Video Files Here")
        drop_area.setAlignment(Qt.AlignCenter)
        drop_area.setStyleSheet("""
            QLabel {
                border: 2px dashed #4a90e2;
                border-radius: 8px;
                padding: 30px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                          stop:0 #ffffff, stop:1 #f5f8fa);
                color: #1e3a5f;
                font-size: 14px;
                font-weight: bold;
            }
            QLabel:hover {
                border-color: #2980b9;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                          stop:0 #f5f8fa, stop:1 #e8f1f8);
                color: #0d2b4d;
            }
        """)
        drop_area.setMinimumHeight(120)
        
        # ファイル選択ボタンのスタイルも更新
        select_button = QPushButton("Choose Files...")
        select_button.setStyleSheet("""
            QPushButton {
                background: #4a90e2;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: #357abd;
            }
            QPushButton:pressed {
                background: #2980b9;
            }
        """)
        select_button.clicked.connect(self.on_select_files)
        
        parent_layout.addWidget(drop_area)
        parent_layout.addWidget(select_button)
    
    def setup_filter_area(self, layout):
        """フィルタエリアの設定"""
        filter_layout = QHBoxLayout()
        
        # フィルタラベル
        filter_label = QLabel("Filter:")
        filter_layout.addWidget(filter_label)
        
        # フィルタ入力フィールド
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Enter filter text...")
        self.filter_input.textChanged.connect(self.apply_filter)
        filter_layout.addWidget(self.filter_input)
        
        # クリアボタン
        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(self.clear_filter)
        filter_layout.addWidget(clear_button)
        
        filter_layout.addStretch()
        layout.addLayout(filter_layout)

    def apply_filter(self):
        """フィルタを適用"""
        self.current_filter = self.filter_input.text().lower()
        self.refresh_table()

    def clear_filter(self):
        """フィルタをクリア"""
        self.filter_input.clear()
        self.current_filter = ""
        self.refresh_table()

    def setup_auto_process_switch(self, parent_layout):
        """自動処理スイッチの設定"""
        self.auto_process = QCheckBox("Start Processing Automatically")
        self.auto_process.setChecked(True)
        parent_layout.addWidget(self.auto_process)
    
    def setup_table_view(self, parent_layout):
        """テーブルビューの設定"""
        self.table = QTableWidget()
        # 行選択と複数選択を有効化
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.MultiSelection)
        # コンテキストメニューを有効化
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.open_table_context_menu)
        self.table.setColumnCount(6)  # カラム数を6に変更
        self.table.setHorizontalHeaderLabels([
            "Video Name", "Open", "Status", "Progress", "Tags", "Actions"  # "Open"カラムを追加
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        parent_layout.addWidget(self.table)
    
    def setup_batch_operations(self, parent_layout):
        """一括操作エリアの設定"""
        batch_layout = QHBoxLayout()
        
        # 一括処理ボタン
        process_button = QPushButton("▶Run Selected")
        process_button.clicked.connect(self.on_batch_process)
        
        # キャンセルボタン
        cancel_button = QPushButton("Stop")
        cancel_button.clicked.connect(self.on_cancel_process)
        
        batch_layout.addWidget(process_button)
        batch_layout.addWidget(cancel_button)
        parent_layout.addLayout(batch_layout)
    
    def setup_export_buttons(self, parent_layout):
        """エクスポートボタンの設定"""
        export_layout = QHBoxLayout()
        
        # CSVセクション
        csv_layout = QHBoxLayout()
        export_csv_btn = QPushButton("Export CSV")
        export_csv_btn.clicked.connect(self.export_to_csv)
        csv_layout.addWidget(export_csv_btn)
        
        open_csv_folder_btn = QPushButton("📁CSV")
        open_csv_folder_btn.clicked.connect(lambda: self.open_folder("csv"))
        open_csv_folder_btn.setToolTip("Open CSV Folder")
        csv_layout.addWidget(open_csv_folder_btn)
        export_layout.addLayout(csv_layout)
        
        # JSONセクション
        json_layout = QHBoxLayout()
        export_json_btn = QPushButton("Export JSON")
        export_json_btn.clicked.connect(self.export_to_json)
        json_layout.addWidget(export_json_btn)
        
        open_json_folder_btn = QPushButton("📁JSON")
        open_json_folder_btn.clicked.connect(lambda: self.open_folder("json"))
        open_json_folder_btn.setToolTip("Open JSON Folder")
        json_layout.addWidget(open_json_folder_btn)
        export_layout.addLayout(json_layout)
        
        parent_layout.addLayout(export_layout)
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """ドラッグエンターイベントの処理"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event: QDropEvent):
        """ドロップイベントの処理"""
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        self.process_dropped_files(files)
    
    def on_select_files(self):
        """ファイル選択ダイアログを表示"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Video Files",
            "",
            "Video Files (*.mp4 *.avi *.mov *.wmv);;All Files (*.*)"
        )
        if files:
            self.process_dropped_files(files)
    
    def process_dropped_files(self, files):
        """ドロップされたファイルの処理"""
        for file in files:
            self.logger.info(f"ファイルが追加されました: {file}")
            
            # 重複チェックを追加
            try:
                conn = self.db._get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM videos WHERE file_path = ?", (file,))
                existing = cursor.fetchone()
                conn.close()
                if existing:
                    video_id = existing[0]
                    self.logger.info(f"重複ファイル検出: {file} (video_id={video_id})")
                    QMessageBox.information(self, "情報", f"ファイル '{Path(file).name}' は既に追加されています。重複をスキップします。")
                    continue
            except Exception as e:
                self.logger.error(f"重複チェック中にエラーが発生しました: {str(e)}", exc_info=True)

            # データベースに追加
            try:
                video_id = self.db.add_video(file)
                self.add_video_to_table(file, video_id, "UNPROCESSED", 0, [])  # 空のタグリストを追加
                
                # 自動処理が有効な場合は処理を開始
                if self.auto_process.isChecked():
                    asyncio.run_coroutine_threadsafe(
                        self.process_video(video_id, file),
                        self.loop
                    )
                    
            except Exception as e:
                self.logger.error(f"ファイルの追加中にエラーが発生しました: {str(e)}")
                self.show_error(f"ファイルの追加に失敗しました: {file}")
    
    def add_video_to_table(self, file_path: str, video_id: int, status: str, progress: int, tags: list = None):
        """テーブルに新しいファイルを追加"""
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        # ファイル名
        self.table.setItem(row, 0, QTableWidgetItem(Path(file_path).name))
        self.table.item(row, 0).setData(Qt.UserRole, video_id)
        
        # 動画を開くボタン
        open_button = QPushButton("🎬")
        open_button.setToolTip("Open Video")
        open_button.clicked.connect(lambda: os.startfile(file_path))
        self.table.setCellWidget(row, 1, open_button)
        
        # 状態
        self.table.setItem(row, 2, QTableWidgetItem(status))
        
        # 進捗バー
        progress_bar = QProgressBar()
        progress_bar.setValue(progress)
        self.table.setCellWidget(row, 3, progress_bar)
        
        # タグの表示
        tag_text = ", ".join(tags) if tags else ""
        self.table.setItem(row, 4, QTableWidgetItem(tag_text))
        
        # 再処理ボタン
        reprocess_button = QPushButton("▶Run")
        reprocess_button.clicked.connect(lambda: self.on_reprocess(video_id, file_path))
        self.table.setCellWidget(row, 5, reprocess_button)
    
    async def process_video(self, video_id: int, file_path: str):
        """動画を非同期で処理"""
        try:
            await self.processor.process_video(
                file_path,
                lambda vid, prog: self.signal_emitter.progress_updated.emit(vid, prog),
                lambda vid, status: self.signal_emitter.status_updated.emit(vid, status)
            )
        except Exception as e:
            self.logger.error(f"動画の処理中にエラーが発生しました: {str(e)}")
            self.signal_emitter.error_occurred.emit(f"動画の処理に失敗しました: {file_path}")
    
    def update_progress(self, video_id: int, progress: int):
        """進捗バーの更新"""
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.data(Qt.UserRole) == video_id:
                progress_bar = self.table.cellWidget(row, 3)
                if progress_bar:
                    progress_bar.setValue(progress)
                break
    
    def update_status(self, video_id: int, status: str):
        """状態の更新"""
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.data(Qt.UserRole) == video_id:
                self.table.item(row, 2).setText(status)
                break
    
    def show_error(self, message: str):
        """エラーメッセージの表示"""
        QMessageBox.critical(self, "Error", message)
    
    def on_batch_process(self):
        """選択された動画を一括処理"""
        video_ids = self._get_selected_video_ids()
        if not video_ids:
            QMessageBox.warning(self, "Warning", "Please select videos to process.")
            return
        
        # APIキーが設定されているか確認
        api_key = self.config.get_api_key()
        if not api_key:
            result = QMessageBox.question(
                self, 
                "API Key Required",
                "Gemini API key is not set. Open the settings screen?",
                QMessageBox.Yes | QMessageBox.No
            )
            if result == QMessageBox.Yes:
                self.set_api_key()
            return
            
        # 一括処理の確認
        prompt_name = self.prompt_combo.currentText()  # プロンプトコンボボックスから現在の設定名を取得
        result = QMessageBox.question(
            self,
            "Batch Processing Confirmation", 
            f"Process selected {len(video_ids)} videos.\n"
            f"Current prompt setting: {prompt_name}\n\n"
            "Continue?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if result == QMessageBox.Yes:
            # 処理対象の動画パスを取得
            video_paths = []
            for video_id in video_ids:
                path = self.db.get_video_info(video_id)["file_path"]
                video_paths.append(path)
                
            # 非同期処理を開始
            asyncio.run_coroutine_threadsafe(
                self.processor.process_multiple_videos(
                    video_paths,
                    lambda vid, prog: self.signal_emitter.progress_updated.emit(vid, prog),
                    lambda vid, status: self.signal_emitter.status_updated.emit(vid, status)
                ),
                self.loop
            )
    
    def on_cancel_process(self):
        """選択された項目の処理をキャンセル"""
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            return
        
        for item in selected_rows:
            row = item.row()
            video_id = self.table.item(row, 0).data(Qt.UserRole)
            self.processor.cancel_processing(video_id)
    
    def on_reprocess(self, video_id: int, file_path: str):
        """動画の再処理"""
        try:
            # APIキーが設定されているか確認
            api_key = self.config.get_api_key()
            if not api_key:
                result = QMessageBox.question(
                    self, 
                    "API Key Required",
                    "Gemini API key is not set. Open the settings screen?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if result == QMessageBox.Yes:
                    self.set_api_key()
                return
            
            self.set_video_status(video_id, VideoStatus.PENDING.value)
            
            asyncio.run_coroutine_threadsafe(
                self.processor.process_video(
                    file_path, 
                    lambda vid, prog: self.signal_emitter.progress_updated.emit(vid, prog),
                    lambda vid, status: self.signal_emitter.status_updated.emit(vid, status)
                ),
                self.loop
            )
        except Exception as e:
            self.logger.error(f"動画の再処理中にエラーが発生しました: {str(e)}")
            QMessageBox.critical(self, "Error", f"動画の再処理に失敗しました: {str(e)}")
    
    def refresh_table(self):
        """テーブルの定期更新"""
        try:
            videos = self.db.get_all_videos()
            
            selected_rows = [item.row() for item in self.table.selectedItems()]
            scroll_position = self.table.verticalScrollBar().value()
            
            self.table.setRowCount(0)
            
            for video in videos:
                if self.current_filter in video["file_name"].lower():
                    self.add_video_to_table(
                        video["file_path"],
                        video["id"],
                        video["status"],
                        video["progress"],
                        video["tags"]  # タグ情報を追加
                    )
            
            for row in selected_rows:
                if row < self.table.rowCount():
                    self.table.selectRow(row)
            
            self.table.verticalScrollBar().setValue(scroll_position)
                        
        except Exception as e:
            self.logger.error(f"テーブルの更新中にエラーが発生しました: {str(e)}")
    
    def export_to_csv(self):
        """選択された項目をCSVにエクスポート"""
        try:
            self.logger.info(f"CSVエクスポート開始 - 使用DB: {self.db.get_database_path()}")
            video_ids = self._get_selected_video_ids()
            filepath = self.export_manager.export_to_csv(video_ids if video_ids else None)
            self.logger.info(f"CSVエクスポート完了: {filepath}")
            QMessageBox.information(
                self,
                "Information",
                f"CSV file created:\n{filepath}"
            )
            
        except Exception as e:
            self.logger.error(f"CSVエクスポート中にエラーが発生しました: {str(e)}")
            QMessageBox.critical(
                self,
                "Error",
                f"エクスポート中にエラーが発生しました:\n{str(e)}"
            )
    
    def export_to_json(self):
        """選択された項目をJSONにエクスポート"""
        try:
            video_ids = self._get_selected_video_ids()
            # 選択がない場合はNoneを渡して全件出力
            filepath = self.export_manager.export_to_json(video_ids if video_ids else None)
            QMessageBox.information(
                self,
                "Information",
                f"JSON file created:\n{filepath}"
            )
            
        except Exception as e:
            self.logger.error(f"JSONエクスポート中にエラーが発生しました: {str(e)}")
            QMessageBox.critical(
                self,
                "Error",
                f"エクスポート中にエラーが発生しました:\n{str(e)}"
            )
    
    def _get_selected_video_ids(self) -> List[int]:
        """選択された項目のvideo_idリストを取得"""
        video_ids = []
        processed_rows = set()
        
        for item in self.table.selectedItems():
            row = item.row()
            if row in processed_rows:
                continue
            
            try:
                video_id = self.table.item(row, 0).data(Qt.UserRole)
                if video_id is not None and video_id not in video_ids:
                    video_ids.append(video_id)
                processed_rows.add(row)
                
            except Exception as e:
                self.logger.error(f"行 {row} の処理中にエラーが発生: {str(e)}")
                continue
        
        return video_ids
    
    def closeEvent(self, event):
        """ウィンドウを閉じる際の処理"""
        self.config.set_active_database(self.db.get_database_path())
        
        if hasattr(self, "loop") and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
        
        super().closeEvent(event)

    def setup_menu_bar(self):
        """メニューバーの設定"""
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu("File")
        
        new_db_action = file_menu.addAction("New")
        new_db_action.triggered.connect(self.create_new_database)
        
        open_db_action = file_menu.addAction("Open")
        open_db_action.triggered.connect(self.open_database)
        
        self.recent_menu = QMenu("Recent Files", self)
        file_menu.addMenu(self.recent_menu)
        self.update_recent_files_menu()
        
        file_menu.addSeparator()
        
        close_db_action = file_menu.addAction("Close")
        close_db_action.triggered.connect(self.close_database)
        
        file_menu.addSeparator()
        
        exit_action = file_menu.addAction("Exit")
        exit_action.triggered.connect(self.close)
        
        settings_menu = menubar.addMenu("Settings")
        api_key_action = settings_menu.addAction("Set API Key")
        api_key_action.triggered.connect(self.set_api_key)
        model_action = settings_menu.addAction("Set Model")
        model_action.triggered.connect(self.set_model)
        
        window_menu = menubar.addMenu("Window")
        
        motion_list_action = window_menu.addAction("Open Motion List")
        motion_list_action.triggered.connect(self._open_motion_list)
        
        help_menu = menubar.addMenu("Help")
        about_action = help_menu.addAction("About")
        about_action.triggered.connect(self.show_about)
        help_action = help_menu.addAction("How to Use")
        help_action.triggered.connect(self.show_help)

    def set_api_key(self):
        """APIキーを設定するダイアログを表示"""
        current_key = self.config.get_api_key() or ""
        masked_key = "X" * len(current_key) if current_key else ""
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Set API Key")
        layout = QVBoxLayout()
        
        info_label = QLabel(
            "You can set your API key in two ways:\n"
            "1. Set environment variable 'GOOGLE_API_KEY' (recommended)\n"
            "2. Enter directly here\n\n"
            "Note: Environment variable takes priority"
        )
        layout.addWidget(info_label)
        
        input_field = QLineEdit(dialog)
        input_field.setPlaceholderText("Enter your API key here")
        input_field.setText(masked_key)
        layout.addWidget(input_field)
        
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        dialog.setLayout(layout)
        
        if dialog.exec() == QDialog.Accepted:
            new_key = input_field.text()
            if new_key and new_key != masked_key:
                self.config.set_api_key(new_key)
                QMessageBox.information(self, "Success", "API key saved.")

    def set_model(self):
        """Geminiモデル名を設定するダイアログを表示"""
        current_model = self.config.get_model_name()
        dialog = QDialog(self)
        dialog.setWindowTitle("Set Gemini Model")
        layout = QVBoxLayout()
        
        info_label = QLabel("Enter the Gemini model name:")
        layout.addWidget(info_label)
        
        input_field = QLineEdit(dialog)
        input_field.setPlaceholderText("e.g., gemini-2.5-pro-preview-05-06")
        input_field.setText(current_model)
        layout.addWidget(input_field)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        dialog.setLayout(layout)
        
        if dialog.exec() == QDialog.Accepted:
            new_model = input_field.text().strip()
            if new_model and new_model != current_model:
                try:
                    self.config.set_model_name(new_model)
                    # 新しいモデル名をGeminiAPIに反映
                    self.processor.gemini._setup_model()
                    QMessageBox.information(self, "Success", f"Model set to {new_model}")
                    self.logger.info(f"Gemini model updated to: {new_model}")
                except Exception as e:
                    self.logger.error(f"モデル設定エラー: {str(e)}")
                    QMessageBox.critical(self, "Error", f"モデル設定中にエラーが発生しました:\n{str(e)}")

    def show_about(self):
        """バージョン情報を表示"""
        QMessageBox.about(
            self,
            "About",
            "MP4toText - Video Tool\nVersion: 1.0.0\n© 2025 RentaroKai"
        )

    def show_help(self):
        """ヘルプ情報を表示"""
        help_text = """
How to Use:

1. Add videos by dropping files or clicking Choose Files
2. Turn on Auto Start to process videos automatically
3. Select videos and click Process Selected to analyze multiple videos
4. Save results as CSV or JSON

Visit our website for more help.
        """
        QMessageBox.information(self, "How to Use", help_text)

    def open_folder(self, folder_type: str):
        """指定されたフォルダをエクスプローラーで開く"""
        try:
            paths = self.config.get_paths()
            export_dir = Path(paths.get("export_dir", "./exports"))
            target_dir = export_dir / folder_type
            
            if not target_dir.exists():
                target_dir.mkdir(parents=True, exist_ok=True)
            
            os.startfile(str(target_dir))
            self.logger.info(f"{folder_type}フォルダを開きました: {target_dir}")
            
        except Exception as e:
            self.logger.error(f"フォルダを開く際にエラーが発生しました: {str(e)}")
            QMessageBox.critical(
                self,
                "Error",
                f"フォルダを開けませんでした:\n{str(e)}"
            )

    def _open_motion_list(self):
        """モーションリスト管理ウィンドウを開く"""
        try:
            db_path = self.config.get_active_database()
            if db_path and Path(db_path).exists():
                self.motion_list_window = MotionListWindow(db_path=db_path)
                self.motion_list_window.show()
            else:
                QMessageBox.warning(
                    self,
                    "Warning",
                    f"アクティブなデータベースファイル '{db_path}' が見つかりません。\nモーションリスト管理ウィンドウで手動で選択してください。"
                )
                self.motion_list_window = MotionListWindow()
                self.motion_list_window.show()
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"モーションリスト管理ウィンドウの起動に失敗しました: {str(e)}"
            )

    def update_window_title(self):
        """ウィンドウタイトルを更新（現在のデータベースファイル名を表示）"""
        db_path = self.db.get_database_path()
        db_filename = os.path.basename(db_path)
        self.setWindowTitle(f"MotionTag - Video Tool [{db_filename}]")
    
    def refresh_after_db_change(self):
        """データベース変更後の画面更新"""
        self.logger.info(f"データベース変更が検出されました。現在のDB: {self.db.get_database_path()}")
        
        # ExportManagerのデータベース参照を更新
        self.export_manager = ExportManager(self.config, self.db)
        self.logger.info("ExportManagerのデータベース参照を更新しました")
        
        # VideoProcessorのデータベース参照を更新
        # 注意: VideoProcessorは内部でデータベースを生成するため、新しいインスタンスを作成
        old_processor = self.processor
        self.processor = VideoProcessor(self.db)
        # 現在のプロンプト設定を引き継ぐ
        self.processor.set_prompt_config(old_processor.current_prompt_config)
        self.logger.info("VideoProcessorのインスタンスを更新しました")
        
        # 画面を更新
        self.refresh_table()
        self.update_window_title()
        self.logger.info("データベース変更後の画面更新が完了しました")
    
    def update_recent_files_menu(self):
        """最近使用したファイルメニューを更新"""
        # 設定を再読み込みして最新の状態を取得
        config_data = self.config._load_json(self.config.config_file)
        self.logger.debug(f"設定ファイルの内容確認: {config_data}")
        
        # 最近使用したファイルのリストを取得
        recent_files = config_data.get("recent_databases", [])
        self.logger.debug(f"最近使用したファイルメニュー更新: 取得したファイル数={len(recent_files)}, ファイル={recent_files}")
        
        # メニューをクリア
        self.recent_menu.clear()
        
        # 最近使用したファイルがない場合
        if not recent_files:
            no_recent = QAction("No recent files", self)
            no_recent.setEnabled(False)
            self.recent_menu.addAction(no_recent)
            return
        
        # 最近使用したファイルをメニューに追加
        for file_path in recent_files:
            action = QAction(file_path, self)
            action.triggered.connect(lambda checked, path=file_path: self.open_database_from_path(path))
            self.recent_menu.addAction(action)
    
    def create_new_database(self):
        """新しいデータベースファイルを作成"""
        # ファイル選択ダイアログ
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            "Create New Database", 
            str(Path.home()), 
            "SQLite Database (*.db)"
        )
        
        if not file_path:  # キャンセルされた場合
            return
            
        try:
            self.logger.debug(f"新しいデータベースを作成します: {file_path}")
            
            if self.db.create_new_database(file_path):
                self.logger.debug(f"データベース作成成功: {file_path}")
                
                self.update_recent_files_menu()
                
                self.config.set_active_database(file_path)
                
                self.signal_emitter.database_changed.emit()
                self.logger.info(f"新しいデータベースを作成しました: {file_path}")
            else:
                QMessageBox.critical(self, "Error", "Failed to create database.")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error creating database: {str(e)}")
            self.logger.error(f"データベース作成中にエラーが発生: {str(e)}", exc_info=True)
    
    def open_database(self):
        """既存のデータベースファイルを開く"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Open Database", 
            str(Path.home()), 
            "SQLite Database (*.db)"
        )
        
        if not file_path:  # キャンセルされた場合
            return
            
        self.open_database_from_path(file_path)
    
    def open_database_from_path(self, file_path):
        """指定されたパスのデータベースを開く"""
        try:
            self.logger.debug(f"データベースを開こうとしています: {file_path}")
            
            # データベースを変更
            if self.db.change_database(file_path):
                self.logger.debug(f"データベース変更成功: {file_path}")
                
                self.update_recent_files_menu()
                
                self.config.set_active_database(file_path)
                
                self.signal_emitter.database_changed.emit()
                self.logger.info(f"データベースを開きました: {file_path}")
            else:
                QMessageBox.critical(self, "Error", "Failed to open database.")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error opening database: {str(e)}")
            self.logger.error(f"データベースを開く際にエラーが発生: {str(e)}", exc_info=True)
    
    def close_database(self):
        """現在のデータベースを閉じてデフォルトのデータベースに戻る"""
        try:
            default_db_path = self.config.get_paths()["db_path"]
            self.logger.debug(f"デフォルトデータベースに戻ります: {default_db_path}")
            
            if self.db.change_database(default_db_path):
                self.logger.debug(f"データベース変更成功（デフォルトに戻りました）")
                
                self.update_recent_files_menu()
                
                self.config.set_active_database(default_db_path)
                
                self.signal_emitter.database_changed.emit()
                self.logger.info("デフォルトデータベースに戻りました")
            else:
                QMessageBox.critical(self, "Error", "Failed to return to default database.")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error closing database: {str(e)}")
            self.logger.error(f"データベースを閉じる際にエラーが発生: {str(e)}", exc_info=True)
    
    def confirm_discard_changes(self):
        """未保存の変更を破棄するか確認"""
        return True

    def set_video_status(self, video_id, status):
        """ビデオのステータスを設定"""
        try:
            self.db.update_video_status(video_id, status)
            self.refresh_table()
        except Exception as e:
            self.logger.error(f"ビデオステータス更新中にエラーが発生: {str(e)}", exc_info=True)
            self.show_error(f"ステータス更新中にエラーが発生しました: {str(e)}")
    
    def add_video_files(self, file_paths):
        """ビデオファイルをデータベースに追加"""
        try:
            added = []
            
            for file_path in file_paths:
                if not os.path.exists(file_path):
                    self.logger.warning(f"ファイルが存在しません: {file_path}")
                    continue
                    
                # 重複チェックを追加
                try:
                    conn = self.db._get_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT id FROM videos WHERE file_path = ?", (file_path,))
                    existing = cursor.fetchone()
                    conn.close()
                    if existing:
                        video_id = existing[0]
                        self.logger.info(f"重複ファイル検出: {file_path} (video_id={video_id})")
                        QMessageBox.information(self, "情報", f"ファイル '{os.path.basename(file_path)}' は既に追加されています。重複をスキップします。")
                        continue
                except Exception as e:
                    self.logger.error(f"重複チェック中にエラーが発生しました: {str(e)}", exc_info=True)
                
                file_name = os.path.basename(file_path)
                video_id = self.db.add_video(file_path, file_name)
                
                if video_id:
                    added.append((video_id, file_path))
            
            if added:
                self.logger.info(f"{len(added)}件のビデオを追加しました")
                self.refresh_table()
                
                if self.auto_process.isChecked():
                    for video_id, file_path in added:
                        self.process_video(video_id, file_path)
            
            return len(added)
            
        except Exception as e:
            self.logger.error(f"ビデオ追加中にエラーが発生: {str(e)}", exc_info=True)
            self.show_error(f"ビデオ追加中にエラーが発生しました: {str(e)}")
            return 0
    
    def delete_selected_videos(self):
        """選択されたビデオを削除"""
        selected_rows = self.get_selected_rows()
        if not selected_rows:
            QMessageBox.information(self, "Information", "Please select videos to delete.")
            return
        
        msg = "Delete selected videos?"
        reply = QMessageBox.question(self, 'Confirm', msg, QMessageBox.Yes, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                for row in sorted(selected_rows, reverse=True):
                    # UserRoleに設定したvideo_idを取得
                    video_id = self.table.item(row, 0).data(Qt.UserRole)
                    self.logger.debug(f"Deleting video_id={video_id}, row={row}")
                    if video_id is None:
                        continue
                    self.db.delete_video(video_id)
                
                self.logger.info(f"{len(selected_rows)}件のビデオを削除しました")
                self.refresh_table()
                
            except Exception as e:
                self.logger.error(f"ビデオ削除中にエラーが発生: {str(e)}", exc_info=True)
                self.show_error(f"ビデオ削除中にエラーが発生しました: {str(e)}")
    
    def update_analysis_result(self, video_id, result_json):
        """解析結果を更新"""
        try:
            self.db.add_or_update_analysis_result(video_id, result_json)
            
        except Exception as e:
            self.logger.error(f"解析結果更新中にエラーが発生: {str(e)}", exc_info=True)
            self.show_error(f"解析結果の更新中にエラーが発生しました: {str(e)}")
    
    def process_selected_videos(self):
        """選択されたビデオの処理を開始"""
        selected_rows = self.get_selected_rows()
        if not selected_rows:
            QMessageBox.information(self, "Information", "処理するビデオを選択してください。")
            return
        
        prompt_name = self.prompt_combo.currentText()
        
        for row in selected_rows:
            video_id = int(self.table.item(row, 0).text())
            file_path = self.table.item(row, 1).text()
            
            status = self.table.item(row, 3).text()
            if status == VideoStatus.PROCESSING:
                continue
            
            self.db.update_video_prompt(video_id, prompt_name)
            
            self.process_video(video_id, file_path)

    def open_table_context_menu(self, position):
        """テーブルのコンテキストメニューを表示"""
        menu = QMenu()
        delete_action = QAction("Delete Selected", self)
        delete_action.triggered.connect(self.delete_selected_videos)
        menu.addAction(delete_action)
        menu.exec(self.table.viewport().mapToGlobal(position))

    def get_selected_rows(self) -> List[int]:
        """選択された行番号のリストを取得"""
        # 選択された行のインデックスを取得
        return [idx.row() for idx in self.table.selectionModel().selectedRows()] 