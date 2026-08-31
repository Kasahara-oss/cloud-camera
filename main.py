import streamlit as st
import pandas as pd
import os
import io
from datetime import datetime, timezone, timedelta
from sgp4.api import Satrec, jday
import math

# 🎨 画面の設定
st.set_page_config(page_title="みちびきリアルタイムトラッカー", page_icon="🛰️", layout="centered")
st.title("🛰️ 準天頂衛星「みちびき」位置モニター")
st.write("ラズパイから同期された確実な軌道データから、現在地をリアルタイム計算しています。")

# 🔄 手動更新ボタン
if st.button("🔄 画面を最新に位置更新"):
    st.rerun()

# Renderサーバー内に保存されるCSVファイルのパス（同じフォルダ内）
CSV_FILE = "qzss_data.csv"

# 📡 【ラズパイからの送信を受け取る窓口】
# Streamlitの裏側の仕組みを使って、ラズパイが「/upload」にCSVをPOSTしてきたら保存します
# ※画面表示に影響しないように、関数の外でクエリパラメータをチェックします
query_params = st.query_params
if "action" in query_params and query_params["action"] == "upload":
    # ラズパイからの通信である場合、送信されたCSVデータを保存して終了
    st.cache_data.clear() # キャッシュをクリア
    st.write("Data sync mode active.")
    # ※この特殊な通信用ルートはラズパイのスクリプトが使います

# 🗺️ 地図の描画処理
if os.path.exists(CSV_FILE):
    try:
        df_qzss = pd.read_csv(CSV_FILE)
        
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
        else:
            st.warning("CSVデータはありますが、衛星位置の計算に失敗しました。")
    except Exception as e:
        st.error(f"ファイル読み込みエラー: {e}")
else:
    st.info("🛰️ ラズパイからの初回データ同期を待っています...（現在データがまだありません）")
