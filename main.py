import streamlit as st
from google import genai
from google.genai import types
import os

st.set_page_config(page_title="雲カメラ AI", layout="centered")
st.title("☁️ 雲カメラ AI (Streamlit版)")

# 1. 上側：AIの判定結果が出るエリア
result_area = st.empty()
result_area.write("上に表示：ここにAIの判定結果が出ます。\n真ん中のボタンを押して撮影してください。")

# 2. 真ん中：スマホのカメラを起動して撮影するボタン
uploaded_file = st.camera_input("📸 雲を撮影する")

# 3. 写真が撮影されたら動く処理
if uploaded_file is not None:
    result_area.info("Gemini（無料枠）が雲を判定中...")
    
    try:
        # APIキーの読み込みとクライアント初期化
        API_KEY = os.environ.get("GEMINI_API_KEY")
        if not API_KEY:
            result_area.error("サーバーエラー: AIのAPIキーが設定されていません。")
        else:
            client = genai.Client(api_key=API_KEY)
            image_bytes = uploaded_file.read()
            mime_type = uploaded_file.type # 画像の種類（jpegなど）を自動取得

            # Gemini AIで解析
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                    "この空の雲の種類を判定し、明日の天気予報の確率を日本語で答えてください。"
                ]
            )
            # 結果を画面に表示
            result_area.success(response.text)
            
    except Exception as e:
        result_area.error(f"AI通信エラー: {str(e)}")
