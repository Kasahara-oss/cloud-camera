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
st.write("CelesTrakの最新軌道データから、1分おきに現在地をリアルタイム計算しています。")

# ⏱️ 60秒（60000ミリ秒）ごとにページを自動でリロードしてピンを動かす
# これによりスマホを開いている間、1分おきにピンが最新位置に更新されます
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=60000, key="datarefresh")
except ImportError:
    # ライブラリがない場合の安全策（手動更新用のボタンを配置）
    if st.button("🔄 画面を最新に更新"):
        st.rerun()

# 🌐 CelesTrakから「みちびき（QZSS）」のTLEデータを直接取得
URL = "https://celestrak.org"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

@st.cache_data(ttl=3600)  # CelesTrakへの負荷を減らすため、データ取得は1時間に1回にキャッシュします
def fetch_qzss_data():
    try:
        response = requests.get(URL, headers=headers, timeout=10)
        if response.status_code == 200 and "38148" in response.text: # みちびき1号機のカタログ番号が含まれているか確認
            return response.text
    except Exception as e:
        st.error(f"データ取得エラー: {e}")
    return None

tle_text = fetch_qzss_data()

if tle_text:
    # 現在の時刻（UTC）を取得してSGP4計算用の時間に変換
    now = datetime.now(timezone.utc)
    jd, fr = jday(now.year, now.month, now.day, now.hour, now.minute, now.second + now.microsecond/1e6)
    
    sat_positions = []
    lines = tle_text.strip().split("\n")
    
    # TLEは3行1組（名前、Line1、Line2）で構成されているため、3行ずつ処理
    for i in range(0, len(lines) - 2, 3):
        name = lines[i].strip()
        line1 = lines[i+1].strip()
        line2 = lines[i+2].strip()
        
        # 衛星オブジェクトの作成と軌道計算
        sat = Satrec.twoline2rv(line1, line2)
        e, r, v = sat.sgp4(jd, fr)
        
        if e == 0:
            x, y, z = r[0], r[1], r[2] # 座標（km）
            long = math.degrees(math.atan2(y, x))
            hyp = math.sqrt(x**2 + y**2)
            lat = math.degrees(math.atan2(z, hyp))
            
            # 地球の自転（GMST）を考慮した簡易的な経度補正
            # UTC 00:00 からの経過時間による自転角の計算
            # ※より精密な変換にはastropy等が必要ですが、日本付近にいるかはこれで確認できます
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
        
        # 🗺️ 日本地図の上に赤いピンを立てる（Streamlit標準の地図機能）
        st.map(df_map, latitude='latitude', longitude='longitude', size=200, color='#FF4B4B')
        
        # 📋 データ一覧の表示（日本時間も添える）
        jst_time = datetime.now(timezone(timedelta(hours=9))).strftime('%Y-%m-%d %H:%M:%S')
        st.subheader(f"📋 衛星の位置データ一覧 ({jst_time} JST)")
        st.dataframe(df_map, use_container_width=True)
else:
    st.error("CelesTrakからのデータ取得に失敗したか、データが空です。時間を置いてお試しください。")

