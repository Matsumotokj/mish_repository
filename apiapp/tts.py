import os
# from gtts import gTTS # ★★★ gTTSをインポート ★★★
# from io import BytesIO # メモリ内でバイナリデータを扱うため

import re

# Gemini (テキスト生成)
import google.generativeai as genai

# Google TTS (音声合成)
from google.cloud import texttospeech

from dotenv import load_dotenv


import cloudinary
import cloudinary.uploader
import io

from google.oauth2 import service_account # これを追加
import json

# --- Cloudinaryの設定 ---
cloudinary.config(
  cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME"),
  api_key = os.getenv("CLOUDINARY_API_KEY"),
  api_secret = os.getenv("CLOUDINARY_API_SECRET"),
  secure = True
)

# Audio Playback (再生)
# from pydub import AudioSegment
# import simpleaudio as sa

# google_api_key_path = "service-account-key.json"
# os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = google_api_key_path
# client = texttospeech.TextToSpeechClient()
load_dotenv()

google_creds_json_str = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
tts_client = None

# try:
#     tts_client = texttospeech.TextToSpeechClient()
#     print("Google Cloud TTSクライアントが正常に初期化されました。")
# except Exception as e:
#     print(f"警告: Google Cloud TTSクライアントの初期化に失敗しました: {e}")
#     print("GOOGLE_APPLICATION_CREDENTIALSが正しく設定されているか確認してください。")
#     tts_client = None

if google_creds_json_str:
    # ケース1: Render環境など、環境変数にJSONの中身が直接設定されている場合
    try:
        credentials_info = json.loads(google_creds_json_str)
        credentials = service_account.Credentials.from_service_account_info(credentials_info)
        tts_client = texttospeech.TextToSpeechClient(credentials=credentials)
        print("Google Cloud TTSクライアントの初期化に成功しました (from env var)。")
    except Exception as e:
        print(f"警告: 環境変数からのTTSクライアント初期化に失敗しました: {e}")
else:
    # ケース2: ローカル環境など、ファイルパスで認証する場合
    print("GOOGLE_CREDENTIALS_JSONが見つからないため、ファイルパスでの認証を試みます。")
    try:
        # この方法は GOOGLE_APPLICATION_CREDENTIALS 環境変数（ファイルパス）を使用します
        tts_client = texttospeech.TextToSpeechClient()
        print("Google Cloud TTSクライアントの初期化に成功しました (from file path)。")
    except Exception as e:
        print(f"警告: ファイルパスからのTTSクライアント初期化に失敗しました: {e}")

        

def generate_mp3_from_text(text: str, public_id: str, speaking_rate=1.0) -> str:
    """
    指定されたテキストからMP3音声を生成し、指定されたディレクトリに保存する関数。
    """

    """
    Google Cloud TTSを使い、指定されたテキストからMP3音声を生成し、
    指定されたディレクトリに保存する関数。
    """
    if not tts_client:
        print("エラー: Google Cloud TTSクライアントが初期化されていません。")
        return None

    if not text.strip():
        print("警告: 空または空白のみのテキストの音声生成はスキップされました。")
        return None

    try:
        # APIに渡すリクエストボディを構築
        synthesis_input = texttospeech.SynthesisInput(text=text)
        voice = texttospeech.VoiceSelectionParams(
            language_code="ja-JP", name="ja-JP-Wavenet-B" # WaveNetの高音質ボイス
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate = speaking_rate
        )

        # APIを呼び出して音声データを取得
        response = tts_client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )

        # ファイルのフルパスを構築
        # file_path = os.path.join(output_dir, filename)

        # # 取得した音声データ（バイナリ）をファイルに書き込む
        # with open(file_path, "wb") as out:
        #     out.write(response.audio_content)
        
        # print(f"Google TTSで音声ファイルを生成しました: {file_path}")
        # return filename # 成功したらファイル名を返す

        # 2. メモリ上の音声データをCloudinaryにアップロード
        # Cloudinaryでは音声ファイルは"video"リソースとして扱われる
        upload_result = cloudinary.uploader.upload(
            io.BytesIO(response.audio_content),
            resource_type="video",
            public_id=public_id,
            folder="typing_app_audio/" # Cloudinary上のフォルダを指定
        )

        # 3. アップロードされたファイルのセキュアなURLを返す
        secure_url = upload_result.get('secure_url')
        print(f"Cloudinaryに音声ファイルをアップロードしました: {secure_url}")
        return secure_url

    except Exception as e:
        print(f"Google TTSでエラーが発生しました: {e}")
        return None # エラー時はNoneを返す




def split_text_by_punctuation(text: str) -> list[str]:
    """
    テキストを句点（。！？）で分割し、句点を含むフレーズのリストを返す。
    例: "こんにちは。元気ですか？はい！" -> ["こんにちは。", "元気ですか？", "はい！"]
    """



    """正規表現を使って、句読点でテキストを分割する関数"""
    # 「。」「！」「？」の後で分割し、句読点自体は文に残す
    sentences = re.split(r'(?<=[。？！])\s*', text)
    # 結果リストの末尾に空の要素が入ることがあるので除去
    return [s for s in sentences if s]
