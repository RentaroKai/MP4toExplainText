import os
import logging
import asyncio
import threading
import time
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QCheckBox, QTableWidget, QTableWidgetItem,
    QLabel, QProgressBar, QFileDialog, QMessageBox,
    QMenuBar, QMenu, QInputDialog, QDialog, QLineEdit, QDialogButtonBox
)
from PySide6.QtCore import Qt, QMimeData, Signal, QObject, QTimer
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from src.core.config_manager import ConfigManager
from src.core.video_processor import VideoProcessor
from src.core.database import Database
from src.core.export_manager import ExportManager
from typing import List

class SignalEmitter(QObject):
    """非同期処理からのシグナルを発行するためのクラス"""
    progress_updated = Signal(int, int)  # video_id, progress
    status_updated = Signal(int, str)    # video_id, status
    error_occurred = Signal(str)         # error_message

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.config = ConfigManager()
        self.db = Database()
        self.processor = VideoProcessor()
        self.signal_emitter = SignalEmitter()
        self.export_manager = ExportManager(self.config, self.db)
        self.current_filter = ""  # フィルタ文字列を保持
        
        # シグナルの接続
        self.signal_emitter.progress_updated.connect(self.update_progress)
        self.signal_emitter.status_updated.connect(self.update_status)
        self.signal_emitter.error_occurred.connect(self.show_error)
        
        # ウィンドウの設定
        self.setWindowTitle("MotionTag - Video Tool")
        self.setMinimumSize(800, 600)
        
        # メニューバーの設定
        self.setup_menu_bar()
        
        # メインウィジェットとレイアウトの設定
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # UIコンポーネントの設定
        self.setup_drag_drop_area(layout)
        self.setup_filter_area(layout)  # フィルタエリアを追加
        self.setup_auto_process_switch(layout)
        self.setup_table_view(layout)
        self.setup_batch_operations(layout)
        self.setup_export_buttons(layout)
        
        # ドラッグ＆ドロップを有効化
        self.setAcceptDrops(True)
        
        # 非同期イベントループの設定
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # イベントループを別スレッドで実行
        self.loop_thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self.loop_thread.start()
        
        # 定期的な更新用タイマー
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.refresh_table)
        self.update_timer.start(5000)  # 5秒ごとに更新
        
        # 初期データの読み込み
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
                    video["progress"]
                )
        except Exception as e:
            self.logger.error(f"初期データの読み込み中にエラーが発生しました: {str(e)}")
            self.show_error("データの読み込みに失敗しました")
    
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
                transition: all 0.3s ease;
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
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Video Name", "Status", "Progress", "Tags", "Actions"
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
        open_csv_folder_btn.setToolTip("CSVフォルダを開く")
        csv_layout.addWidget(open_csv_folder_btn)
        export_layout.addLayout(csv_layout)
        
        # JSONセクション
        json_layout = QHBoxLayout()
        export_json_btn = QPushButton("Export JSON")
        export_json_btn.clicked.connect(self.export_to_json)
        json_layout.addWidget(export_json_btn)
        
        open_json_folder_btn = QPushButton("📁JSON")
        open_json_folder_btn.clicked.connect(lambda: self.open_folder("json"))
        open_json_folder_btn.setToolTip("JSONフォルダを開く")
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
            
            # データベースに追加
            try:
                video_id = self.db.add_video(file)
                self.add_video_to_table(file, video_id, "UNPROCESSED", 0)
                
                # 自動処理が有効な場合は処理を開始
                if self.auto_process.isChecked():
                    asyncio.run_coroutine_threadsafe(
                        self.process_video(video_id, file),
                        self.loop
                    )
                    
            except Exception as e:
                self.logger.error(f"ファイルの追加中にエラーが発生しました: {str(e)}")
                self.show_error(f"ファイルの追加に失敗しました: {file}")
    
    def add_video_to_table(self, file_path: str, video_id: int, status: str, progress: int):
        """テーブルに新しいファイルを追加"""
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        # ファイル名
        self.table.setItem(row, 0, QTableWidgetItem(Path(file_path).name))
        self.table.item(row, 0).setData(Qt.UserRole, video_id)
        
        # 状態
        self.table.setItem(row, 1, QTableWidgetItem(status))
        
        # 進捗バー
        progress_bar = QProgressBar()
        progress_bar.setValue(progress)
        self.table.setCellWidget(row, 2, progress_bar)
        
        # タグ（空）
        self.table.setItem(row, 3, QTableWidgetItem(""))
        
        # 再処理ボタン
        reprocess_button = QPushButton("▶Run")
        reprocess_button.clicked.connect(lambda: self.on_reprocess(video_id, file_path))
        self.table.setCellWidget(row, 4, reprocess_button)
    
    async def process_video(self, video_id: int, file_path: str):
        """動画を非同期で処理"""
        try:
            await self.processor.process_video(
                file_path,
                lambda vid, prog: self.signal_emitter.progress_updated.emit(vid, prog)
            )
        except Exception as e:
            self.logger.error(f"動画の処理中にエラーが発生しました: {str(e)}")
            self.signal_emitter.error_occurred.emit(f"動画の処理に失敗しました: {file_path}")
    
    def update_progress(self, video_id: int, progress: int):
        """進捗バーの更新"""
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.data(Qt.UserRole) == video_id:
                progress_bar = self.table.cellWidget(row, 2)
                if progress_bar:
                    progress_bar.setValue(progress)
                break
    
    def update_status(self, video_id: int, status: str):
        """状態の更新"""
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.data(Qt.UserRole) == video_id:
                self.table.item(row, 1).setText(status)
                break
    
    def show_error(self, message: str):
        """エラーメッセージの表示"""
        QMessageBox.critical(self, "エラー", message)
    
    def on_batch_process(self):
        """選択された項目の一括処理"""
        try:
            selected_rows = self.table.selectedItems()
            if not selected_rows:
                self.logger.info("処理する項目が選択されていません")
                return
            
            self.logger.info(f"選択された項目数: {len(selected_rows)}")
            
            video_ids = []  # 順序を保持するためにリストを使用
            processed_rows = set()
            
            for item in selected_rows:
                row = item.row()
                if row in processed_rows:
                    continue
                    
                try:
                    video_id = self.table.item(row, 0).data(Qt.UserRole)
                    if video_id is None:
                        self.logger.warning(f"行 {row} のvideo_idがNoneです")
                        continue
                        
                    video_info = self.db.get_video_info(video_id)
                    if video_info is None:
                        self.logger.warning(f"video_id {video_id} の情報が見つかりません")
                        continue
                        
                    file_path = video_info["file_path"]
                    if not (video_id, file_path) in video_ids:  # 重複チェック
                        video_ids.append((video_id, file_path))
                    processed_rows.add(row)
                    self.logger.info(f"処理キューに追加: video_id={video_id}, file_path={file_path}")
                    
                except Exception as e:
                    self.logger.error(f"行 {row} の処理中にエラーが発生: {str(e)}")
                    continue
            
            if not video_ids:
                self.logger.warning("処理可能な動画が見つかりませんでした")
                self.show_error("処理可能な動画が選択されていません")
                return
            
            self.logger.info(f"処理を開始する動画数: {len(video_ids)}")
            
            # 全ての動画の処理をキューに追加
            for video_id, file_path in video_ids:
                try:
                    asyncio.run_coroutine_threadsafe(
                        self.process_video(video_id, file_path),
                        self.loop
                    )
                    self.logger.info(f"処理タスクをキューに追加: video_id={video_id}")
                except Exception as e:
                    self.logger.error(f"タスク登録中にエラー: video_id={video_id}, error={str(e)}")
                    self.show_error(f"処理の開始に失敗しました: {str(e)}")
            
        except Exception as e:
            self.logger.error(f"一括処理中に予期せぬエラーが発生: {str(e)}")
            self.show_error(f"一括処理中にエラーが発生しました: {str(e)}")
    
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
        print(f"再処理ボタンがクリックされました - video_id: {video_id}, file_path: {file_path}")
        self.logger.info(f"再処理が開始されました - video_id: {video_id}, file_path: {file_path}")
        try:
            asyncio.run_coroutine_threadsafe(
                self.process_video(video_id, file_path),
                self.loop
            )
            self.logger.info(f"再処理タスクが登録されました - video_id: {video_id}")
        except Exception as e:
            self.logger.error(f"再処理の開始に失敗しました - video_id: {video_id}, error: {str(e)}")
            self.show_error(f"再処理の開始に失敗しました: {str(e)}")
    
    def refresh_table(self):
        """テーブルの定期更新"""
        try:
            videos = self.db.get_all_videos()
            
            # 現在のテーブルの状態を保存
            selected_rows = [item.row() for item in self.table.selectedItems()]
            scroll_position = self.table.verticalScrollBar().value()
            
            # テーブルをクリア
            self.table.setRowCount(0)
            
            # フィルタに一致する動画のみを表示
            for video in videos:
                if self.current_filter in video["file_name"].lower():
                    self.add_video_to_table(
                        video["file_path"],
                        video["id"],
                        video["status"],
                        video["progress"]
                    )
            
            # 選択状態を復元
            for row in selected_rows:
                if row < self.table.rowCount():
                    self.table.selectRow(row)
            
            # スクロール位置を復元
            self.table.verticalScrollBar().setValue(scroll_position)
                        
        except Exception as e:
            self.logger.error(f"テーブルの更新中にエラーが発生しました: {str(e)}")
    
    def export_to_csv(self):
        """選択された項目をCSVにエクスポート"""
        try:
            video_ids = self._get_selected_video_ids()
            # 選択がない場合はNoneを渡して全件出力
            filepath = self.export_manager.export_to_csv(video_ids if video_ids else None)
            QMessageBox.information(
                self,
                "エクスポート完了",
                f"CSVファイルを作成しました:\n{filepath}"
            )
            
        except Exception as e:
            self.logger.error(f"CSVエクスポート中にエラーが発生しました: {str(e)}")
            QMessageBox.critical(
                self,
                "エラー",
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
                "エクスポート完了",
                f"JSONファイルを作成しました:\n{filepath}"
            )
            
        except Exception as e:
            self.logger.error(f"JSONエクスポート中にエラーが発生しました: {str(e)}")
            QMessageBox.critical(
                self,
                "エラー",
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
        """ウィンドウが閉じられる時の処理"""
        self.update_timer.stop()
        if self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
        event.accept()

    def setup_menu_bar(self):
        """メニューバーの設定"""
        menubar = self.menuBar()
        
        # 設定メニュー
        settings_menu = menubar.addMenu("Settings")
        api_key_action = settings_menu.addAction("Set API Key")
        api_key_action.triggered.connect(self.set_api_key)
        
        # ヘルプメニュー
        help_menu = menubar.addMenu("Help")
        about_action = help_menu.addAction("About")
        about_action.triggered.connect(self.show_about)
        help_action = help_menu.addAction("How to Use")
        help_action.triggered.connect(self.show_help)

    def set_api_key(self):
        """APIキーを設定するダイアログを表示"""
        current_key = self.config.get_api_key() or ""
        # マスク表示用の文字列を作成
        masked_key = "X" * len(current_key) if current_key else ""
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Set API Key")
        layout = QVBoxLayout()
        
        # 説明ラベル
        info_label = QLabel(
            "You can set your API key in two ways:\n"
            "1. Set environment variable 'GOOGLE_API_KEY' (recommended)\n"
            "2. Enter directly here\n\n"
            "Note: Environment variable takes priority"
        )
        layout.addWidget(info_label)
        
        # 入力フィールド
        input_field = QLineEdit(dialog)
        input_field.setPlaceholderText("Enter your API key here")
        input_field.setText(masked_key)
        layout.addWidget(input_field)
        
        # ボタンボックス
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

    def show_about(self):
        """バージョン情報を表示"""
        QMessageBox.about(
            self,
            "About",
            "MotionTag - Video Tool\nVersion: 1.0.0\n© 2024 MotionTag Team"
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
                "エラー",
                f"フォルダを開けませんでした:\n{str(e)}"
            ) 