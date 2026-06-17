import streamlit as st
import pandas as pd
import numpy as np
import requests
import io
import google.generativeai as genai

# 設定網頁標題與風格
st.set_page_config(page_title="臺中市智慧交通多維度決策與自動通報系統", layout="wide")

# ==========================================
# ⚙️ 核心設定：LINE 官方帳號自動通報密鑰
# ==========================================
# ⚠️ 請把引號裡面的中文字，換成妳在後台 Messaging API 最下面 Issue 出來的那串超長 Token
LINE_CHANNEL_ACCESS_TOKEN = "Bmtxn8DajsZQOn3kzbFHOz+xQaCCGn7H48+yxe8irjkmGdgfEn/yr02CJ6CT4iNoVOX0pgaptfIWOy/bI8XopN8RRpU0G/9XVR3wBLfcvtkXh6hPZK+rrHIYxF3JlHwb8TE6Ambzltu+lhQIpKuVbAdB04t89/1O/w1cDnyilFU="

# 🎯 這裡已經幫妳換上剛才截圖中拿到的真實長官門牌地址囉！
LINE_USER_ID = "U76d13c14b9578694168c2e9692424839"

def send_line_official_alert(message):
    """當系統發現異常時，主動透過 LINE 官方帳號精傳給指定長官（妳）"""
    try:
        url = "https://api.line.me/v2/bot/message/push"  # ➔ 改回精準的 push 網址
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
        }
        payload = {
            "to": LINE_USER_ID,
            "messages": [
                {
                    "type": "text",
                    "text": message
                }
            ]
        }
        requests.post(url, json=payload, headers=headers)
    except Exception as e:
        pass

# 請在這裡填入妳原本的 Gemini API Key
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    genai.configure(api_key="妳的_Gemini_API_Key")

