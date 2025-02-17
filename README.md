# MP4toExplainText

AIを利用して動画分析とタグ付けを行うアプリ

## 概要

動画ファイル(mp4)を分析し、動作を自動的に検出して  
表形式に出力するアプリケーションです。
 - ふさわしいファイル名
 - 男性/女性/年齢
 - 姿勢の詳細
 - 動きの説明
 - LOOP可能かどうか

スクリプトの中で、自然言語で  
XXの情報を書いて！と指定しているだけなので、  
改造すれば自分のほしい情報を取得できます。

ツールの画面に出るタグ情報は少ないですが、  
csvを出すとタグがびっしり書かれています。


## 主な機能

- 動画ファイルの読み込みと分析
- 自動タグ付け機能
- カスタムタグの作成と管理
- 分析結果のCSVエクスポート
- ログ管理システム

## システム要件

- Python 3.8以上
- Windows 10/11

## インストール

1. リポジトリのクローン:

2. 依存関係のインストール:
```bash
pip install -r requirements.txt
```

3. 設定ファイルの準備:
- `config/config.json`にアプリケーションの設定を記述
- Gemini APIキーの設定

## Gemini APIキーの取得方法

Gemini API キーを取得するには以下の手順に従ってください:

1. [Google Gemini](https://www.google.com/ai/gemini) の公式サイトにアクセス
2. Google アカウントでログインまたは新規登録を行う
3. プロジェクトを作成し、Gemini API を有効化する
4. 発行された API キーを `config/config.json` の該当箇所に設定する

※ 詳細な手順は Google のドキュメントをご参照ください。

## 使用方法


1. アプリケーションの起動:

batで起動するなら run.bat
pythonで起動するなら src/main.py

2. UIから動画ファイルを選択し、分析を開始

## プロジェクト構成

```
MotionTag/
├── src/              # ソースコード
│   ├── core/         # コア機能
│   └── ui/          # UIコンポーネント
├── config/           # 設定ファイル
├── data/            # 分析用データ
├── exports/         # エクスポートファイル
├── logs/            # ログファイル
├── tests/           # テストコード
└── tools/           # 開発用ツール
```

## 開発者向け情報

- ログの確認: `logs/motion_tag_[日付].log`
- 分析結果: `exports/csv/`

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 貢献

バグ報告や機能要望は、GitHubのIssueでお願いします。
プルリクエストも歓迎します。 

## メモ

シンプルな動画解析のスクリプトサンプルは
samplescripts
フォルダに入れてある