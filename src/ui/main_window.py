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
    QMenuBar, QMenu, QInputDialog, QDialog, QLineEdit, QDialogButtonBox,
    QComboBox
)
from PySide6.QtCore import Qt, QMimeData, Signal, QObject, QTimer
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QAction
from src.core.config_manager import ConfigManager
from src.core.video_processor import VideoProcessor
from src.core.database import Database
from src.core.export_manager import ExportManager
from src.core.prompt_manager import PromptManager
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
        
        # データベースインスタンスを渡してVideoProcessorを初期化
        self.processor = VideoProcessor(self.db)
        self.prompt_manager = PromptManager()
        self.current_filter = ""  # フィルタ文字列を保持
        
        # 変更フラグの初期化
        self.has_unsaved_changes = False
        
        # シグナルの接続
        self.signal_emitter.progress_updated.connect(self.update_progress)
        self.signal_emitter.status_updated.connect(self.update_status)
        self.signal_emitter.error_occurred.connect(self.show_error)
        self.signal_emitter.database_changed.connect(self.refresh_after_db_change)
        
        # ウィンドウタイトルの更新
        self.update_window_title()
        
        # ウィンドウの設定
        self.setMinimumSize(800, 600)
        
        # メニューバーの設定
        self.setup_menu_bar()
        
        # メインウィジェットとレイアウトの設定
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # UIコンポーネントの設定
        self.setup_prompt_selector(layout)
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
        print("=== タイマー設定 ===")
        print("更新間隔: 30秒 (1分)")
        self.update_timer.start(30000)  # 60秒（1分）ごとに更新に変更
        
        # 初期データの読み込み
        self.load_initial_data()
        
        # データベース変更時はウィンドウタイトルを更新（refresh_after_db_changeですでに接続済み）
        # self.signal_emitter.database_changed.connect(self.update_window_title)
        # 重複した接続を防止するためにコメントアウト
        
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
    
    def setup_prompt_selector(self, layout):
        """プロンプト設定選択用のコンボボックスを設定"""
        prompt_layout = QHBoxLayout()
        
        # ラベル
        label = QLabel("プロンプト設定:")
        prompt_layout.addWidget(label)
        
        # コンボボックス
        self.prompt_combo = QComboBox()
        self.update_prompt_list()
        self.prompt_combo.currentTextChanged.connect(self.on_prompt_changed)
        prompt_layout.addWidget(self.prompt_combo)
        
        # 更新ボタン
        refresh_button = QPushButton("更新")
        refresh_button.clicked.connect(self.update_prompt_list)
        prompt_layout.addWidget(refresh_button)
        
        # 右側に余白を追加
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
        
        # 動画を開くボタン
        open_button = QPushButton("🎬")
        open_button.setToolTip("動画を開く")
        open_button.clicked.connect(lambda: os.startfile(file_path))
        self.table.setCellWidget(row, 1, open_button)
        
        # 状態
        self.table.setItem(row, 2, QTableWidgetItem(status))
        
        # 進捗バー
        progress_bar = QProgressBar()
        progress_bar.setValue(progress)
        self.table.setCellWidget(row, 3, progress_bar)
        
        # タグ（空）
        self.table.setItem(row, 4, QTableWidgetItem(""))
        
        # 再処理ボタン
        reprocess_button = QPushButton("▶Run")
        reprocess_button.clicked.connect(lambda: self.on_reprocess(video_id, file_path))
        self.table.setCellWidget(row, 5, reprocess_button)
    
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
        QMessageBox.critical(self, "エラー", message)
    
    def on_batch_process(self):
        """選択された項目の一括処理"""
        try:
            # デバッグ用：選択状態の確認
            print("=== 処理開始前の選択状態 ===")
            initial_selected_items = self.table.selectedItems()
            print(f"選択されているアイテム数: {len(initial_selected_items)}")
            for item in initial_selected_items:
                print(f"選択行: {item.row()}, 列: {item.column()}, テキスト: {item.text()}")
            
            # 選択された行の一意のインデックスを取得
            selected_rows = set(item.row() for item in initial_selected_items)
            print(f"一意の選択行数: {len(selected_rows)}")
            print(f"選択された行: {sorted(list(selected_rows))}")
            
            if not selected_rows:
                self.logger.info("処理する項目が選択されていません")
                return
            
            self.logger.info(f"選択された項目数: {len(selected_rows)}")
            video_ids = []  # 処理対象のvideo_idリスト
            
            for row in selected_rows:
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
                    video_ids.append((video_id, file_path))
                    self.logger.info(f"処理キューに追加: video_id={video_id}, file_path={file_path}")
                    
                except Exception as e:
                    self.logger.error(f"行 {row} の処理中にエラーが発生: {str(e)}")
                    continue
            
            # デバッグ用：処理後の選択状態の確認
            print("\n=== 処理後の選択状態 ===")
            final_selected_items = self.table.selectedItems()
            print(f"選択されているアイテム数: {len(final_selected_items)}")
            for item in final_selected_items:
                print(f"選択行: {item.row()}, 列: {item.column()}, テキスト: {item.text()}")
            
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
            self.logger.info(f"CSVエクスポート開始 - 使用DB: {self.db.get_database_path()}")
            video_ids = self._get_selected_video_ids()
            # 選択がない場合はNoneを渡して全件出力
            filepath = self.export_manager.export_to_csv(video_ids if video_ids else None)
            self.logger.info(f"CSVエクスポート完了: {filepath}")
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
        """ウィンドウを閉じる際の処理"""
        # 未保存の変更がある場合は確認
        if self.has_unsaved_changes and not self.confirm_discard_changes():
            event.ignore()
            return
            
        # 現在のデータベースパスを保存
        self.config.set_active_database(self.db.get_database_path())
        
        # イベントループの停止
        if hasattr(self, "loop") and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
        
        # 親クラスの処理を呼び出し
        super().closeEvent(event)

    def setup_menu_bar(self):
        """メニューバーの設定"""
        menubar = self.menuBar()
        
        # ファイルメニュー（新規追加）
        file_menu = menubar.addMenu("ファイル")
        
        # 新規データベース作成
        new_db_action = file_menu.addAction("新規作成")
        new_db_action.triggered.connect(self.create_new_database)
        
        # データベースを開く
        open_db_action = file_menu.addAction("開く")
        open_db_action.triggered.connect(self.open_database)
        
        # 最近使用したファイルメニュー
        self.recent_menu = QMenu("最近使用したファイル", self)
        file_menu.addMenu(self.recent_menu)
        self.update_recent_files_menu()
        
        file_menu.addSeparator()
        
        # データベースを閉じる（デフォルトDBに戻る）
        close_db_action = file_menu.addAction("閉じる")
        close_db_action.triggered.connect(self.close_database)
        
        file_menu.addSeparator()
        
        # アプリケーション終了
        exit_action = file_menu.addAction("終了")
        exit_action.triggered.connect(self.close)
        
        # 設定メニュー
        settings_menu = menubar.addMenu("Settings")
        api_key_action = settings_menu.addAction("Set API Key")
        api_key_action.triggered.connect(self.set_api_key)
        
        # Windowメニュー
        window_menu = menubar.addMenu("Window")
        
        # モーションリスト管理を開く
        motion_list_action = window_menu.addAction("Open Motion List")
        motion_list_action.triggered.connect(self._open_motion_list)
        
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
                "エラー",
                f"フォルダを開けませんでした:\n{str(e)}"
            )

    def _open_motion_list(self):
        """モーションリスト管理ウィンドウを開く"""
        try:
            db_path = self.config.get_paths().get("db_path")
            if db_path and Path(db_path).exists():
                self.motion_list_window = MotionListWindow(db_path=db_path)
                self.motion_list_window.show()
            else:
                QMessageBox.warning(
                    self,
                    "警告",
                    "データベースファイルが見つかりません。\nモーションリスト管理ウィンドウで手動で選択してください。"
                )
                self.motion_list_window = MotionListWindow()
                self.motion_list_window.show()
        except Exception as e:
            QMessageBox.critical(
                self,
                "エラー",
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
        self.has_unsaved_changes = False  # 変更フラグをリセット
    
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
            no_recent = QAction("最近使用したファイルはありません", self)
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
        # 未保存の変更がある場合は確認
        if self.has_unsaved_changes and not self.confirm_discard_changes():
            return
            
        # ファイル選択ダイアログ
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            "新規データベースの作成", 
            str(Path.home()), 
            "SQLiteデータベース (*.db)"
        )
        
        if not file_path:  # キャンセルされた場合
            return
            
        try:
            self.logger.debug(f"新しいデータベースを作成します: {file_path}")
            
            # 新しいデータベースを作成
            if self.db.create_new_database(file_path):
                self.logger.debug(f"データベース作成成功: {file_path}")
                
                # 最近使用したファイルメニューを更新（先に実行）
                self.update_recent_files_menu()
                
                # 設定を更新
                self.config.set_active_database(file_path)
                
                # UI更新
                self.signal_emitter.database_changed.emit()
                self.logger.info(f"新しいデータベースを作成しました: {file_path}")
            else:
                QMessageBox.critical(self, "エラー", "データベースの作成に失敗しました。")
                
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"データベースの作成中にエラーが発生しました: {str(e)}")
            self.logger.error(f"データベース作成中にエラーが発生: {str(e)}", exc_info=True)
    
    def open_database(self):
        """既存のデータベースファイルを開く"""
        # 未保存の変更がある場合は確認
        if self.has_unsaved_changes and not self.confirm_discard_changes():
            return
            
        # ファイル選択ダイアログ
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "データベースを開く", 
            str(Path.home()), 
            "SQLiteデータベース (*.db)"
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
                
                # 最近使用したファイルメニューを更新（先に実行）
                self.update_recent_files_menu()
                
                # 設定を更新
                self.config.set_active_database(file_path)
                
                # UI更新
                self.signal_emitter.database_changed.emit()
                self.logger.info(f"データベースを開きました: {file_path}")
            else:
                QMessageBox.critical(self, "エラー", "データベースを開けませんでした。")
                
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"データベースを開く際にエラーが発生しました: {str(e)}")
            self.logger.error(f"データベースを開く際にエラーが発生: {str(e)}", exc_info=True)
    
    def close_database(self):
        """現在のデータベースを閉じてデフォルトのデータベースに戻る"""
        # 未保存の変更がある場合は確認
        if self.has_unsaved_changes and not self.confirm_discard_changes():
            return
            
        try:
            # デフォルトのDBパスを取得
            default_db_path = self.config.get_paths()["db_path"]
            self.logger.debug(f"デフォルトデータベースに戻ります: {default_db_path}")
            
            # データベースを変更
            if self.db.change_database(default_db_path):
                self.logger.debug(f"データベース変更成功（デフォルトに戻りました）")
                
                # 最近使用したファイルメニューを更新（先に実行）
                self.update_recent_files_menu()
                
                # 設定を更新
                self.config.set_active_database(default_db_path)
                
                # UI更新
                self.signal_emitter.database_changed.emit()
                self.logger.info("デフォルトデータベースに戻りました")
            else:
                QMessageBox.critical(self, "エラー", "デフォルトデータベースに戻れませんでした。")
                
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"データベースを閉じる際にエラーが発生しました: {str(e)}")
            self.logger.error(f"データベースを閉じる際にエラーが発生: {str(e)}", exc_info=True)
    
    def confirm_discard_changes(self):
        """未保存の変更を破棄するか確認"""
        reply = QMessageBox.question(
            self, 
            "確認", 
            "保存されていない変更があります。変更を破棄してもよろしいですか？",
            QMessageBox.Yes | QMessageBox.No, 
            QMessageBox.No
        )
        return reply == QMessageBox.Yes

    def set_video_status(self, video_id, status):
        """ビデオのステータスを設定"""
        try:
            self.db.update_video_status(video_id, status)
            self.has_unsaved_changes = True  # 変更フラグをセット
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
                    
                file_name = os.path.basename(file_path)
                
                # データベースに追加
                video_id = self.db.add_video(file_path, file_name)
                
                if video_id:
                    added.append((video_id, file_path))
                    self.has_unsaved_changes = True  # 変更フラグをセット
            
            # 追加結果の表示
            if added:
                self.logger.info(f"{len(added)}件のビデオを追加しました")
                self.refresh_table()
                
                # 自動処理が有効ならば処理を開始
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
            QMessageBox.information(self, "情報", "削除するビデオを選択してください。")
            return
        
        # 削除確認
        msg = "選択されたビデオを削除しますか？"
        reply = QMessageBox.question(self, '確認', msg, QMessageBox.Yes, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                for row in sorted(selected_rows, reverse=True):
                    video_id = int(self.table.item(row, 0).text())
                    self.db.delete_video(video_id)
                    self.has_unsaved_changes = True  # 変更フラグをセット
                
                self.logger.info(f"{len(selected_rows)}件のビデオを削除しました")
                self.refresh_table()
                
            except Exception as e:
                self.logger.error(f"ビデオ削除中にエラーが発生: {str(e)}", exc_info=True)
                self.show_error(f"ビデオ削除中にエラーが発生しました: {str(e)}")
    
    def update_analysis_result(self, video_id, result_json):
        """解析結果を更新"""
        try:
            self.db.add_or_update_analysis_result(video_id, result_json)
            self.has_unsaved_changes = True  # 変更フラグをセット
            
        except Exception as e:
            self.logger.error(f"解析結果更新中にエラーが発生: {str(e)}", exc_info=True)
            self.show_error(f"解析結果の更新中にエラーが発生しました: {str(e)}")
    
    def process_selected_videos(self):
        """選択されたビデオの処理を開始"""
        selected_rows = self.get_selected_rows()
        if not selected_rows:
            QMessageBox.information(self, "情報", "処理するビデオを選択してください。")
            return
        
        # プロンプト設定の取得
        prompt_name = self.prompt_combo.currentText()
        
        # 処理開始
        for row in selected_rows:
            video_id = int(self.table.item(row, 0).text())
            file_path = self.table.item(row, 1).text()
            
            # ステータスが処理中の場合はスキップ
            status = self.table.item(row, 3).text()
            if status == VideoStatus.PROCESSING:
                continue
            
            # プロンプト名をDBに保存（追加機能）
            self.db.update_video_prompt(video_id, prompt_name)
            self.has_unsaved_changes = True  # 変更フラグをセット
            
            # 処理開始
            self.process_video(video_id, file_path) 