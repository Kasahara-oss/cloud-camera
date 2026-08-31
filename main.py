import streamlit as st
from google import genai
import os

st.set_page_config(page_title="雲カメラ AI", page_icon="📸", layout="centered")
st.title("📸 雲カメラ AI")
st.write("撮影した写真をAIが判定し、雲の名前や天気の傾向を教えます。")

# Gemini APIの初期化（Renderの環境変数から取得）
api_key = os.environ.get("GEMINI_API_KEY")

uploaded_file = st.file_uploader("真ん中のボタンを押して撮影してください。", type=["jpg", "jpeg", "png"], capture="camera")

if uploaded_file is not None:
    st.image(uploaded_file, caption="撮影した写真", use_container_width=True)
    
    if not api_key:
        st.error("Gemini APIキーが設定されていません。RenderのEnvironment設定を確認してください。")
    else:
        with st.spinner("ここにAIの判定結果が出ます。解析中..."):
            try:
                client = genai.Client(api_key=api_key)
                # 画像データを読み込み
                image_bytes = uploaded_file.read()
                
                # Geminiに解析を依頼
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[
                        {'mime_type': 'image/jpeg', 'data': image_bytes},
                        "この画像に写っている雲の種類（十種雲形など）を特定し、その雲の特徴と今後の天気の変化の予測を分かりやすく日本語で解説してください。"
                    ]
                )
                st.subheader("🤖 AIの判定結果")
                st.write(response.text)
            except Exception as e:
                st.error(f"AI解析エラー: {e}")
