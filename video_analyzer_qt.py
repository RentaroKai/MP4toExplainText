import os
import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QTextEdit, 
                             QFileDialog, QMessageBox)
from PySide6.QtCore import Qt
import google.generativeai as genai
from video_analyzer import setup_gemini, analyze_video

class VideoAnalyzerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("動画解析アプリ")
        self.setMinimumSize(600, 500)
        
        # メインウィジェットとレイアウトの設定
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # ファイル選択部分
        file_layout = QHBoxLayout()
        self.file_path_label = QLabel("ファイルが選択されていません")
        select_button = QPushButton("動画を選択")
        select_button.clicked.connect(self.select_file)
        file_layout.addWidget(self.file_path_label)
        file_layout.addWidget(select_button)
        layout.addLayout(file_layout)
        
        # プロンプト入力部分
        layout.addWidget(QLabel("プロンプト："))
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText("この動画における人物の動きを解析して以下のフォーマット(カンマ区切りのcsv)で返してください。\n# 項目の内容(ヘッダー):\nこの動きにふさわしいファイル名(英語),日本語のファイル名,この動きをあてはめるのにふさわしい人物像(男女年齢),この動きがふさわしい場面(日本語),全体的な動きの説明(日本語),初期のポーズ(日本語),終わりのポーズ(日本語)")
        self.prompt_edit.setText("この動画における人物の動きを解析して以下のフォーマット(カンマ区切りのcsv)で返してください。\n# 項目の内容(ヘッダー):\nこの動きにふさわしいファイル名(英語),日本語のファイル名,この動きをあてはめるのにふさわしい人物像(男女年齢),この動きがふさわしい場面(日本語),全体的な動きの説明(日本語),初期のポーズ(日本語),終わりのポーズ(日本語)")
        self.prompt_edit.setMaximumHeight(100)
        layout.addWidget(self.prompt_edit)
        
        # 解析ボタン
        analyze_button = QPushButton("解析開始")
        analyze_button.clicked.connect(self.analyze_video)
        layout.addWidget(analyze_button)
        
        # 結果表示部分
        layout.addWidget(QLabel("解析結果："))
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        layout.addWidget(self.result_text)
        
        # Gemini APIの初期設定
        try:
            setup_gemini()
        except ValueError as e:
            QMessageBox.critical(self, "エラー", str(e))
            sys.exit(1)
        
        self.selected_file = None
    
    def select_file(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "動画ファイルを選択",
            "",
            "動画ファイル (*.mp4)"
        )
        if file_name:
            self.selected_file = file_name
            self.file_path_label.setText(os.path.basename(file_name))
    
    def analyze_video(self):
        if not self.selected_file:
            QMessageBox.warning(self, "警告", "動画ファイルを選択してください。")
            return
        
        prompt = self.prompt_edit.toPlainText()
        if not prompt:
            prompt = "この動画における人物の動きを解析して以下のフォーマット(カンマ区切りのcsv)で返してください。\n# 項目の内容(ヘッダー):\nこの動きにふさわしいファイル名(英語),日本語のファイル名,この動きをあてはめるのにふさわしい人物像(男女年齢),この動きがふさわしい場面(日本語),全体的な動きの説明(日本語),初期のポーズ(日本語),終わりのポーズ(日本語)"
        
        try:
            self.result_text.setPlainText("解析を開始します...\n")
            QApplication.processEvents()
            
            result = analyze_video(self.selected_file, prompt)
            self.result_text.setPlainText(result)
        
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"解析中にエラーが発生しました：\n{str(e)}")
            self.result_text.setPlainText("エラーが発生しました。")

def main():
    app = QApplication(sys.argv)
    window = VideoAnalyzerWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 