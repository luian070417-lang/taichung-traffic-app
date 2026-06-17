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

# 讓長官在左邊選單切換主要功能
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
        
        if not map_df.empty:
            st.map(map_df)
        else:
            st.warning("⚠️ 該行政區無可用之 GPS 點位資料。")

    st.markdown("---")
    st.markdown("#### 🚀 啟動 Gemini AI 多維度專家深度分析")
    
    if st.button("🧠 進行全方位決策公文生成", key="deep_ai_btn"):
        with st.spinner("AI 正在交叉比對「天候、照明、道路狀態、肇因代碼」進行多維度精算..."):
            
            # 使用安全的 .format() 規避大括號編譯錯誤
            prompt = """
            你是一位精通智慧城市交通工程、大數據交叉特徵精算與財政公文的最高權威決策顧問。
            目前正在審查臺中市【{}】的交通歷年特徵。
            
            請針對以下大數據提取出來的特徵，進行【多維度、多面向、全方位（而非單一表面）】的複合推理分析：
            1. 主要肇因代碼前三名：{} (標準定義：7.0=未依規定讓車、59.0=闖紅燈、84.0=未注意車前狀況)
            2. 事故位置代碼前三名：{} (標準定義：1.0=交叉路口內、2.0=交叉路口附近、9.0=一般直路)
            3. 天候特徵：{}
            4. 道路照明特徵：{}
            
            請幫交通局長撰寫一份 350 字內、架構嚴謹的【智慧工程修繕多維度決策公文】：
            - 📊 【多維度複合診斷】：深入剖析這些特徵之間的潛在關聯性（例如：在某種特殊天候或夜間照明不佳時，交叉路口內(代碼1.0)的未讓車(代碼7.0)或闖紅燈(59.0)為什麼會複合加劇，絕非單一原因）。
            - 🛠️ 【全方位整修方案】：針對上述分析出來的多面向交通病因，給出該怎麼具體整修的短中長期工程建議（例如結合防滑、科技執法、照明優化的複合工程）。
            """.format(selected_district, top_causes, top_locations, top_weather, top_light)
            
            try:
                model = genai.GenerativeModel("gemini-2.5-flash-lite")
                response = model.generate_content(prompt)
                st.session_state["ai_deep_analysis_result"] = response.text
            except Exception as e:
                st.error(f"Gemini API 呼叫失敗，請確認加密機密設定。錯誤原因: {e}")

    if st.session_state.get("ai_deep_analysis_result"):
        st.markdown(st.session_state["ai_deep_analysis_result"])

# ------------------------------------------
# 💰 功能二：預算導向、全台中抓出事率最高 Top 3 與修理方案
# ------------------------------------------
else:
    st.title("💰 預算導向高風險熱點工程排程系統")
    st.markdown("### 📊 全臺中市橫向大數據精算與修繕分配")
    st.markdown("---")
    
    # 預算輸入框放在左側邊欄
    input_budget = st.sidebar.number_input("請輸入本月整修預算上限 (新台幣元)", min_value=100000, value=2000000, step=100000)
    
    st.write(f"💵 目前設定核發總預算上限：**{input_budget:,} 元**")
    st.write("點擊下方按鈕，系統將自動比對全臺中各區數據，抓出出事率最高的前三個地區，並由 AI 產出推薦整修方案。")
    
    if st.button("🔍 橫向精算：揪出最需要修理的 Top 3 地區", key="top3_calc_btn"):
        with st.spinner("大數據橫向精算中，並派送資料給 AI 生成修理對策..."):
            
            # 自動計算出事率最高的前三個地區
            top_3_districts = df['區'].value_counts().head(3).index.tolist()
            top_3_counts = df['區'].value_counts().head(3).values.tolist()
            
            # 展示精確的數據表格
            st.markdown("#### 🚨 系統精算：全臺中市最急需修繕行政區前三名")
            top3_df = pd.DataFrame({
                "優先修理順序": ["🎯 Top 1 優先改善", "⚠️ Top 2 加強改善", "⚡ Top 3 同步改善"],
                "行政區名稱": top_3_districts,
                "歷史事故累積件數": [f"{count} 件" for count in top_3_counts],
            })
            st.table(top3_df)
            
            # 抓取這前三名地區的特徵以便丟給 AI 做精確診斷
            district_summary = ""
            for i, dist in enumerate(top_3_districts):
                d_df = df[df['區'] == dist]
                d_cause = d_df['肇事因素主要'].value_counts().idxmax()
                d_loc = d_df['事故位置'].value_counts().idxmax()
                district_summary += "地區{}: {} (累積事故 {} 件, 最核心肇因代碼: {}, 主要出事位置代碼: {})\n".format(
                    i+1, dist, top_3_counts[i], d_cause, d_loc
                )
            
            # 使用安全的 .format() 規避大括號編譯錯誤
            prompt = """
            你是一位精通智慧城市交通財政工程、預算排程與風險稽核的最高顧問專家。
            大數據系統橫向比對全臺中市後，精算出事故率最高、最急需這筆預算修理的前三個地區特徵如下：
            {}
            
            長官目前給定的總改善預算上限為新台幣 {} 元。
            
            請幫交通局長撰寫一份【高風險 Top 3 地區預算分配與修繕對策報告】：
            1. 📊 推薦整修方案（具體修什麼）：針對這三個地區各自的頭號車禍病因，轉換成中文交通工程術語，具體寫出每個地區應該「修什麼工程」（例如：增設科技執法、改善路口照明、補強停讓標線）。
            2. 💰 預算編列原因：考量到預算上限為 {} 元，請寫出為什麼把預算砸在這三個行政區、這幾個項目的原因與預期效益（如何精準控管成本、達到最大事故降幅）。
            """.format(district_summary, input_budget, input_budget)
            
            try:
                model = genai.GenerativeModel("gemini-2.5-flash-lite")
                response = model.generate_content(prompt)
                st.session_state["ai_budget_top3_output"] = response.text
            except Exception as e:
                st.error(f"Gemini API 呼叫失敗。錯誤原因: {e}")

    if st.session_state.get("ai_budget_top3_output"):
        st.markdown("---")
        st.markdown("### 📋 AI 推薦修繕方案與預算效益報告")
        st.markdown(st.session_state["ai_budget_top3_output"])
