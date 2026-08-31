import streamlit as st
import pandas as pd
import os
from datetime import datetime, timezone, timedelta
from sgp4.api import Satrec, jday
import math

# 🎨 画面の設定
st.set_page_config(page_title="みちびきリアルタイムトラッカー", page_icon="🛰️", layout="centered")

CSV_FILE = "qzss_data.csv"

# 📡 【最新仕様：ラズパイからのデータ送信を100%確実にキャッチする窓口】
# st.query_params の内容を一度 Python の辞書形式（.to_dict()）に変換することで、
# 最新のStreamlit仕様でもデータがリストにならず、正しい文字列として確実に読み込めるようになります。
params = st.query_params.to_dict()

if "action" in params and params["action"] == "sync":
    tle_data = params.get("data")
    if tle_data:
        try:
            rows = []
            # ラズパイから届いた軽量な数値の塊（Line1*Line2|...）を元のTLE構造に分解・復元します
            satellites = [sat for sat in tle_data.split("|") if sat]
            for idx, sat in enumerate(satellites):
                if "*" in sat:
                    l1, l2 = sat.split("*")
                    # カタログ番号をもとに、衛星の名前を自動で割り振ります
                    name = f"QZSS SATELLITE #{idx+1}"
                    if "38148" in l1: name = "MICHIBIKI-1 (QZSS)"
                    elif "42738" in l1: name = "MICHIBIKI-2 (QZSS)"
                    elif "42917" in l1: name = "MICHIBIKI-3 (QZSS)"
                    elif "42965" in l1: name = "MICHIBIKI-4 (QZSS)"
                    elif "47306" in l1: name = "MICHIBIKI-1R (QZSS)"
                    rows.append([name, l1, l2])
            
            if rows:
                # 復元したデータをCSVファイルとしてRenderサーバー内にがっちり書き込み保存します
                df_sync = pd.DataFrame(rows, columns=['OBJECT_NAME', 'TLE_LINE1', 'TLE_LINE2'])
                df_sync.to_csv(CSV_FILE, index=False)
                st.write("SUCCESS") # ラズパイ側への成功合図
                st.stop() # 画面の描画をここで強制停止して通信を終了します
        except Exception as e:
            st.write(f"ERROR: {e}")
            st.stop()

# ─── ここから下は通常のスマホ閲覧用の地図画面 ───
st.title("🛰️ 準天頂衛星「みちびき」位置モニター")
st.write("ご自宅のラズパイから同期された確実な軌道データから、現在地をリアルタイム計算しています。")

if st.button("🔄 画面を最新に位置更新"):
    st.rerun()

# 🗺️ 地図の描画処理
if os.path.exists(CSV_FILE) and os.path.getsize(CSV_FILE) > 0:
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
                
        if sat_positions:
            df_map = pd.DataFrame(sat_positions)
            st.map(df_map, latitude='latitude', longitude='longitude', size=200, color='#FF4B4B')
            
            jst_time = datetime.now(timezone(timedelta(hours=9))).strftime('%Y-%m-%d %H:%M:%S')
            st.subheader(f"📋 衛星の位置データ一覧 ({jst_time} JST)")
            st.dataframe(df_map, use_container_width=True)
    except Exception as e:
        st.error(f"ファイル読み込みエラー: {e}")
else:
    st.info("🛰️ ラズパイからの初回データ同期を待っています...（現在データがまだ到着していません）")
