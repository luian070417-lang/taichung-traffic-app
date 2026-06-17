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
    if current_count > 1000: # 簡單設定一個門檻值示範
        alert_msg = f"🚨【警報】{selected_district}事故量
