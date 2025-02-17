# AIに取得してほしい項目を変更してもらうためのcursor向け仕様変更書サンプル

2. **プロンプトの改善点**
- プロンプト追加。あと　recommended_character_profile　のプロンプトは消して取得しない
- "suitable character_gender for the movement (Please choose one of the following options: male, female, both, any)"
- "suitable character_age_group for the movement (Please choose one of the following options: young, adult, elderly, child)"
- "suitable character_body_type for the movement (Please choose one of the following options: average, muscular, slim)"

3. **データベースの変更案**
- `recommended_character_profile`は廃止
- 新規カラムを追加：
  - `character_gender` TEXT DEFAULT NULL
  - `character_age_group` TEXT DEFAULT NULL
  - `character_body_type` TEXT DEFAULT NULL
- 制約は設けず、AIからの自由な文字列を受け入れる

5. **CSVエクスポートの改善**
- 既存の`recommended_character_profile`列は削除
- 新しい3列を追加：
  - `character_gender`
  - `character_age_group`
  - `character_body_type`

7. **必要な修正ファイル**
- `src/core/gemini_api.py`: レスポンススキーマの調整
- `src/core/database.py`: テーブル構造の変更
- `src/core/export_manager.py`: CSV出力の更新


修正が必要なファイルと変更内容：

1. **データベース関連の修正**
- `src/core/database.py`
  - 新規カラムの追加：`character_gender`, `character_age_group`, `character_body_type`

2. **Gemini API関連の修正**
- `src/core/gemini_api.py`
  - プロンプトの更新
  - 新しい文字列フォーマットへの対応

4. **エクスポート関連の修正**
- `src/core/export_manager.py`
  - CSVエクスポート処理の更新
  - 新規カラムの追加対応

5. **設定ファイルの修正**
- `config/config.json`
  - 新しいプロファイル構造に対応する設定の追加
  - デフォルト値の設定


実装の優先順位としては：

1. データベース構造の変更（`database.py`）
2. Gemini APIの応答形式の更新（`gemini_api.py`）
3. エクスポート機能の更新（`export_manager.py`）

