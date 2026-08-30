import streamlit as st
import pandas as pd
import requests
import io
from datetime import datetime, timezone, timedelta
from sgp4.api import Satrec, jday
import math

# 🎨 画面の設定
st.set_page_config(page_title="みちびきリアルタイムトラッカー", page_icon="🛰️", layout="centered")
st.title("🛰️ 準天頂衛星「みちびき」位置モニター")
st.write("CelesTrakの最新軌道データから、現在地をリアルタイム計算しています。")

# 🔄 手動更新ボタン
if st.button("🔄 画面を最新に位置更新"):
    st.cache_data.clear()
    st.rerun()

# 🌐 CelesTrakから「みちびき（QZSS）」のデータを確実に取得するURL（本家TLE形式）
URL = "https://celestrak.org"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

@st.cache_data(ttl=1800)  # 30分間キャッシュ
def fetch_qzss_tle():
    try:
        response = requests.get(URL, headers=headers, timeout=15)
        if response.status_code == 200 and len(response.text.strip()) > 0:
            return response.text
    except Exception as e:
        st.error(f"通信エラー詳細: {e}")
    return None

tle_text = fetch_qzss_tle()

if tle_text:
    # 現在の時刻（UTC）を取得してSGP4計算用の時間に変換
    now = datetime.now(timezone.utc)
    jd, fr = jday(now.year, now.month, now.day, now.hour, now.minute, now.second + now.microsecond/1e6)
    
    sat_positions = []
    lines = tle_text.strip().split("\n")
    
    # 3行1組（名前、Line1、Line2）でループ処理
    for i in range(0, len(lines) - 2, 3):
        name = lines[i].strip()
        line1 = lines[i+1].strip()
        line2 = lines[i+2].strip()
        
        if not line1.startswith('1 ') or not line2.startswith('2 '):
            continue
            
        try:
            sat = Satrec.twoline2rv(line1, line2)
            e, r, v = sat.sgp4(jd, fr)
            
            if e == 0:
                # sgp4ライブラリの正しい座標抽出
                x, y, z = r[0], r[1], r[2]
                long = math.degrees(math.atan2(y, x))
                hyp = math.sqrt(x**2 + y**2)
                lat = math.degrees(math.atan2(z, hyp))
                
                # 地球の自転を考慮した経度補正
                hours_since_utc = now.hour + now.minute/60.0 + now.second/3600.0
                long = (long - (hours_since_utc * 15.04107)) % 360
                if long > 180:
                    long -= 360
                    
                alt = math.sqrt(x**2 + y**2 + z**2) - 6378.137
                
                sat_positions.append({
                    '衛星名 (Name)': name,
                    'latitude': lat,
                    'longitude': long,
                    '高度 (Alt)': f"{alt:.1f} km"
                })
        except Exception:
            continue
            
    if sat_positions:
        df_map = pd.DataFrame(sat_positions)
        
        # 🗺️ 日本地図の上に赤いピンを立てる
        st.map(df_map, latitude='latitude', longitude='longitude', size=200, color='#FF4B4B')
        
        # 📋 データ一覧の表示
        jst_time = datetime.now(timezone(timedelta(hours=9))).strftime('%Y-%m-%d %H:%M:%S')
        st.subheader(f"📋 衛星の位置データ一覧 ({jst_time} JST)")
        st.dataframe(df_map, use_container_width=True)
    else:
        st.warning("衛星データの解析に失敗しました。データが一時的に乱れている可能性があります。")
else:
    st.error("CelesTrakからのデータ取得に失敗したか、データが空です。")