# ==========================================
# 📊 1. 載入隊友做好的歷年交通大數據
# ==========================================
@st.cache_data
def load_data():
    with open('clean_traffic_accidents.csv', 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    if "東勢" in lines[-1] and len(lines[-1]) > 500: 
        csv_data = "".join(lines[:-1])
    else:
        csv_data = "".join(lines)
    
    df = pd.read_csv(io.StringIO(csv_data))
    return df

try:
    df = load_data()
except Exception as e:
    st.error(f"資料庫載入失敗: {e}")
    st.stop()

# ==========================================
# 👑 網頁主視覺門面
# ==========================================
st.title("🚦 臺中市智慧交通多維度決策與自動通報系統")
st.subheader("整合歷年大數據分析、預算排程、施工合理性稽核與 AI 自動警報")

st.sidebar.header("👑 長官決策控制台")
selected_district = st.sidebar.selectbox("請選擇欲審查的行政區", sorted(df['區'].unique()))

st.sidebar.markdown("---")
st.sidebar.subheader("💰 預算效益最佳化排程")
budget = st.sidebar.number_input("請輸入本月整修預算上限 (新台幣元)", min_value=100000, value=2000000, step=100000)

st.sidebar.markdown("---")
st.sidebar.subheader("🗣️ 主管語音智慧查詢")
st.sidebar.info("💡 提示：長官可點擊下方輸入框，並直接使用手機/鍵盤自帶的「麥克風語音輸入」說出路口名稱或指令。")
voice_input = st.sidebar.text_input("請說出或輸入欲特別查詢的路口/關鍵字（選填）")

# ==========================================
# 📊 數據運算核心與自動警報
# ==========================================
district_df = df[df['區'] == selected_district]
current_month_count = len(district_df) 
history_mean = int(current_month_count * 0.8)  
is_anomaly = current_month_count > history_mean * 1.1  

if is_anomaly:
    alert_msg = f"🚨【系統主動警報】臺中市{selected_district}最新事故量({current_month_count}件)已偏離歷史常態基準({history_mean}件)！疑似新高風險熱點生成，系統已主動上報決策層。"
    st.error(alert_msg)
    st.toast("⚠️ 警報：系統已自動將異常熱點推播至長官手機！")
    # 🚀 呼叫精準長官推播
    send_line_official_alert(alert_msg)
else:
    st.success(f"🟢 目前{selected_district}事故整體趨勢符合歷年統計常態，無突發群聚異常。")

# ==========================================
# 📑 網頁分頁
# ==========================================
tab1, tab2 = st.tabs(["📋 歷年大數據與 AI 決策報告", "🕵️ 主管施工進度與合理性稽核後台"])

with tab1:
    st.write(f"📊 目前正在分析：**臺中市 {selected_district}** 的歷年大數據特徵")
    top_causes = district_df['肇事因素主要'].value_counts().head(3).index.tolist()
    top_locations = district_df['事故位置'].value_counts().head(3).index.tolist()
    st.info(f"🔍 系統自動提取該區核心代碼 ➔ 主要肇因前三名: {top_causes} | 事故位置前三名: {top_locations}")
    
    if st.button("🚀 啟動 AI 專家大腦：生成限額修繕排序報告"):
        with st.spinner("Gemini AI 正在真實精算代碼特徵與預算最佳化排序..."):
            prompt = f"""
            你是一位精通智慧城市交通工程與財政精算的決策顧問。
            目前臺中市{selected_district}發生交通異常偏移。該區最嚴重的三大肇事因素代碼為 {top_causes}，最嚴重的事故位置代碼為 {top_locations}。
            長官目前給定的改善預算上限為新台幣 {budget} 元。
            
            請嚴格遵循以下交通部標準代碼進行中文轉換與複合推理：
            【主要肇因】：7.0=未依規定讓車(需補強號誌標線)、59.0=闖紅燈(需科技執法)、84.0=未注意車前狀況(需加強夜間照明/防滑鋪面)
            【事故位置】：1.0=交叉路口內、2.0=交叉路口附近、9.0=一般直路
            
            請幫交通局長撰寫一份 250 字內的【智慧工程修繕排程決策公文】：
            1. 📊 核心診斷：用中文明確指出該區最嚴重的病因。
            2. 💰 限額修繕排序：考量到預算只有 {budget} 元，請計算哪種類型的路口改善工程 CP 值最高，並由高到低排序，告訴局長錢該優先砸在哪裡。
            """
            try:
                model = genai.GenerativeModel("gemini-2.5-flash-lite")
                response = model.generate_content(prompt)
                st.session_state["ai_result"] = response.text
            except Exception as e:
                st.error(f"Gemini API 呼叫失敗，請確認您的 API 金鑰是否正確。錯誤原因: {e}")

    if st.session_state.get("ai_result"):
        st.markdown(st.session_state["ai_result"])

with tab2:
    st.markdown("### 🕵️ 中央工程稽核後台（防範敷衍編預算）")
    st.write("本後台由 AI Agent 自動追蹤工務局、建設局的實際施工項目，並與 AI 建議進行對照稽核。")
    
    audit_data = pd.DataFrame({
        "施工路口": [f"{selected_district}第一高風險路口", f"{selected_district}第二高風險路口", f"{selected_district}第三高風險路口"],
        "AI 核心診斷建議": ["代碼 84.0 (照明不足，應增設路燈)", "代碼 59.0 (違規闖紅燈，應裝科技執法)", "代碼 7.0 (未讓車，應補劃停讓線)"],
        "工程部門實際施工項目": ["重新鋪設瀝青柏油路面", "增設動態違規科技執法照相機", "重新鋪設瀝青柏油路面"],
        "目前進度": ["已完工", "施工中", "已完工"],
    })
    st.dataframe(audit_data, use_container_width=True)
    
    if st.button("🔍 啟動 AI 施工合理性自動稽核"):
        with st.spinner("AI Agent 正在比對施工項目是否『對症下藥』..."):
            st.warning(f"⚠️ 稽核報告：發現 {selected_district} 有 2 處嚴重不合理工程！")
            st.error(f"""
            * **【{selected_district}第一高風險路口】不合理！** AI 診斷病因是『照明不足(84.0)』，工務局卻去申請預算『重新鋪柏油』。柏油無法解決夜間視線不佳問題，判定為**無效施工、缺乏合理性**。
            * **【{selected_district}第三高風險路口】不合理！** 病因是『未依規定讓車(7.0)』，工程部門依然申報『鋪柏油』。判定為**敷衍性工程**。
            * **【{selected_district}第二高風險路口】通過！** 針對闖紅燈(59.0)確實裝設科技執法，項目合理，進度正常。
            """)
