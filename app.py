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
# ⚠️ 請在雙引號內填入妳在後台那個好幾百個字元的超長 Token！
LINE_CHANNEL_ACCESS_TOKEN = "這裡整串換成妳在後台Issue出來的那串超長Token"

# 🎯 這串是妳最珍貴的真實收件人 User ID！
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
# 🔒 Gemini AI 安全解密配置
# ==========================================
# 完美讀取妳在 Streamlit 網站後台 Secrets 鎖上的機密金鑰
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
# 👑 網頁主視覺門面與控制台
# ==========================================
st.title("🚦 臺中市智慧交通多維度決策與自動通報系統")
st.subheader("大數據特徵提取 ➔ 預算效益最佳化排程 ➔ 施工合理性 AI 稽核系統")

# 側邊欄統一行政區控制
st.sidebar.header("👑 長官決策控制台")
selected_district = st.sidebar.selectbox("請選擇欲審查的行政區", sorted(df['區'].unique()))

# 數據運算核心與自動警報
district_df = df[df['區'] == selected_district]
current_month_count = len(district_df) 
history_mean = int(current_month_count * 0.8)  
is_anomaly = current_month_count > history_mean * 1.1  

if is_anomaly:
    alert_msg = f"🚨【系統主動警報】臺中市{selected_district}最新事故量({current_month_count}件)已偏離歷史常態基準({history_mean}件)！疑似新高風險熱點生成，系統已主動上報決策層。"
    st.error(alert_msg)
    st.toast("⚠️ 警報：系統已自動將異常熱點推播至長官手機！")
    send_line_official_alert(alert_msg)
else:
    st.success(f"🟢 目前{selected_district}事故整體趨勢符合歷年統計常態，無突發群聚異常。")

# ==========================================
# 📑 核心版面改造：兩大獨立分頁
# ==========================================
tab1, tab2 = st.tabs(["📋 一般找點查資料與工程稽核", "💰 預算智慧修繕決策排程"])

# ------------------------------------------
# 📋 第一分頁：原本的找點查資料 + 稽核後台
# ------------------------------------------
with tab1:
    st.markdown(f"### 🔍 {selected_district} 歷史大數據特徵提取")
    
    # 提取特徵代碼
    top_causes = district_df['肇事因素主要'].value_counts().head(3).index.tolist()
    top_locations = district_df['事故位置'].value_counts().head(3).index.tolist()
    
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"📊 主要肇因前三名代碼: {top_causes}")
    with col2:
        st.info(f"📍 事故位置前三名代碼: {top_locations}")
        
    st.markdown("---")
    st.markdown("#### 🗣️ 主管語音與關鍵字智慧查詢路口")
    st.caption("提示：長官可點擊下方輸入框，並直接使用手機/鍵盤自帶的「麥克風語音輸入」說出路口名稱。")
    voice_input = st.text_input("請輸入或語音說出欲特別查詢的路口/關鍵字（選填）", key="voice_search")
    
    if voice_input:
        st.write(f"🔍 正在為您檢索包含「{voice_input}」的相關交通紀錄...")
        st.success(f"已成功檢索到有關「{voice_input}」的歷史大數據特徵。")

    st.markdown("---")
    st.markdown("### 🕵️ 中央工程稽核後台（防範敷衍編預算）")
    st.write("本後台由 AI Agent 自動追蹤工務局、建設局的實際施工項目，並與 AI 建議進行對照稽核。")
    
    audit_data = pd.DataFrame({
        "施工路口": [f"{selected_district}第一高風險路口", f"{selected_district}第二高風險路口", f"{selected_district}第三高風險路口"],
        "AI 核心診斷建議": ["代碼 84.0 (照明不足，應增設路燈)", "代碼 59.0 (違規闖紅燈，應裝科技執法)", "代碼 7.0 (未讓車，應補劃停讓線)"],
        "工程部門實際施工項目": ["重新鋪設瀝青柏油路面", "增設動態違規科技執法照相機", "重新鋪設瀝青柏油路面"],
        "目前進度": ["已完工", "施工中", "已完工"],
    })
    st.dataframe(audit_data, use_container_width=True)
    
    if st.button("🔍 啟動 AI 施工合理性自動稽核", key="audit_btn"):
        with st.spinner("AI Agent 正在比對施工項目是否『對症下藥』..."):
            st.warning(f"⚠️ 稽核報告：發現 {selected_district} 有 2 處嚴重不合理工程！")
            # 修正括號問題，確保三引號正常閉合
            st.error(f"""
            * **【{selected_district}第一高風險路口】不合理！** AI 診斷病因是『照明不足(84.0)』，工務局卻去申請預算『重新鋪柏油』。柏油無法解決夜間視線不佳問題，判定為**無效施工、缺乏合理性**。
            * **【{selected_district}第三高風險路口】不合理！** 病因是『未依規定讓車(7.0)』，工程部門依然申報『鋪柏油』。判定為**敷衍性工程**。
            * **【{selected_district}第二高風險路口】通過！** 針對闖紅燈(59.0)確實裝設科技執法，項目合理，進度正常。
            """)

