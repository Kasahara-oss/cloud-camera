import streamlit as st
import pandas as pd
import requests
import io
import csv
from datetime import datetime, timezone, timedelta
from sgp4.api import Satrec, jday
import math

# 🎨 画面の設定（みちびき専用のタイトル）
st.set_page_config(page_title="みちびきリアルタイムトラッカー", page_icon="🛰️", layout="centered")
st.title("🛰️ 準天頂衛星「みちびき」位置モニター")
st.write("CelesTrakの最新軌道データから、現在地をリアルタイム計算しています。")

# 🔄 手動更新ボタン
if st.button("🔄 画面を最新に位置更新"):
    st.cache_data.clear()  # ✨ 正しいキャッシュ消去の命令に直しました
    st.rerun()

# 🌐 CelesTrakから「みちびき（QZSS）」のデータを直接取得
# テストコードで確実にデータが引けていた「CSV形式」に統一します
URL = "https://celestrak.org"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

@st.cache_data(ttl=1800)  # 30分間データを記憶（キャッシュ）します
def fetch_qzss_csv():
    try:
        response = requests.get(URL, headers=headers, timeout=10)
        if response.status_code == 200 and "TLE_LINE1" in response.text:
            return response.text
    except Exception as e:
        st.error(f"データ取得エラー: {e}")
    return None

csv_text = fetch_qzss_csv()

if csv_text:
    # 現在の時刻（UTC）を取得してSGP4計算用の時間に変換
    now = datetime.now(timezone.utc)
    jd, fr = jday(now.year, now.month, now.day, now.hour, now.minute, now.second + now.microsecond/1e6)
    
    sat_positions = []
    
    # テストコードと同じ、確実なCSV解析ルートで処理
    f = io.StringIO(csv_text)
    reader = csv.DictReader(f)
    
    for row in reader:
        name = row.get('OBJECT_NAME')
        line1 = row.get('TLE_LINE1')
        line2 = row.get('TLE_LINE2')
        
        if not line1 or not line2:
            continue
            
        # 衛星オブジェクトの作成と軌道計算
        sat = Satrec.twoline2rv(line1.strip(), line2.strip())
        e, r, v = sat.sgp4(jd, fr)
        
        if e == 0:
            x, y, z = r[0], r[1], r[2] # 座標（km）を配列から個別に取得
            long = math.degrees(math.atan2(y, x))
            hyp = math.sqrt(x**2 + y**2)
            lat = math.degrees(math.atan2(z, hyp))
            
            # 地球の自転を考慮した経度補正
            hours_since_utc = now.hour + now.minute/60.0 + now.second/3600.0
            long = (long - (hours_since_utc * 15.04107)) % 360
            if long > 180:
                long -= 360
                
            alt = math.sqrt(x**2 + y**2 + z**2) - 6378.137 # 高度
            
            sat_positions.append({
                '衛星名 (Name)': name,
                'latitude': lat,
                'longitude': long,
                '高度 (Alt)': f"{alt:.1f} km"
            })
            
    if sat_positions:
        df_map = pd.DataFrame(sat_positions)
        
        # 🗺️ 日本地図の上に赤いピンを立てる
        st.map(df_map, latitude='latitude', longitude='longitude', size=200, color='#FF4B4B')
        
        # 📋 データ一覧の表示（日本時間も添える）
        jst_time = datetime.now(timezone(timedelta(hours=9))).strftime('%Y-%m-%d %H:%M:%S')
        st.subheader(f"📋 衛星の位置データ一覧 ({jst_time} JST)")
        st.dataframe(df_map, use_container_width=True)
    else:
        st.warning("解析された衛星データが0件です。データの中身を確認してください。")
else:
    st.error("CelesTrakからのデータ取得に失敗したか、データが空です。時間を置いてお試しください。")
