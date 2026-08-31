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
st.write("CelesTrakの公式データから、現在地をリアルタイム計算しています。")

# 🔄 手動更新ボタン
if st.button("🔄 画面を最新に位置更新"):
    st.cache_data.clear()
    st.rerun()

# 🌐 CelesTrak公式が推奨する、みちびき（QZSS）の最新データURL
URL = "https://celestrak.org"

# 🚀 【重要】CelesTrakにブロックされないための「正しい身元証明」に修正
headers = {
    "User-Agent": "StreamlitQZSSBot/1.0 (https://my-home-sensor.win; Contact: owner)"
}

@st.cache_data(ttl=1800)  # 30分間キャッシュしてサーバーの負荷を軽減
def fetch_qzss_tle():
    try:
        # 🔒 verify=False を追加してクラウド特有のSSL接続エラーを強制回避
        response = requests.get(URL, headers=headers, timeout=15, verify=False)
        if response.status_code == 200 and len(response.text.strip()) > 0:
            return response.text
    except Exception as e:
        st.error(f"通信エラー詳細: {e}")
    return None

tle_text = fetch_qzss_tle()

if tle_text:
    now = datetime.now(timezone.utc)
    jd, fr = jday(now.year, now.month, now.day, now.hour, now.minute, now.second + now.microsecond/1e6)
    
    sat_positions = []
    lines = tle_text.strip().split("\n")
    
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
                # SGP4のテンソル/リスト構造から数値を安全に取り出し
                x = float(r[0])
                y = float(r[1])
                z = float(r[2])
                
                long = math.degrees(math.atan2(y, x))
                hyp = math.sqrt(x**2 + y**2)
                lat = math.degrees(math.atan2(z, hyp))
                
                # 地球の自転を考慮した簡易的な経度補正（UTC基準）
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
        st.warning("衛星データの解析に失敗しました。")
else:
    st.error("CelesTrakからのデータ取得に失敗しました。身元ブロック、または通信エラーが発生しています。")
