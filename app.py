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

main_function = st.sidebar.selectbox(
    "請選擇核心功能：",
    ["📊 功能一：行政區數據與多維度 AI 深度診斷", "💰 功能二：預算導向 Top 3 熱點工程排程"]
)

# ------------------------------------------
# 📊 功能一：選區、互動地圖、路口聯動、多維度 AI
# ------------------------------------------
if main_function == "📊 功能一：行政區數據與多維度 AI 深度診斷":
    
    st.title("🚦 臺中市智慧交通多維度決策與自動通報系統")
    st.markdown("### 🗺️ 行政區智慧戰情監控面板 (支援大頭針點擊聯動)")
    st.markdown("---")
    
    selected_district = st.sidebar.selectbox("請選擇欲審查的行政區", sorted(df['區'].unique()))
    
    # 過濾出有座標的資料
    district_df = df[df['區'] == selected_district].dropna(subset=['GPS座標Y', 'GPS座標X']).copy()
    current_month_count = len(district_df) 
    history_mean = int(current_month_count * 0.8)  
    is_anomaly = current_month_count > history_mean * 1.1  

    if is_anomaly:
        alert_msg = "🚨【系統主動警報】臺中市{}最新事故量({}件)已偏離歷史常態基準({}件)！系統已自動上報長官。".format(selected_district, current_month_count, history_mean)
        st.error(alert_msg)
        send_line_official_alert(alert_msg)
    else:
        st.success(f"🟢 目前{selected_district}事故整體趨勢符合歷年統計常態，無突發群聚異常。")

    # 左右排版
    col_data, col_map = st.columns([1, 1])
    
    with col_data:
        st.markdown(f"#### 📋 {selected_district} 概況與點擊觀測台")
        st.metric(label="📊 該行政區總事故件數", value=f"{len(district_df)} 件")
        st.info("💡 操作提示：請點擊右邊地圖上的【任何一個藍色大頭針】，下方就會即時跳出該路口的特定細節，並能用 AI 針對該路口進行複合分析！")

    with col_map:
        st.markdown("#### 📍 高風險路口互動地圖 (請點擊藍色大頭針)")
        
        if not district_df.empty:
            center_lat = district_df['GPS座標Y'].mean()
            center_lon = district_df['GPS座標X'].mean()
            m = folium.Map(location=[center_lat, center_lon], zoom_start=13)
            
            # 安全取前 50 筆點位，避免地圖負載過重
            sample_df = district_df.head(50)
            for idx, row in sample_df.iterrows():
                # 將真實的資料庫 index 寫進大頭針
                folium.Marker(
                    location=[row['GPS座標Y'], row['GPS座標X']],
                    popup=f"ID:{idx}",
                    tooltip="點擊查看此路口詳情"
                ).add_to(m)
            
            # 渲染互動地圖
            map_data = st_folium(m, width=600, height=350, key="traffic_map")
        else:
            st.warning("⚠️ 該行政區無可用之 GPS 點位資料。")
            map_data = None

    # ==========================================
    # 🎯 核心連動：解析點擊的大頭針
    # ==========================================
    st.markdown("---")
    clicked_index = None
    
    if map_data and map_data.get("last_object_clicked"):
        # 雙重防護解析機制，相容各種版本的 folium popup 回傳格式
        try:
            if map_data.get("last_object_clicked_popup"):
                popup_text = map_data["last_object_clicked_popup"]
                clicked_index = int(popup_text.split(":")[-1].strip())
        except:
            clicked_index = None

    # 連動表格顯示
    if clicked_index is not None and clicked_index in district_df.index:
        st.warning(f"🎯 已成功選定特定觀測路口 (資料庫編號: {clicked_index})")
        target_df = district_df.loc[[clicked_index]]
    else:
        st.info(f"📊 尚未點擊特定大頭針，目前展示【{selected_district}】整體前幾筆資料作為範本：")
        target_df = district_df.head(3)

    st.dataframe(target_df[['年', '月', '日', '時', '區', '肇事因素主要', '事故位置', '天候', '道路照明設備']], use_container_width=True)

    # 提取特徵給 AI
    top_causes = target_df['肇事因素主要'].tolist()
    top_locations = target_df['事故位置'].tolist()
    top_weather = target_df['天候'].tolist()
    top_light = target_df['道路照明設備'].tolist()

    st.markdown("#### 🚀 啟動 Gemini AI 針對該路口數據進行深度分析")
    
    if st.button("🧠 生成該選定路口專屬決策公文", key="deep_ai_btn"):
        with st.spinner("AI 正在針對該路口特徵進行「天候、照明、肇因」多維度精算..."):
            
            prompt = """
            你是一位精通智慧城市交通工程、路口大數據特徵精算與財政公文的最高權威決策顧問。
            目前正在審查臺中市【{}】被長官點擊選定的高風險特定路口資料。
            
            請針對這筆被選定路口的特定真實大數據特徵，進行【多維度、多面向（而非單一表面）】的複合推理分析：
            1. 主要肇因代碼：{} (標準定義參考：7.0=未依規定讓車、59.0=闖紅燈、84.0=未注意車前狀況)
            2. 事故具體位置代碼：{} (標準定義參考：1.0=交叉路口內、2.0=交叉路口附近、9.0=一般直路)
            3. 發生時的天候狀態：{}
            4. 發生時的道路照明：{}
            
            請幫交通局長撰寫一份 350 字內、針對該路口的【特定高風險路口修繕多維度決策公文】：
            - 📊 【該路口多維度診斷】：結合該路口發生車禍時的照明、天候與位置代碼，指出在這種複合環境下，為什麼會引發該肇事因素，深度找出病因（例如：夜間無路燈時在交叉路口內極易因為視線不良複合引發未讓車）。
            - 🛠️ 【量身打造整修方案】：針對該路口的多維度病因，給出該怎麼具體整修這條路口的工程建議（如增設路口科技執法、夜間LED主動發光停讓牌、或加強交叉路口內照明與防滑工程）。
            """.format(selected_district, top_causes, top_locations, top_weather, top_light)
            
            try:
                model = genai.GenerativeModel("gemini-2.5-flash-lite")
                response = model.generate_content(prompt)
                st.session_state["ai_click_analysis_result"] = response.text
            except Exception as e:
                st.error("Gemini API 呼叫失敗，請確認加密機密設定。錯誤原因: {}".format(e))

    if st.session_state.get("ai_click_analysis_result"):
        st.markdown(st.session_state["ai_click_analysis_result"])

