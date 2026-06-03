import streamlit as st
import pandas as pd
import google.generativeai as genai
import folium
from streamlit_folium import st_folium
import os
import requests
import io

# 🔐 資訊安全最高標準：程式碼內絕不留任何金鑰字串
if "GEMINI_API_KEY" in st.secrets:
    api_key_val = st.secrets["GEMINI_API_KEY"]
else:
    # 如果是在自己電腦本地跑，且沒有設定檔，就直接提示錯誤，拒絕執行
    st.error("❌ 找不到 Gemini API 金鑰！請在本地 .streamlit/secrets.toml 或雲端後台設定。")
    st.stop()

genai.configure(api_key=api_key_val)

# 🎨 網頁全螢幕與標題配置
st.set_page_config(layout="wide", page_title="臺中市交通智慧治理大數據儀表板", page_icon="🚦")

# 💄 【超級美編核心】注入企業級 CSS 科技感視覺樣式
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    h1 {
        color: #0f4c81 !important; /* 經典科技深藍 */
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        font-weight: 800 !important;
        border-bottom: 3px solid #00a8cc; /* 青綠色下底線 */
        padding-bottom: 10px;
    }
    h3 {
        color: #1b4965 !important;
        font-weight: 700 !important;
        margin-top: 20px !important;
    }
    [data-testid="stMetricValue"] { font-size: 24px !important; color: #0077b6 !important; font-weight: bold !important; }
    div[data-testid="metric-container"] {
        background-color: #ffffff; border-radius: 10px; padding: 15px 20px !important;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05); border-left: 5px solid #00a8cc;
    }
    .stButton>button {
        background: linear-gradient(135deg, #0f4c81 0%, #00a8cc 100%) !important;
        color: white !important; font-weight: bold !important; border: none !important;
        padding: 10px 25px !important; border-radius: 25px !important; width: 100%;
    }
    .ai-report-box { background-color: #f0f8ff; border-left: 6px solid #0f4c81; padding: 20px; border-radius: 8px; }
    </style>
""", unsafe_allow_html=True)

# 📊 官方數據代碼對照表
WEATHER_MAP = {1: "暴雨", 2: "大雨", 3: "下雨", 4: "陰天", 5: "晴天", 6: "風沙", 7: "多雲", 8: "霧或煙霧"}
LOCATION_MAP = {1: "交叉路口內", 2: "交叉路口附近", 3: "機車車道", 4: "廣場", 5: "普通車道", 6: "快車道", 7: "慢車道", 8: "路肩/路緣", 9: "一般車道", 14: "行人穿越道", 19: "橋樑"}
CAUSE_MAP = {84: "未注意車前狀況", 7: "未依規定讓車", 59: "左轉彎未依規定", 11: "違反號誌管制", 51: "變換車道不當", 20: "超速失控", 14: "未保持安全距離", 8: "未依規定減速", 40: "逆向行駛", 48: "迴轉未依規定"}

# 🌐 【自動聯網更新網址】自動抓取最新雲端開放資料庫
LIVE_DATA_URL = "https://datacenter.taichung.gov.tw/swagger/OpenData/9ff5068a-669b-4bf1-bf63-47895e69e061"

# 🧠 核心數據融合快取機制
@st.cache_data(ttl=86400)
def load_and_merge_master_database():
    local_df = pd.DataFrame()
    if os.path.exists("data.csv"):
        try: local_df = pd.read_csv("data.csv", encoding='utf-8-sig')
        except: local_df = pd.read_csv("data.csv", encoding='cp950')
        
    live_df = pd.DataFrame()
    try:
        response = requests.get(LIVE_DATA_URL, timeout=10)
        response.raise_for_status()
        try: csv_text = response.content.decode('utf-8-sig')
        except: csv_text = response.content.decode('cp950')
        live_df = pd.read_csv(io.StringIO(csv_text))
    except:
        pass
        
    if not local_df.empty and not live_df.empty:
        master_df = pd.concat([local_df, live_df], ignore_index=True).drop_duplicates(subset=['序號'])
        return master_df, "merged"
    elif not local_df.empty:
        return local_df, "local_only"
    else:
        return pd.DataFrame(), "none"

raw_df, db_status = load_and_merge_master_database()

def clean_data_pipeline(df_input):
    if df_input.empty: return df_input
    df = df_input.copy()
    if '天候' in df.columns: df['天候描述'] = df['天候'].map(WEATHER_MAP).fillna("其他")
    if '事故位置' in df.columns: df['位置描述'] = df['事故位置'].map(LOCATION_MAP).fillna("其他/路段")
    if '肇事因素主要' in df.columns: df['主要肇因描述'] = df['肇事因素主要'].map(CAUSE_MAP).fillna("其他原因")
    if 'GPS座標X' in df.columns and 'GPS座標Y' in df.columns:
        df['GPS座標X'] = pd.to_numeric(df['GPS座標X'], errors='coerce')
        df['GPS座標Y'] = pd.to_numeric(df['GPS座標Y'], errors='coerce')
        df = df.dropna(subset=['GPS座標X', 'GPS座標Y'])
    return df

df = clean_data_pipeline(raw_df)

if not df.empty:
    st.sidebar.markdown("<h2 style='color: #0f4c81; font-weight: bold;'>🎛️ 治理控制台</h2>", unsafe_allow_html=True)
    
    if db_status == "merged":
        st.sidebar.markdown("<div style='background-color: #d4edda; color: #155724; padding: 10px; border-radius: 5px; font-weight: bold; margin-bottom: 10px;'>📡 數據狀態：已自動融合同步最新雲端開放資料</div>", unsafe_allow_html=True)
    else:
        st.sidebar.markdown("<div style='background-color: #fff3cd; color: #856404; padding: 10px; border-radius: 5px; font-weight: bold; margin-bottom: 10px;'>💾 數據狀態：目前讀取本地歷史大數據</div>", unsafe_allow_html=True)
        
    st.sidebar.success(f"📊 超級數據庫總計：{len(df)} 筆紀錄")
    
    dist_col = [col for col in df.columns if "區" in col or "鄉鎮" in col]
    dist_field = dist_col[0] if dist_col else "區"
    
    all_districts = sorted([str(x) for x in df[dist_field].dropna().unique() if str(x).strip() != ""])
    selected_district = st.sidebar.selectbox("🏙️ Step 1. 選擇臺中市行政區", ["-- 請選擇 --"] + all_districts)
    
    st.markdown("<h1>🚦 臺中市交通智慧治理：微觀路口 AI 決策輔助系統</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #6c757d; font-size: 15px;'>本系統整合地理空間大數據與新世代生成式 AI，旨在為交通局與工務局提供精準的路口整修方案，實現智慧都市精準治理。</p>", unsafe_allow_html=True)
    
    if selected_district != "-- 請選擇 --":
        district_df = df[df[dist_field] == selected_district]
        
        st.write("---")
        st.markdown(f"### 🗺️ 臺中市 {selected_district} 交通事故高發熱點分佈圖")
        st.markdown("<div style='background-color: #eaf6f6; padding: 10px; border-radius: 5px; color: #0077b6; font-size: 14px; font-weight: 500; margin-bottom: 15px;'>💡 決策指引：請點擊地圖上的【紅色大頭針標記】，下方將一秒啟動大數據深度挖掘與 AI 診斷。</div>", unsafe_allow_html=True)
        
        center_lat = district_df['GPS座標Y'].mean()
        center_lon = district_df['GPS座標X'].mean()
        
        m = folium.Map(location=[center_lat, center_lon], zoom_start=14, control_scale=True)
        
        district_df['Lat_Group'] = district_df['GPS座標Y'].round(3)
        district_df['Lon_Group'] = district_df['GPS座標X'].round(3)
        intersection_counts = district_df.groupby(['Lat_Group', 'Lon_Group']).size().reset_index(name='事故次數')
        
        for _, row in intersection_counts.sort_values(by='事故次數', ascending=False).head(80).iterrows():
            folium.Marker(
                location=[row['Lat_Group'], row['Lon_Group']],
                popup=f"歷史與最新累積：{row['事故次數']} 件",
                icon=folium.Icon(color='red', icon='info-sign')
            ).add_to(m)
            
        map_data = st_folium(m, width="100%", height=450, key="taichung_map")
        
        clicked_lat, clicked_lon = None, None
        if map_data and map_data.get("last_object_clicked"):
            clicked_lat = map_data["last_object_clicked"]["lat"]
            clicked_lon = map_data["last_object_clicked"]["lng"]
            
        st.write("---")
        
        if clicked_lat and clicked_lon:
            intersection_df = district_df[
                (abs(district_df['GPS座標Y'] - clicked_lat) < 0.0015) & 
                (abs(district_df['GPS座標X'] - clicked_lon) < 0.0015)
            ]
            total_cases = len(intersection_df)
            
            st.markdown(f"### 📊 該指定路口歷年複合多維度分析報告")
            st.markdown(f"<p style='color: #4a5568;'>📌 <b>經緯度定位：</b> ({clicked_lat:.4f}, {clicked_lon:.4f}) | <b>歷史與最新累積總數：</b> <span style='color: #e63946; font-weight: bold; font-size: 18px;'>{total_cases}</span> 件</p>", unsafe_allow_html=True)
            
            if total_cases > 0:
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.markdown("##### 🕰️ 高發月份與時段特徵")
                    time_summary = intersection_df.groupby(['月', '時']).size().reset_index(name='件數').sort_values(by='件數', ascending=False).head(3)
                    st.dataframe(time_summary, hide_index=True, use_container_width=True)
                with c2:
                    st.markdown("##### 🌤️ 肇事環境天候特徵")
                    st.dataframe(intersection_df['天候描述'].value_counts().head(3), use_container_width=True)
                with c3:
                    st.markdown("##### 💥 核心主要肇事因素")
                    reason_summary = intersection_df['主要肇因描述'].value_counts().to_dict()
                    st.dataframe(intersection_df['主要肇因描述'].value_counts().head(3), use_container_width=True)
                    
                with st.expander("📋 點擊展開查閱本路口歷史原始事件清單（公務流水帳）"):
                    st.dataframe(intersection_df[['序號', '年', '月', '日', '時', '分', '天候描述', '位置描述', '主要肇因描述', '死亡數量', '受傷數量']], use_container_width=True)
                
                st.write("")
                st.markdown("### 🏛️ 行政決策：智慧交通工程整修方案")
                
                # ==========================================
                # 🧠 1. 記憶鎖與路口切換防呆感應機制
                # （請把這段放在按鈕的最上方，靠最左邊，不要縮排在任何 if 裡面）
                # ==========================================

                # 用當前的經緯度組合出一個唯一的路口鑰匙
                current_intersection_key = f"{clicked_lat:.4f}_{clicked_lon:.4f}"

                # 初始化網頁記憶體
                if "ai_report" not in st.session_state:
                    st.session_state["ai_report"] = None

                # 💡 防呆機制：如果使用者點擊了地圖上「新的路口」，自動把舊報告擦掉，避免顯示錯誤！
                if "last_intersection" not in st.session_state or st.session_state["last_intersection"] != current_intersection_key:
                    st.session_state["ai_report"] = None
                    st.session_state["last_intersection"] = current_intersection_key
                                
                
                # ==========================================
                # 🚀 2. AI 診斷按鈕主體（原本位置直接整段覆蓋）
                # ==========================================
                if st.button("🚀 啟動 AI 多維度工程診斷與整修建議書"):
                    with st.spinner("AI 交通顧問正在交叉比對歷年大數據與台灣地方氣候特徵..."):
                        try:
                            # 🧠 【神升級咒語】注入台灣地方月份氣候對照與思考步驟令
                            prompt_template = """
                            你是一位精通智慧城市與交通工程學（Traffic Engineering）的政府決策顧問專家。
                            請針對台中市[DISTRICT]內，經緯度約為([LAT], [LON])的十字路口，進行事故的【多維度關聯性診斷】。
            
                            歷史大數據交叉統計結果如下：
                            1. 歷年累積事故件數：[TOTAL_CASES]件
                            2. 月份與小時事故高發特徵：[TIME_SUMMARY]
                            3. 天候分佈特徵：[WEATHER_SUMMARY]
                            4. 事故位置特徵：[LOCATION_SUMMARY]
                            5. 官方記錄主要肇事因素統計：[REASON_SUMMARY]
            
                            💡【重要分析步驟：台灣地方氣候與月份衝突交叉比對機制】
                            請你在大腦中優先比對上方數據中的「高發月份」與以下「台灣特有氣候型態」是否存在潛在的複合因果關聯：
                            - 5月 ~ 6月：台灣梅雨季節（連續大雨、路面容易嚴重積水打滑、視線極度不良）。
                            - 7月 ~ 9月：颱風季與極端午後雷陣雨（瞬間暴雨、積水、強風）。
                            - 10月 ~ 翌年1月：冬季東北季風（強風影響機車穩定度、冬季下午 17-18 時天色提早變黑，正逢下班尖峰，視線昏暗）。
            
                            【篩選規則】：
                            - 如果經比對後，發現高發月份、天候描述與上述台灣氣候特徵「有明顯吻合或潛在關聯」，請務必在報告的第二部分『三大潛在複合危險因子』中明確指出，並作為後續實體設施（如排水、照明、防滑）的整修依據。
                            - 如果高發月份大多屬於平穩月份，或天候特徵皆為晴天、與台灣氣候特徵「完全沒有特別關係」，請自動忽略，不需要在報告中硬寫或捏造氣候因素。
            
                            請幫臺中市交通局撰寫一份結構清晰、字數約 250-300 字左右的【路口整修工程決策報告】。
                            you必須嚴格遵循以下格式輸出，並大量使用粗體字標記關鍵字，確保官員能「一眼抓到重點」：
            
                            ### 📊 1. 核心診斷結論
                            （請用 1-2 句話，一針見血地總結該路口最严峻的交通安全核心問題是什麼）
            
                            ### ⚠️ 2. 三大潛在複合危險因子
                            - **[因子一標題]**：結合「時間/天候/位置/主要肇因」推測出第一個隱含的複合危險。（此處請依據上述機制，確認並寫出是否與台灣特定月份氣候相關）。
                            - **[因子二標題]**：結合數據推測出第二個路口環境與行為的衝突點。
                            - **[因子三標題]**：結合數據點出第三個潛在工程或宣導漏洞。
            
                            ### 🛠️ 3. 三大實體工程改善方案（請直接開出具體藥方，拒絕空泛口號）
                            - **[方案一：號誌與車道優化]**：給出具體可動工的標線或號誌微調建議（如：左轉保護時相、反光標線、機車停等區重新規劃）。
                            - **[方案二：實體設施加強]**：增設實體設備建議（針對上述診斷之缺陷，給出如：加強夜間LED照明、增設鋪面防滑係數、改善路口排水）。
                            - **[方案三：科技執法與防制]**：針對該路口核心肇因，提報精準科技執法取締的具體項目（如：取締未依規定讓車、闖紅燈）。
                            """
            
                            # 進行字串動態取代
                            prompt = prompt_template
                            prompt = prompt.replace("[DISTRICT]", str(selected_district))
                            prompt = prompt.replace("[LAT]", f"{clicked_lat:.4f}")
                            prompt = prompt.replace("[LON]", f"{clicked_lon:.4f}")
                            prompt = prompt.replace("[TOTAL_CASES]", str(total_cases))
                            prompt = prompt.replace("[TIME_SUMMARY]", str(time_summary.to_dict(orient='records')))
                            prompt = prompt.replace("[WEATHER_SUMMARY]", str(intersection_df['天候描述'].value_counts().to_dict()))
                            prompt = prompt.replace("[LOCATION_SUMMARY]", str(intersection_df['位置描述'].value_counts().to_dict()))
                            prompt = prompt.replace("[REASON_SUMMARY]", str(reason_summary))
            
                            model = genai.GenerativeModel('gemini-1.5-flash')
                            response = model.generate_content(prompt)
            
                            # 🔒 【關鍵鎖】將生成的報告本文鎖進 Streamlit 網頁記憶體
                            st.session_state["ai_report"] = response.text
            
                        except Exception as e:
                            st.error(f"AI 報告生成失敗: {e}")


                # ==========================================
                # 📝 3. 顯示 AI 報告的區塊
                # （一定要放在按鈕外面！最左邊不能留空格，對齊最外層）
                # ==========================================
                if st.session_state["ai_report"] is not None:
                    st.markdown(f"""
                        <div class="ai-report-box">
                        {st.session_state["ai_report"].replace('### ', '<br><h3>').replace('- **', '<li><b>').replace('**', '</b>')}
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.markdown("<div style='background-color: #ffffff; padding: 40px; text-align: center; border-radius: 10px; border: 2px dashed #cbd5e0; color: #a0aec0; font-weight: 500;'>☝️ 填報準備：請在上方地圖點擊任一【紅色大頭針】以喚醒大數據決策儀表板。</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div style='background-color: #ffffff; padding: 60px; text-align: center; border-radius: 10px; border: 2px dashed #cbd5e0; color: #a0aec0; font-size: 18px; font-weight: 500; margin-top: 50px;'>🏙️ 請在左側邊欄選單選擇你想查詢評估的臺中市行政區。</div>", unsafe_allow_html=True)
else:
    st.warning("⚠️ 載入的資料表為空，請檢查網路連線或 CSV 檔案內容。")
