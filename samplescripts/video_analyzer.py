import os
import time
import argparse
import google.generativeai as genai

def get_gemini_client():
    """Gemini APIのクライアントを取得する汎用関数"""
    # SSL証明書の環境変数をクリア
    if 'SSL_CERT_FILE' in os.environ:
        del os.environ['SSL_CERT_FILE']
    
    # API keyの取得と設定
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("環境変数 'GOOGLE_API_KEY' が設定されていません")
    
    genai.configure(api_key=api_key)
    return genai

def upload_video(video_path):
    """動画ファイルをGeminiにアップロードする"""
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"ファイルが見つかりません: {video_path}")
    
    file = genai.upload_file(video_path, mime_type="video/mp4")
    print(f"アップロード完了: '{file.display_name}'")
    return file

def wait_for_processing(file):
    """ファイルの処理が完了するまで待機"""
    print("ファイル処理の完了を待機中...")
    while True:
        file = genai.get_file(file.name)
        if file.state.name == "ACTIVE":
            break
        elif file.state.name != "PROCESSING":
            raise Exception(f"ファイル処理に失敗: {file.name}")
        print(".", end="", flush=True)
        time.sleep(5)
    print("\n処理完了")

def analyze_video(video_path, prompt="この動画における人物の動きを解析して日本語で解説してください。"):
    """動画を解析して結果を返す"""
    # Geminiクライアントの取得
    genai = get_gemini_client()
    
    # Geminiモデルの設定
    generation_config = {
        "temperature": 0.7,
        "top_p": 0.95,
        "top_k": 64,
        "max_output_tokens": 2048,
        "response_mime_type": "text/plain",
    }

    model = genai.GenerativeModel(
        model_name="gemini-2.5-pro-preview-05-06",
        generation_config=generation_config,
        system_instruction="常にカンマ区切りのcsv形式で回答する",
    )

    # 動画のアップロードと処理待ち
    video_file = upload_video(video_path)
    wait_for_processing(video_file)

    # チャットセッションの開始と解析
    chat = model.start_chat()
    response = chat.send_message([video_file, prompt])
    return response.text

def main():
    parser = argparse.ArgumentParser(description='Geminiを使用して動画を解析します')
    parser.add_argument('video_path', help='解析する動画ファイルのパス')
    parser.add_argument('--prompt', help='解析時のプロンプト', default="この動画における人物の動きを解析して日本語で解説してください。")
    args = parser.parse_args()

    try:
        get_gemini_client()
        result = analyze_video(args.video_path, args.prompt)
        print("\n解析結果:")
        print(result)
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")

if __name__ == "__main__":
    main() 