# ------------------------------------------
# 💰 功能二：預算導向、全台中抓出事率最高 Top 3 與修理方案
# ------------------------------------------
else:
    st.title("💰 預算導向高風險熱點工程排程系統")
    st.markdown("### 📊 全臺中市橫向大數據精算與修繕分配")
    st.markdown("---")
    
    input_budget = st.sidebar.number_input("請輸入本月整修預算上限 (新台幣元)", min_value=100000, value=2000000, step=100000)
    
    st.write("💵 目前設定核發總預算上限：**{:,} 元**".format(input_budget))
    st.write("點擊下方按鈕，系統將自動比對全臺中各區數據，抓出出事率最高的前三個地區，並由 AI 產出推薦整修方案。")
    
    if st.button("🔍 橫向精算：揪出最需要修理的 Top 3 地區", key="top3_calc_btn"):
        with st.spinner("大數據橫向精算中，並派送資料給 AI 生成修理對策..."):
            
            top_3_districts = df['區'].value_counts().head(3).index.tolist()
            top_3_counts = df['區'].value_counts().head(3).values.tolist()
            
            st.markdown("#### 🚨 系統精算：全臺中市最急需修繕行政區前三名")
            top3_df = pd.DataFrame({
                "優先修理順序": ["🎯 Top 1 優先改善", "⚠️ Top 2 加強改善", "⚡ Top 3 同步改善"],
                "行政區名稱": top_3_districts,
                "歷史事故累積件數": ["{} 件".format(count) for count in top_3_counts],
            })
            st.table(top3_df)
            
            district_summary = ""
            for i, dist in enumerate(top_3_districts):
                d_df = df[df['區'] == dist]
                d_cause = d_df['肇事因素主要'].value_counts().idxmax()
                d_loc = d_df['事故位置'].value_counts().idxmax()
                district_summary += "地區{}: {} (累積事故 {} 件, 最核心肇因代碼: {}, 主要出事位置代碼: {})\n".format(
                    i+1, dist, top_3_counts[i], d_cause, d_loc
                )
            
            prompt = """
            你是一位精通智慧城市交通財政工程、預算排程與風險稽核的最高顧問專家。
            大數據系統橫向比對全臺中市後，精算出事故率最高、最急需這筆預算修理的前三個地區特徵如下：
            {}
            
            長官目前給定的總改善預算上限為新台幣 {} 元。
            
            請幫交通局長撰寫一份【高風險 Top 3 地區預算分配與修繕對策報告】：
            1. 📊 推薦整修方案（具體修什麼）：針對這三個地區各自的頭號車禍病因，具體寫出每個地區應該「修什麼工程」（例如：增設科技執法、改善路口照明）。
            2. 💰 預算編列原因：考量到預算上限為 {} 元，請寫出為什麼把預算砸在這三個行政區項目與預期效益。
            """.format(district_summary, input_budget, input_budget)
            
            try:
                model = genai.GenerativeModel("gemini-2.5-flash")
                response = model.generate_content(prompt)
                st.session_state["ai_budget_top3_output"] = response.text
            except Exception as e:
                st.error("Gemini API 呼叫失敗。錯誤原因: {}".format(e))

    if st.session_state.get("ai_budget_top3_output"):
        st.markdown("---")
        st.markdown("### 📋 AI 推薦修繕方案與預算效益報告")
        st.markdown(st.session_state["ai_budget_top3_output"])
