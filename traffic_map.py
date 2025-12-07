import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import random

# --- 1. 頁面設定 ---
st.set_page_config(page_title="台中市車禍熱點地圖", layout="wide")
st.title("🚗 台中市交通事故熱點導航")
st.markdown("輸入起點與終點，系統將標示路徑周邊的**高風險車禍路段**。")

# --- 2. 模擬資料生成 (正式版請替換為讀取 CSV) ---
@st.cache_data
def load_data():
    # 這裡模擬一些台中市區的座標
    data = []
    # 修正：加上註解符號 # 避免語法錯誤
    base_lat, base_lon = 24.1477, 120.6733 # (台中車站附近)
    
    for _ in range(100):
        lat = base_lat + random.uniform(-0.05, 0.05)
        lon = base_lon + random.uniform(-0.05, 0.05)
        count = random.choices([1, 3, 6], weights=[0.5, 0.3, 0.2])[0] # 模擬事故次數
        
        # 定義顏色
        if count >= 5:
            color = 'red'
            risk = '高危險 (5次以上)'
        elif count >= 2:
            color = 'orange' # 用橘黃色代替黃色在地圖上較清楚
            risk = '注意 (2-4次)'
        else:
            color = 'green'
            risk = '曾經發生 (1次)'
            
        data.append([lat, lon, count, color, risk])
    
    df = pd.DataFrame(data, columns=['lat', 'lon', 'count', 'color', 'risk'])
    return df

df_accidents = load_data()

# --- 3. 側邊欄：使用者輸入 ---
with st.sidebar:
    st.header("🗺️ 路徑規劃")
    start_location = st.text_input("輸入起點", "台中火車站")
    end_location = st.text_input("輸入終點", "逢甲大學")
    
    run_btn = st.button("查詢路徑與風險")
    
    st.divider()
    st.write("🔴 紅色點：發生 5 次以上")
    st.write("🟠 橘色點：發生 2~4 次")
    st.write("🟢 綠色點：發生 1 次")

# --- 4. 地圖邏輯核心 ---
def get_coordinates(address):
    """使用 Nominatim (OpenStreetMap) 將地址轉為經緯度"""
    geolocator = Nominatim(user_agent="taichung_traffic_app")
    try:
        # 加上 "台中市" 增加準確度
        loc = geolocator.geocode(f"台中市 {address}")
        if loc:
            return loc.latitude, loc.longitude
        return None
    except GeocoderTimedOut:
        return None

# 初始化地圖中心 (預設台中)
m = folium.Map(location=[24.1477, 120.6733], zoom_start=13)

# 標記所有車禍點 (預設顯示)
for index, row in df_accidents.iterrows():
    folium.CircleMarker(
        location=[row['lat'], row['lon']],
        radius=5 if row['color'] == 'green' else 8, # 危險的畫大一點
        color=row['color'],
        fill=True,
        fill_color=row['color'],
        fill_opacity=0.7,
        popup=f"事故次數: {row['count']}\n等級: {row['risk']}"
    ).add_to(m)

# 當使用者按下查詢
if run_btn and start_location and end_location:
    with st.spinner('正在計算路徑並分析資料...'):
        start_coords = get_coordinates(start_location)
        end_coords = get_coordinates(end_location)
        
        if start_coords and end_coords:
            # 1. 標記起點與終點
            folium.Marker(start_coords, icon=folium.Icon(color='blue', icon='play'), tooltip="起點").add_to(m)
            folium.Marker(end_coords, icon=folium.Icon(color='black', icon='stop'), tooltip="終點").add_to(m)
            
            # 2. 畫出直線路徑
            folium.PolyLine(
                locations=[start_coords, end_coords],
                color="blue",
                weight=2,
                dash_array='5'
            ).add_to(m)
            
            # 自動調整地圖視角以涵蓋路徑
            m.fit_bounds([start_coords, end_coords])
            
            st.success(f"已規劃從 {start_location} 到 {end_location} 的路徑參考。")
            
            # 3. (進階) 篩選路徑附近的熱點
            min_lat = min(start_coords[0], end_coords[0])
            max_lat = max(start_coords[0], end_coords[0])
            min_lon = min(start_coords[1], end_coords[1])
            max_lon = max(start_coords[1], end_coords[1])
            
            nearby_accidents = df_accidents[
                (df_accidents['lat'].between(min_lat-0.01, max_lat+0.01)) & 
                (df_accidents['lon'].between(min_lon-0.01, max_lon+0.01))
            ]
            
            if not nearby_accidents.empty:
                high_risk_count = len(nearby_accidents[nearby_accidents['count'] >= 5])
                st.warning(f"⚠️ 路徑周邊範圍內共有 {len(nearby_accidents)} 個事故點，其中包含 {high_risk_count} 個高風險(紅色)熱點，請小心駕駛！")
            
        else:
            st.error("找不到地點，請嘗試輸入更完整的名稱 (例如：台中火車站、逢甲大學)。")

# --- 5. 渲染地圖 ---
st_folium(m, width=1200, height=600)

# --- 6. 數據統計圖表 ---
st.divider()
st.subheader("📊 台中市事故數據分析")
col1, col2 = st.columns(2)

with col1:
    st.write("各等級事故比例")
    st.bar_chart(df_accidents['risk'].value_counts())

with col2:
    st.write("數據概覽")
    st.dataframe(df_accidents.head())