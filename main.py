import base64
import os
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from google import genai
from google.genai import types

app = FastAPI()

# サーバーのシステムから安全にAPIキーを読み込む
API_KEY = os.environ.get("GEMINI_API_KEY")

if not API_KEY:
  client = None
else:
  client = genai.Client(api_key=API_KEY)


@app.get("/", response_class=HTMLResponse)
async def index_page():
  # ★JavaScript内の file を file[0] に修正した、iPhone完全対応版の画面です
  html_content = """
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>雲カメラ AI</title>
        <style>
            body { font-family: sans-serif; display: flex; flex-direction: column; align-items: center; padding: 20px; margin: 0; background: #f0f2f5; }
            .container { max-width: 500px; width: 100%; display: flex; flex-direction: column; gap: 20px; }
            #result-area { min-height: 150px; background: white; padding: 15px; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); font-size: 16px; line-height: 1.5; }
            .btn-container { display: flex; justify-content: center; }
            #upload-btn { background: #007bff; color: white; padding: 15px 30px; font-size: 18px; font-weight: bold; border: none; border-radius: 30px; cursor: pointer; width: 100%; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
            #image-area { height: 250px; border: 2px dashed #ccc; border-radius: 12px; display: flex; align-items: center; justify-content: center; overflow: hidden; background: #eaedf1; }
            #preview { max-width: 100%; max-height: 100%; display: none; object-fit: contain; }
            #placeholder { color: #777; }
            .loading { color: #007bff; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="container">
            <div id="result-area">
                <div id="status">上に表示：ここにAIの判定結果が出ます。<br>真ん中のボタンを押して撮影してください。</div>
            </div>
            <div class="btn-container">
                <input type="file" id="camera-input" accept="image/*" capture="camera" style="display: none;">
                <button id="upload-btn">📸 雲を撮影する</button>
            </div>
            <div id="image-area">
                <span id="placeholder">下に表示：ここに撮影した写真が出ます</span>
                <img id="preview" alt="撮影した写真">
            </div>
        </div>
        <script>
            const cameraInput = document.getElementById('camera-input');
            const uploadBtn = document.getElementById('upload-btn');
            const preview = document.getElementById('preview');
            const placeholder = document.getElementById('placeholder');
            const status = document.getElementById('status');

            uploadBtn.addEventListener('click', () => { cameraInput.click(); });

            cameraInput.addEventListener('change', async (e) => {
                const files = e.target.files;
                if (!files || files.length === 0) return;
                
                // ★修正：iPhoneに「1番目の写真データ」だと教える記述に変更
                const targetFile = files[0];

                // 1. 下のエリアに写真を表示
                const reader = new FileReader();
                reader.onload = function(event) {
                    preview.src = event.target.result;
                    preview.style.display = 'block';
                    placeholder.style.display = 'none';
                }
                reader.readAsDataURL(targetFile);

                // 2. 上のエリアを「解析中」にする
                status.innerHTML = '<span class="loading">Gemini（無料枠）が雲を判定中...</span>';

                // 3. サーバーへ送信
                const formData = new FormData();
                formData.append('image_data', targetFile);

                try {
                    const response = await fetch('/analyze', { method: 'POST', body: formData });
                    const result = await response.text();
                    status.innerHTML = result.replace(/\\n/g, '<br>');
                } catch (error) {
                    status.innerHTML = '<span style="color:red;">エラーが発生しました。</span>';
                }
            });
        </script>
    </body>
    </html>
    """
  return HTMLResponse(content=html_content)


@app.post("/analyze")
async def analyze_image(image_data: Request):
  if not client:
    return "サーバーエラー: AIのAPIキーが設定されていません。"

  form = await image_data.form()
  file = form["image_data"]
  image_bytes = await file.read()
  mime_type = file.content_type

  try:
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            (
                "この空の雲の種類を判定し、明日の天気予報の確率を"
                "日本語で答えてください。"
            ),
        ],
    )
    return response.text
  except Exception as e:
    return f"AI通信エラー: {str(e)}"


if __name__ == "__main__":
  import uvicorn

  uvicorn.run(app, host="0.0.0.0", port=8000)
