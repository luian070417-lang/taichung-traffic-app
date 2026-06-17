import streamlit as st
import pandas as pd
import numpy as np
import requests
import io
import google.generativeai as genai
from streamlit_folium import st_folium
import folium

# 設定網頁標題與整體專業風格
st.set_page_config(page_title="臺中市智慧交通多維度決策與自動通報系統", layout="wide")

# ==========================================
# ⚙️ 核心設定：LINE 官方帳號推播密鑰
# ==========================================
# ⚠️ 請填入妳組別的超長 Token
LINE_CHANNEL_ACCESS_TOKEN = "這裡整串換成妳在後台Issue出來的那串超長Token"
LINE_USER_ID = "U76d13c14b9578694168c2e9692424839"

def send_line_official_alert(message):
    try:
        url = "https://api.line.me/v2/bot/message/push"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
        }
        payload = {
            "to": LINE_USER_ID,
            "messages": [{"type": "text", "text": message}]
        }
        requests.post(url, json=payload, headers=headers)
    except:
        pass

# ==========================================
# 🔒 Gemini AI 安全加密配置
# ==========================================
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except Exception as e:
    st.error("❌ 偵測到網站後台未正確設定 GEMINI_API_KEY")

# ==========================================
# 📊 1. 載入歷年交通大數據
# ==========================================
@st.cache_data
def load_data():
    try:
        with open('clean_traffic_accidents.csv', 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except FileNotFoundError:
        with open('clean_traffic_accidents .csv', 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            
    if "東勢" in lines[-1] and len(lines[-1]) > 500: 
        csv_data = "".join(lines[:-1])
    else:
        csv_data = "".join(lines)
    df = pd.read_csv(io.StringIO(csv_data))
    # 建立一個經緯度聯合 Key 用於路口聚合
    df['Location_Key'] = df['GPS座標Y'].astype(str) + "_" + df['GPS座標X'].astype(str)
    return df

try:
    df = load_data()
except Exception as e:
    st.error(f"資料庫載入失敗: {e}")
    st.stop()

# ==========================================
# ⬅️ 側邊欄控制台
# ==========================================
st.sidebar.header("👑 智慧交通主控台")
main_function = st.sidebar.selectbox("請選擇核心功能：", ["📊 功能一：路口點擊聯動與深度分析", "💰 功能二：預算導向 Top 3 熱點排程"])

# ------------------------------------------
# 📊 功能一：路口點擊聯動、全資料顯示、美編 AI
# ------------------------------------------
if main_function == "📊 功能一：路口點擊聯動與深度分析":
    
    st.title("🚦 臺中市智慧交通戰情室")
    selected_district = st.sidebar.selectbox("請選擇行政區", sorted(df['區'].unique()))
    
    # 過濾該區資料
    district_df = df[df['區'] == selected_district].dropna(subset=['GPS座標Y', 'GPS座標X']).copy()
    
    # LINE 自動警報邏輯
    current_count = len(district_df)
    if current_count > 1000: 
        alert_msg = f"🚨【警報】{selected_district}事故量異常！累計 {current_count} 件。"
        st.toast("⚠️ 已發送警報至長官手機")
        send_line_official_alert(alert_msg)

    # 左右排版
    col_info, col_map = st.columns([1, 1.5])
    
    with col_info:
        st.markdown(f"### 📋 {selected_district} 監控概況")
        st.metric("該區累積事故數", f"{current_count} 件")
        st.info("💡 **操作指南**：\n1. 點擊右側地圖藍色大頭針\n2. 下方將跳出該路口**所有歷史案件**\n3. 啟動 AI 針對**該路口整體歷史**診斷")

    with col_map:
        # 路口聚合：計算每個座標點發生的事故件數
        agg_df = district_df.groupby(['Location_Key', 'GPS座標Y', 'GPS座標X']).size().reset_index(name='count')
        
        # 建立地圖
        center_lat, center_lon = agg_df['GPS座標Y'].mean(), agg_df['GPS座標X'].mean()
        m = folium.Map(location=[center_lat, center_lon], zoom_start=14)
        
        # 只顯示前 100 個最高風險點位，避免網頁當機
        top_spots = agg_df.sort_values('count', ascending=False).head(100)
        for _, row in top_spots.iterrows():
            folium.Marker(
                location=[row['GPS座標Y'], row['GPS座標X']],
                popup=f"Loc:{row['Location_Key']}",
                tooltip=f"此路口共發生 {row['count']} 件事故",
                icon=folium.Icon(color='blue', icon='info-sign')
            ).add_to(m)
        
        map_data = st_folium(m, width=700, height=400, key="main_map")

    # ==========================================
    # 🎯 路口聯動邏輯：顯示該點「所有」資料
    # ==========================================
    st.markdown("---")
    selected_loc = None
    if map_data and map_data.get("last_object_clicked_popup"):
        selected_loc = map_data["last_object_clicked_popup"].replace("Loc:", "")

    if selected_loc:
        target_df = district_df[district_df['Location_Key'] == selected_loc]
        st.warning(f"🎯 **已選定路口分析**：此座標路口共發生 **{len(target_df)}** 件案件")
    else:
        st.info(f"📊 尚未選擇特定路口，目前展示 {selected_district} 整體最近 5 筆紀錄：")
        target_df = district_df.head(5)

    # 顯示所有該路口的資料
    st.dataframe(target_df[['年', '月', '日', '時', '區', '肇事因素主要', '事故位置', '天候', '道路照明設備']], use_container_width=True)

    # ==========================================
    # 🚀 AI 美編報告生成
    # ==========================================
    if st.button("🧠 生成路口診斷美編報告"):
        with st.spinner("AI 正在深度分析該路口特徵..."):
            # 整理該路口的統計特徵餵給 AI
            summary_cause = target_df['肇事因素主要'].value_counts().to_dict()
            summary_loc = target_df['事故位置'].value_counts().to_dict()
            
            prompt = f"""
            你是一位智慧交通決策專家。請針對以下特定路口的【{len(target_df)} 件】歷史事故數據進行深度分析。
            
            路口統計特徵：
            - 主要肇因分佈：{summary_cause}
            - 事故位置分佈：{summary_loc}
            - 天候狀況彙整：{target_df['天候'].unique().tolist()}
            
            請生成一份【美觀排版】的分析報告，必須包含以下重點：
            1. 📌 **路口病因診斷** (請加強語氣指出核心問題)
            2. 🛠️ **具體工程建議** (如：科技執法、標線重劃、照明改善)
            3. 💡 **風險評估總結**
            
            請使用 Markdown 格式，多利用 **粗體**、> 引用、以及 ### 標題，讓閱讀者能秒懂重點。
            """
            try:
                # 🎯 修正處：正確改回高額度主力模型 gemini-2.5-flash
                model = genai.GenerativeModel("gemini-2.5-flash")
                response = model.generate_content(prompt)
                st.markdown("### 📋 AI 專家深度診斷報告")
                st.success(response.text)
            except Exception as e:
                st.error(f"AI 呼叫失敗: {e}")

# ------------------------------------------
# 💰 功能二：預算 Top 3
# ------------------------------------------
else:
    st.title("💰 預算導向修繕最佳化系統")
    budget = st.sidebar.number_input("請輸入預算上限 (元)", min_value=100000, value=2000000)
    
    if st.button("🔍 執行全市橫向精算"):
        with st.spinner("正在揪出全台中最該修的 Top 3 行政區..."):
            top_3 = df['區'].value_counts().head(3)
            
            st.markdown("#### 🚨 全台中最急需預算支援行政區")
            for i, (dist, count) in enumerate(top_3.items()):
                st.write(f"**第 {i+1} 名：{dist}** (事故量: {count} 件)")
            
            # AI 推薦方案
            prompt = f"目前全台中事故最高前三名為 {top_3.index.tolist()}。預算只有 {budget} 元。請美觀地列出這三區各別該修什麼工程，並說明預算分配原因。請用列點與標題排版。"
            try:
                # 🎯 修正處：正確改回高額度主力模型 gemini-2.5-flash
                model = genai.GenerativeModel("gemini-2.5-flash")
                response = model.generate_content(prompt)
                st.markdown("---")
                st.info(response.text)
            except Exception as e:
                st.error(f"AI 呼叫失敗: {e}")
