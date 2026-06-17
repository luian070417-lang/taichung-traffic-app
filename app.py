import streamlit as st
import pandas as pd
import numpy as np
import requests
import io
import google.generativeai as genai

# 設定網頁標題與整體專業風格
st.set_page_config(page_title="臺中市智慧交通多維度決策與自動通報系統", layout="wide")

# ==========================================
# ⚙️ 核心設定：LINE 官方帳號推播密鑰
# ==========================================
# ⚠️ 請確保雙引號內有換成妳那串超長的 Token 喔！
LINE_CHANNEL_ACCESS_TOKEN = "這裡整串換成妳在後台Issue出來的那串超長Token"
LINE_USER_ID = "U76d13c14b9578694168c2e9692424839"

def send_line_official_alert(message):
    """當系統發現異常時，主動透過 LINE 官方帳號精準傳給指定長官（妳）"""
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
    st.error("❌ 偵測到網站後台未正確設定 GEMINI_API_KEY，請確認 Streamlit Secrets 設定。")

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
    return pd.read_csv(io.StringIO(csv_data))

try:
    df = load_data()
except Exception as e:
    st.error(f"資料庫載入失敗: {e}")
    st.stop()

# ==========================================
# ⬅️ 側邊欄：功能選單與行政區控制
# ==========================================
st.sidebar.header("👑 智慧交通主控台")

# 依照妳的截圖，讓長官在左邊選單切換主要功能
main_function = st.sidebar.selectbox(
    "請選擇核心功能：",
    ["📊 功能一：行政區數據與多維度 AI 深度診斷", "💰 功能二：預算導向 Top 3 熱點工程排程"]
)

# ------------------------------------------
# 📊 功能一：選區、大頭針地圖、歷年資料、多維度 AI
# ------------------------------------------
if main_function == "📊 功能一：行政區數據與多維度 AI 深度診斷":
    
    st.title("🚦 臺中市智慧交通多維度決策與自動通報系統")
    st.markdown("### 🗺️ 行政區智慧戰情監控面板")
    st.markdown("---")
    
    # 功能一的選區控制放在左邊側邊欄
    selected_district = st.sidebar.selectbox("請選擇欲審查的行政區", sorted(df['區'].unique()))
    
    # 數據過濾
    district_df = df[df['區'] == selected_district]
    current_month_count = len(district_df) 
    history_mean = int(current_month_count * 0.8)  
    is_anomaly = current_month_count > history_mean * 1.1  

    # LINE 即時通報不尋常地區（背景自動觸發）
    if is_anomaly:
        alert_msg = f"🚨【系統主動警報】臺中市{selected_district}最新事故量({current_month_count}件)已偏離歷史常態基準({history_mean}件)！疑似新高風險熱點生成，系統已主動上報決策層。"
        st.error(alert_msg)
        st.toast("⚠️ 警報：系統已自動將異常熱點推播至長官手機！")
        send_line_official_alert(alert_msg)
    else:
        st.success(f"🟢 目前{selected_district}事故整體趨勢符合歷年統計常態，無突發群聚異常。")

    # 左右排版：左邊統計數據與表格、右邊大頭針地圖
    col_data, col_map = st.columns([1, 1])
    
    with col_data:
        st.markdown(f"#### 📋 {selected_district} 歷年統計核心指標摘要")
        st.metric(label="📊 歷史累積事故總量", value=f"{len(district_df)} 件")
        
        # 提取核心代碼特徵
        top_causes = district_df['肇事因素主要'].value_counts().head(3).index.tolist()
        top_locations = district_df['事故位置'].value_counts().head(3).index.tolist()
        top_weather = district_df['天候'].value_counts().head(2).index.tolist()
        top_light = district_df['道路照明設備'].value_counts().head(2).index.tolist()
        
        st.info(f"🔍 主要肇因前三名代碼: {top_causes}\n\n📍 事故位置前三名代碼: {top_locations}")
        st.dataframe(district_df[['年', '月', '區', '肇事因素主要', '事故位置', '天候', '道路照明設備']].head(8), use_container_width=True)

    with col_map:
        st.markdown("#### 📍 高風險路口大頭針地理分佈")
        map_df = district_df[['GPS座標Y', 'GPS座標X']].dropna()
        map_df.columns = ['latitude', 'longitude']
        
        # 修正後的安全地圖判斷（第 124 行修復處）
        if not map_df.empty:
            st.map(map_df)
        else:
            st.warning("⚠️ 該行政區無可用之 GPS 點位資料。")

    st.markdown("---")
    st.markdown("#### 🚀 啟動 Gemini AI 多維度專家深度分析")
    
    if st.button("🧠 進行全方位決策公文生成", key="deep_ai_btn"):
        with st.spinner("AI 正在交叉比對「天候、照明、道路狀態、肇因代碼」進行多維度精算..."):
            
            prompt = f"""
            你是一位精通智慧城市交通工程、大數據交叉特徵精算與財政公文的最高權威決策顧問。
            目前正在審查臺中市【{selected_district}】的交通歷年特徵。
            
            請針對以下大數據提取出來的特徵，進行【多維度、多面向、全方位（而非單一表面）】的複合推理分析：
            1. 主要肇因代碼前三名：{top_causes} (標準定義：7.0=未依規定讓車、59.0=闖紅燈、84.0=未注意車前狀況)
            2. 事故位置代碼前三名：{top_locations} (標準定義：1.0=交叉路口內、2.0=交叉路口附近、9.0=一般直路)
            3. 天候特徵：{top_weather}
            4. 道路照明特徵：{top_light}
            
            請幫交通局長撰寫一份 350 字內、架構嚴謹的【智慧工程修繕多維度決策公文】：
            - 📊 【多維度複合診斷】：深入剖析這些特徵之間的潛在關聯性（例如：在某種特殊天候或夜間照明不佳時，交叉路口內(代碼1.0)的未讓車(代碼7.0)或闖紅燈(59.0)為什麼會複合加劇，絕非單一原因）。
            - 🛠️ 【全方位整修方案】：針對上述分析出來的多面向交通病因，給出
