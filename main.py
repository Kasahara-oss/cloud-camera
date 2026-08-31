import streamlit as st
import pandas as pd
import requests
import io
from datetime import datetime, timezone, timedelta
from sgp4.api import Satrec, jday
import math

st.set_page_config(page_title="みちびきリアルタイムトラッカー", page_icon="🛰️", layout="centered")
st.title("🛰️ 準天頂衛星「みちびき」位置モニター")
st.write("1分おきに自宅のラズパイから最新の軌道データを取得し、リアルタイムに位置を計算しています。")

# ⏱️ 1分おきに画面を強制自動更新するボタン代わりのリロード
if st.button("🔄 画面を最新に位置更新"):
    st.rerun()

# 🌐 あなたが構築したCloudflare Tunnel経由で、ラズパイの温湿度と同じルートからCSVを引っ張ってきます
# ※ポート番号やパス（/qzss_data.csv）は後述のラズパイの設定と連動します
LAPAI_URL = "https://my-home-sensor.win"

@st.cache_data(ttl=50)  # 1分（60秒）未満のアクセスはラズパイに負担をかけないようキャッシュします
def get_data_from_raspi():
    try:
        response = requests.get(LAPAI_URL, timeout=10)
        if response.status_code == 200:
            return response.text
    except Exception as e:
        st.error(f"ラズパイからのデータ取得に失敗しました: {e}")
    return None

csv_text = get_data_from_raspi()

if csv_text:
    try:
        df_qzss = pd.read_csv(io.StringIO(csv_text))
        now = datetime.now(timezone.utc)
        jd, fr = jday(now.year, now.month, now.day, now.hour, now.minute, now.second + now.microsecond/1e6)
        
        sat_positions = []
        for index, row in df_qzss.iterrows():
            name = row.get('OBJECT_NAME')
            line1 = row.get('TLE_LINE1')
            line2 = row.get('TLE_LINE2')
            
            if not line1 or not line2:
                continue
                
            sat = Satrec.twoline2rv(str(line1).strip(), str(line2).strip())
            e, r, v = sat.sgp4(jd, fr)
            
            if e == 0:
                x, y, z = r, r, r
                long = math.degrees(math.atan2(y, x))
                hyp = math.sqrt(x**2 + y**2)
                lat = math.degrees(math.atan2(z, hyp))
                
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
                
        if sat_positions:
            df_map = pd.DataFrame(sat_positions)
            st.map(df_map, latitude='latitude', longitude='longitude', size=200, color='#FF4B4B')
            
            jst_time = datetime.now(timezone(timedelta(hours=9))).strftime('%Y-%m-%d %H:%M:%S')
            st.subheader(f"📋 衛星の位置データ一覧 ({jst_time} JST)")
            st.dataframe(df_map, use_container_width=True)
    except Exception as e:
        st.error(f"データ解析エラー: {e}")
else:
    st.info("🛰️ 自宅のラズパイからのデータ応答を待っています...")