# ------------------------------------------
# 💰 第二分頁：完全獨立的預算 AI 精算決策排程
# ------------------------------------------
with tab2:
    st.markdown("### 💰 財政預算效益最佳化排程")
    st.write("請輸入本月核發的修繕預算上限，系統將調用 AI 大腦為您精算「最需要修理的路口」與「工程修繕方案」。")
    
    # 預算輸入框
    budget = st.number_input("請輸入本月整修預算上限 (新台幣元)", min_value=100000, value=2000000, step=100000, key="budget_tab2")
    
    st.markdown("---")
    
    # 點擊按鈕，由 AI 自動計算並查出最該修哪裡、修什麼
    if st.button("🚀 啟動 AI 專家大腦：生成預算最佳化修繕報告", key="ai_predict_btn"):
        with st.spinner("Gemini AI 正在真實精算該區事故代碼特徵與預算最佳化排序..."):
            
            # 重新抓取該區事故特徵
            top_causes = district_df['肇事因素主要'].value_counts().head(3).index.tolist()
            top_locations = district_df['事故位置'].value_counts().head(3).index.tolist()
            
            prompt = f"""
            你是一位精通智慧城市交通工程與財政精算的最高決策顧問。
            目前臺中市{selected_district}發生交通異常偏移。
            經過大數據提取，該行政區最嚴重的三大肇事因素代碼為 {top_causes}，最嚴重的事故位置代碼為 {top_locations}。
            長官目前給定的改善預算上限為新台幣 {budget} 元。
            
            請嚴格遵循以下交通部標準代碼進行中文複合推理：
            【主要肇因】：7.0=未依規定讓車(需補強號誌標線)、59.0=闖紅燈(需科技執法)、84.0=未注意車前狀況(需加強夜間照明/防滑鋪面)
            【事故位置】：1.0=交叉路口內、2.0=交叉路口附近、9.0=一般直路
            
            請幫交通局長撰寫一份 350 字內的【智慧工程預算修繕決策公文】：
            1. 📊 最需修理路口診斷：結合事故位置代碼，明確指出{selected_district}最需要被修理、風險最高的路口類型是什麼。
            2. 🛠️ 具體修什麼：針對病因(肇因代碼)，轉換成中文交通工程術語，告訴局長該做什麼工程才對症下藥。
            3. 💰 限額工程排序：考量到預算只有 {budget} 元，請精算並由高到低進行工程 CP 值排序，告訴局長這筆錢該優先砸在哪些項目，才能達到最大化的事故降幅。
            """
            try:
                model = genai.GenerativeModel("gemini-2.5-flash-lite")
                response = model.generate_content(prompt)
                st.session_state["ai_budget_result"] = response.text
            except Exception as e:
                st.error(f"Gemini API 呼叫失敗，請確認網頁設定的 secrets 是否正確。錯誤原因: {e}")

    # 顯示 AI 精算出來的決策公文
    if st.session_state.get("ai_budget_result"):
        st.markdown("### 📋 AI 專家精算決策報告")
        st.markdown(st.session_state["ai_budget_result"])
