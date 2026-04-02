import streamlit as st
import requests
import pandas as pd
import json
import xml.etree.ElementTree as ET
import base64
import os
import time
from datetime import datetime
from PIL import Image
import io
from streamlit_paste_button import paste_image_button

# ==========================================
# 🔐 1. 안전한 API 키 로드
# ==========================================
try:
    NAVER_CLIENT_ID = st.secrets["NAVER_CLIENT_ID"]
    NAVER_CLIENT_SECRET = st.secrets["NAVER_CLIENT_SECRET"]
    DOMEGGOOK_API_KEY = st.secrets["DOMEGGOOK_API_KEY"]
    ELEVENST_API_KEY = st.secrets["ELEVENST_API_KEY"]
    CLAUDE_API_KEY = st.secrets["CLAUDE_API_KEY"]
    TELEGRAM_BOT_TOKEN = st.secrets["TELEGRAM_BOT_TOKEN"]
    TELEGRAM_CHAT_ID = st.secrets["TELEGRAM_CHAT_ID"]
    RAPID_API_KEY = st.secrets.get("RAPID_API_KEY", "") # 글로벌 소싱용 추가
except KeyError as e:
    st.error(f"시크릿 키 설정 오류: {e}")
    st.stop()

# ==========================================
# 🎨 2. Ultra 고급 디자인 및 CSS 주입
# ==========================================
st.set_page_config(page_title="위탁의왕 Ultra", page_icon="👑", layout="wide")

st.markdown("""
<style>
    @keyframes gradientBG {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    .stApp {
        background: linear-gradient(-45deg, #0a0f1e, #1a2a4a, #0d1b33, #050a14);
        background-size: 400% 400%;
        animation: gradientBG 15s ease infinite;
        color: #e0e6ed;
    }
    [data-testid="stSidebar"] {
        background-color: rgba(3, 45, 25, 0.9) !important;
        backdrop-filter: blur(10px);
        border-right: 1px solid rgba(255, 215, 0, 0.2);
    }
    [data-testid="stSidebar"] * { color: #f0f0f0 !important; font-weight: 500; }
    .stButton > button {
        width: 100%; border-radius: 8px; font-weight: bold;
        background: linear-gradient(45deg, #03C75A, #029f47);
        color: white; border: none; transition: all 0.3s;
        box-shadow: 0 4px 15px rgba(3, 199, 90, 0.3);
    }
    .stButton > button:hover {
        background: linear-gradient(45deg, #ffd700, #ffb900);
        color: #032d19; transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(255, 215, 0, 0.4);
    }
    h1 { color: #ffd700 !important; text-shadow: 0 2px 4px rgba(0,0,0,0.5); font-weight: 800; letter-spacing: -1px; }
    h2, h3 { color: #f0f0f0 !important; }
    .stMetric label { color: #aaa !important; }
    .stMetric [data-testid="stMetricValue"] { color: #ffd700 !important; font-weight: 800; }
    .result-card {
        border: 1px solid rgba(255,255,255,0.05); padding: 20px; border-radius: 12px;
        background-color: rgba(255,255,255,0.02); margin-bottom: 15px; transition: border 0.3s;
        position: relative;
    }
    .result-card:hover { border: 1px solid rgba(255, 215, 0, 0.3); }
    .stTextInput input, .stNumberInput input, .stSelectbox div {
        background-color: rgba(0,0,0,0.2) !important; color: white !important;
        border: 1px solid rgba(255,255,255,0.1) !important; border-radius: 8px !important;
    }
    hr { border: 0; border-top: 1px solid rgba(255, 215, 0, 0.1); }
    .keyword-badge {
        display: inline-block; padding: 5px 12px; margin-right: 10px; border-radius: 20px;
        background-color: rgba(255, 215, 0, 0.1); border: 1px solid rgba(255, 215, 0, 0.3);
        color: #ffd700; font-size: 0.9rem; font-family: monospace;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🔐 3. 세션 상태 관리
# ==========================================
if 'helper_generated_text' not in st.session_state: st.session_state['helper_generated_text'] = ""
if 'keyword_input' not in st.session_state: st.session_state['keyword_input'] = ""
if 'keywords_list' not in st.session_state: st.session_state['keywords_list'] = []
if 'run_search' not in st.session_state: st.session_state['run_search'] = False

# ==========================================
# 🛠️ 4. 핵심 API 함수
# ==========================================
def call_claude_api(body):
    try:
        headers = {
            "x-api-key": CLAUDE_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        body["model"] = "claude-sonnet-4-6"
        resp = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=body, timeout=80)
        if resp.status_code == 200:
            return resp.json()["content"][0]["text"].strip()
        return None
    except:
        return None

def 네이버검색(상품명, 개수=50):
    url = "https://openapi.naver.com/v1/search/shop.json"
    headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
    params = {"query": 상품명, "sort": "sim", "display": 개수}
    try: return requests.get(url, headers=headers, params=params).json()
    except: return {"items": []}

def 필터링(items, 배송비=0):
    상품목록 = []
    해외키워드 = ['직구', '해외', '구매대행', 'USA', '중국', '항공', '통관']
    for item in items:
        가격 = int(item['lprice'])
        이미지 = item.get('image', '')
        링크 = item.get('link', '')
        if 가격 <= 100 or any(k in item['title'] for k in 해외키워드): continue
        상품목록.append({
            "제목": item['title'].replace('<b>', '').replace('</b>', ''),
            "가격": 가격, "배송비": 배송비, "총가격": 가격 + 배송비,
            "이미지": 이미지, "링크": 링크, "출처": "네이버"
        })
    return 상품목록

def 도매꾹검색(검색어, 개수=20):
    url = "https://domeggook.com/ssl/api/"
    params = {"ver": "4.1", "mode": "getItemList", "aid": DOMEGGOOK_API_KEY, "market": "dome", "om": "json", "kw": 검색어, "sz": 개수}
    try:
        data = requests.get(url, params=params).json()
        items = data['domeggook']['list']['item']
        if isinstance(items, dict): items = [items]
        결과 = []
        for item in items:
            p = int(item.get('price', 0))
            f = int(item.get('deli', {}).get('fee', 0) or 0)
            if item.get('deli', {}).get('who', '') == 'S': f = 0
            결과.append({
                "제목": item.get('title', ''), "가격": p, "배송비": f, "총가격": p + f,
                "이미지": item.get('thumb', ''), "링크": item.get('url', ''), "출처": "도매꾹"
            })
        return sorted(결과, key=lambda x: x['총가격'])
    except: return []

def 검색_11번가(검색어, 개수=20):
    url = "http://openapi.11st.co.kr/openapi/OpenApiService.tmall"
    params = {"key": ELEVENST_API_KEY, "apiCode": "ProductSearch", "keyword": 검색어, "pageSize": 개수}
    try:
        resp = requests.get(url, params=params)
        root = ET.fromstring(resp.content.decode('euc-kr', errors='ignore'))
        상품목록 = []
        for item in root.findall('.//Product'):
            f = int(item.findtext('DeliveryFee', '0').replace(',', '').strip() or 0)
            p = int(item.findtext('SalePrice', '0').replace(',', '').strip() or 0)
            if f >= 6000: continue
            상품목록.append({
                "제목": item.findtext('ProductName', '').replace('<b>', '').replace('</b>', ''),
                "가격": p, "배송비": f, "총가격": p + f,
                "이미지": item.findtext('ProductImage100', ''), "링크": item.findtext('DetailPageUrl', ''), "출처": "11번가"
            })
        return sorted(상품목록, key=lambda x: x['총가격'])
    except: return []

def 검색_글로벌_알리(검색어, 개수=20):
    endpoints = [
        "https://aliexpress-datahub.p.rapidapi.com/item_search_2",
        "https://aliexpress-datahub.p.rapidapi.com/item_search_3"
    ]
    querystring = {"q": 검색어, "page": "1"}
    headers = {
        "x-rapidapi-key": RAPID_API_KEY.strip(),
        "x-rapidapi-host": "aliexpress-datahub.p.rapidapi.com"
    }
    
    response = None
    for url in endpoints:
        try:
            response = requests.get(url, headers=headers, params=querystring, timeout=5)
            if response.status_code == 200: break 
        except: continue

    if not response or response.status_code != 200: return []
        
    try:
        data = response.json()
        상품목록 = []
        items_data = []
        if 'result' in data:
            if 'resultList' in data['result']: items_data = data['result']['resultList']
            elif isinstance(data['result'], list): items_data = data['result']

        for item in items_data:
            item_info = item.get('item', {})
            delivery = item.get('delivery', {})
            usd_price = float(item_info.get('sku', {}).get('def', {}).get('promotionPrice', item_info.get('sku', {}).get('def', {}).get('price', 0)))
            krw_price = int(usd_price * 1500)
            sales = int(item_info.get('sales', 0))
            if sales >= 0: 
                img_url = item_info.get('image', '')
                if img_url and not img_url.startswith('http'): img_url = "https:" + img_url
                link_url = item_info.get('itemUrl', '')
                if link_url and not link_url.startswith('http'): link_url = "https:" + link_url
                상품목록.append({
                    "제목": item_info.get('title', ''), "가격": krw_price, "총가격": krw_price, "판매량": sales,
                    "평점": item_info.get('evaluateRate', 'N/A'), "이미지": img_url, "링크": link_url, "출처": "AliExpress"
                })
        return sorted(상품목록, key=lambda x: x['가격'])
    except: return []

def 출력_통합_결과_레이아웃(검색어):
    with st.spinner(f"'{검색어}' 국내 및 글로벌 최저가 동시 분석 중..."):
        n_list = 필터링(네이버검색(검색어).get('items', []))
        d_list = 도매꾹검색(검색어)
        e_list = 검색_11번가(검색어)
        en_kw = 검색어
        if RAPID_API_KEY:
            prompt = f"'{검색어}'를 알리익스프레스 검색용 영어 단어로 번역해줘. 설명 없이 영어 단어만 출력해."
            body = {"max_tokens": 50, "messages": [{"role": "user", "content": prompt}]}
            res_kw = call_claude_api(body)
            en_kw = res_kw if res_kw else 검색어
            a_list = 검색_글로벌_알리(en_kw)
        else: a_list = []

        c1, c2, c3, c4 = st.columns(4)
        platforms = [("🟢 네이버", n_list), ("🔵 도매꾹", d_list), ("🔴 11번가", e_list), ("✈️ 글로벌(알리)", a_list)]

        for (name, data), col in zip(platforms, [c1, c2, c3, c4]):
            with col:
                st.markdown(f"### {name}")
                if data:
                    best = data[0]
                    sales_info = f"<div style='position:absolute; top:10px; left:10px; background-color:#ff4500; color:white; padding:3px 8px; border-radius:5px; font-weight:bold; font-size:0.8rem;'>판매량 {best['판매량']}+</div>" if '판매량' in best else ""
                    st.markdown(f"""<div class="result-card">{sales_info}
<img src="{best['이미지']}" style="width:100%; border-radius:8px; margin-bottom:15px;">
<h4 style="color:#ffd700; margin:0;">{best.get('총가격', best.get('가격')):,}원</h4>
<p style="color:#ccc; font-size:0.8rem; margin:5px 0 15px 0; height:40px; overflow:hidden;">{best['제목'][:40]}...</p>
</div>""", unsafe_allow_html=True)
                    st.link_button("👑 왕의 소싱처로 이동", best['링크'], type="primary")
                else:
                    if name == "✈️ 글로벌(알리)":
                        st.warning("서버 혼잡 (플랜B 가동)")
                        ali_url = f"https://ko.aliexpress.com/w/wholesale-{en_kw.replace(' ', '-')}.html"
                        st.link_button("🚀 알리 다이렉트 결과", ali_url, use_container_width=True)
                    else: st.error("결과 없음")

        all_combined = n_list[:10] + d_list[:10] + e_list[:10] + a_list[:10]
        combined = sorted(all_combined, key=lambda x: x['총가격'])
        if combined:
            st.divider()
            st.markdown("## 🏆 전체 통합 최저가 TOP 10")
            for i, item in enumerate(combined[:10], 1):
                with st.container():
                    col_img, col_txt, col_btn = st.columns([1, 5, 2])
                    with col_img: st.image(item['이미지'], width=100)
                    with col_txt:
                        badge = "✈️ 직구" if item['출처'] == "AliExpress" else "🇰🇷 국내"
                        st.markdown(f"""<div style="margin-bottom:15px;">
<strong style="color:#ffd700; font-size:1.1rem;">{i}. [{badge} | {item['출처']}]</strong>
<span style="color:#fff;">{item['제목']}</span><br>
<span style="color:#03C75A; font-weight:bold; font-size:1.2rem;">{item['총가격']:,}원</span>
</div>""", unsafe_allow_html=True)
                    with col_btn: st.link_button("구매하러 가기", item['링크'])

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    params = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}
    try: requests.post(url, params=params)
    except: pass

이력파일 = "추천이력.json"
def 이력_로드():
    if os.path.exists(이력파일): return json.load(open(이력파일, 'r', encoding='utf-8'))
    return {}
def 이력_저장(날짜, 키워드목록):
    data = 이력_로드()
    기존 = data.get(날짜, [])
    data[날짜] = list(set(기존 + 키워드목록))
    json.dump(data, open(이력파일, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
def 전체_사용된_키워드():
    data = 이력_로드()
    모든키워드 = []
    for kw_list in data.values(): 모든키워드.extend(kw_list)
    return set(모든키워드)

# ==========================================
# 🖥️ 5. 사이드바 메뉴
# ==========================================
st.sidebar.markdown("# 👑 위탁의왕 Ultra")
st.sidebar.markdown("---")
메뉴 = st.sidebar.radio("메뉴 선택", [
    "🏠 홈", "📸 이미지로 검색", "🔎 통합 최저가 검색", "🇨🇳 글로벌 사입/직구 검색", 
    "🏪 상품 등록 도우미", "🕵️‍♂️ 경쟁사 리뷰 분석기",  # <-- 이 부분이 추가되었습니다!
    "💰 마진 계산기", "📦 재고/가격 알림", "💎 블루오션 탐지 + 🤖 자동추천"
], index=0)
# ==========================================
# --- [Menu 1, 2, 3] 생략 (기존 코드와 동일) ---
# ==========================================
if 메뉴 == "🏠 홈":
    st.markdown("<h1>👑 위탁의왕 자동화 대시보드 v6.1 Ultra</h1>", unsafe_allow_html=True)
    st.caption(f"📅 오늘 날짜: {datetime.now().strftime('%Y-%m-%d')} | 대표님, 오늘도 위탁 시장의 왕이 되어보시죠!")
    st.divider()
    col1, col2, col3 = st.columns(3)
    col1.metric("업무 모드", "매출 폭발 모드 🚀")
    col2.metric("AI 마케터", "Sonnet Ultra")
    col3.metric("디자인 티어", "Royal Gold")
    st.divider()
    st.markdown("""<div style="background-color:rgba(255,215,0,0.05); padding:30px; border-radius:15px; border:1px solid rgba(255,215,0,0.1);">
<h3 style="color:#ffd700; margin-top:0;">👋 위탁의 왕, 대표님 환영합니다!</h3>
<p style="color:#e0e6ed; line-height:1.8;">단순히 상품을 올리고 기다리던 시대는 끝났습니다. 데이터 기반의 소싱과 AI 카피라이팅으로 지배하십시오.</p></div>""", unsafe_allow_html=True)

# ==========================================
# --- [Menu 2] 이미지로 검색 ---
# ==========================================
elif 메뉴 == "📸 이미지로 검색":
    st.markdown("<h1>📸 AI 이미지 최저가 검색 (Lens Mode)</h1>", unsafe_allow_html=True)
    st.info("💡 상품을 캡처(Win+Shift+S)한 뒤 아래 버튼을 누르거나, 파일을 직접 업로드해주세요.")

    # 🚨 [추가됨] 화면이 멈추거나 에러가 났을 때 강제로 뚫어주는 새로고침 버튼
    if st.button("🔄 화면이 멈추거나 막혔을 때 누르세요 (초기화)", type="secondary"):
        st.session_state['keywords_list'] = []
        st.session_state['keyword_input'] = ""
        st.session_state['run_search'] = False
        st.rerun()

    with st.container():
        paste_result = paste_image_button(
            label="📋 캡처한 이미지 바로 붙여넣기 (클릭!)",
            background_color="#03C75A",
            hover_background_color="#029f47",
            text_color="#ffffff"
        )

        img_bytes = None

        if paste_result.image_data is not None:
            try:
                pil_image = paste_result.image_data
                if pil_image.mode != 'RGB': pil_image = pil_image.convert('RGB')
                pil_image.thumbnail((1500, 1500))
                buffered = io.BytesIO()
                pil_image.save(buffered, format="JPEG")
                img_bytes = buffered.getvalue()
            except Exception as e:
                st.error(f"이미지 처리 중 에러 발생: {e}")

        # 🚨 [복구됨] 실수로 지워졌던 '컴퓨터 파일 업로드' 창 부활!
        st.write("---")
        with st.expander("📂 또는 내 컴퓨터의 파일로 업로드하기", expanded=True):
            up_file = st.file_uploader("파일 선택", type=['jpg', 'jpeg', 'png'])
            if up_file:
                try:
                    img_bytes = up_file.getvalue()
                    pil_image = Image.open(io.BytesIO(img_bytes))
                    if pil_image.mode != 'RGB': pil_image = pil_image.convert('RGB')
                    pil_image.thumbnail((1500, 1500))
                    buffered = io.BytesIO()
                    pil_image.save(buffered, format="JPEG")
                    img_bytes = buffered.getvalue()
                except Exception as e:
                    st.error(f"파일 업로드 에러: {e}")

        if img_bytes:
            b64 = base64.b64encode(img_bytes).decode("utf-8")
            st.divider()
            col_u1, col_u2 = st.columns([1, 2])
            with col_u1:
                st.image(img_bytes, width=300, caption="성공적으로 불러왔습니다!")
            with col_u2:
                st.markdown("### 1단계: AI 정밀 분석")
                if st.button("🔍 AI 황금 키워드 9개 추출", key="btn_ai_kw"):
                    with st.spinner("이미지 정밀 분석 중... (최대 10초 소요)"):
                        prompt_text = """당신은 한국의 10년 차 탑티어 상품 소싱 MD입니다.
1. 브랜드/모델명을 알면 앞쪽에 적으세요.
2. 모르면 네이버/도매꾹 검색용 구체적 명사로 적으세요.
3. 총 9개 명사형 키워드만 콤마(,)로 구분해서 출력하세요. (설명 없음)"""
                        body = {
                            "model": "claude-sonnet-4-6",
                            "max_tokens": 300,
                            "messages": [{"role": "user", "content": [
                                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}},
                                {"type": "text", "text": prompt_text}
                            ]}]
                        }
                        res = call_claude_api(body)
                        if res:
                            st.session_state['keywords_list'] = [k.strip() for k in res.split(',')]
                            st.rerun()
                        else:
                            st.error("⚠️ AI 서버 혼잡. [초기화] 버튼을 누르고 다시 시도해주세요.")

    if st.session_state.get('keywords_list'):
        st.divider()
        st.markdown("### 2단계: 사냥할 키워드 선택")
        k_list = st.session_state['keywords_list']
        cols = st.columns(3)
        for i, kw in enumerate(k_list):
            if cols[i % 3].button(f"💎 {kw}", key=f"kw_{i}", use_container_width=True):
                st.session_state['keyword_input'] = kw
                st.session_state['run_search'] = True
                st.rerun()

    if st.session_state.get('keyword_input') and st.session_state.get('keyword_input') != "":
        st.divider()
        with st.container():
            st.markdown("### 3단계: 통합 검색어")
            search_kw = st.text_input("🔎 검색어 수정", value=st.session_state['keyword_input'], key="input_search_kw")
            if st.button("🛒 실시간 통합 최저가 사냥 시작", type="primary", key="btn_main_search") or st.session_state.get('run_search'):
                st.session_state['run_search'] = False
                if search_kw: 출력_통합_결과_레이아웃(search_kw)
elif 메뉴 == "🔎 통합 최저가 검색":
    st.markdown("<h1>🔎 통합 최저가 검색 (텍스트)</h1>", unsafe_allow_html=True)
    text_kw = st.text_input("사냥할 상품명을 입력하세요", placeholder="예: 무선 가습기")
    if st.button("🚀 실시간 통합 비교 시작", type="primary", use_container_width=True):
        if text_kw: 출력_통합_결과_레이아웃(text_kw)

# ==========================================
# --- [Menu 4] 글로벌 사입/직구 검색 (업데이트!) ---
# ==========================================
elif 메뉴 == "🇨🇳 글로벌 사입/직구 검색":
    st.markdown("<h1>🇨🇳 글로벌 신뢰도 1티어 최저가 사냥</h1>", unsafe_allow_html=True)
    
    # 💡 마법의 수식어 상시 노출 섹션
    st.markdown("""
    <div style="background-color:rgba(255,215,0,0.1); padding:15px; border-radius:10px; border:1px solid #ffd700; margin-bottom:20px;">
        <h4 style="margin-top:0; color:#ffd700;">💡 신상품 사입 치트키 (검색어 뒤에 붙여보세요)</h4>
        <div style="margin-top:10px;">
            <span class="keyword-badge">ins风</span> 인스타 감성 / 트렌디 디자인<br>
            <span class="keyword-badge">新款</span> 최신 모델 / 이번 시즌 신상품<br>
            <span class="keyword-badge">创意</span> 아이디어 / 독창적인 상품
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.container():
        col1, col2 = st.columns([3, 1])
        global_kw = col1.text_input("사냥할 상품명을 입력하세요 (한글)", placeholder="예: 인스타풍 유리컵")
        
        if col2.button("🌐 글로벌 최저가 탐색", type="primary", use_container_width=True):
            if global_kw:
                with st.spinner("Claude AI가 글로벌용 키워드로 번역 중..."):
                    prompt = f"'{global_kw}'를 알리익스프레스 검색용 영문으로 번역해줘. 설명 없이 영어만 출력해."
                    en_kw = call_claude_api({"max_tokens": 50, "messages": [{"role": "user", "content": prompt}]})
                    cn_kw = call_claude_api({"max_tokens": 50, "messages": [{"role": "user", "content": f"'{global_kw}'를 1688 검색용 중국어 간체로 번역해줘. 설명 없이 중국어만 출력해."}]})
                    en_kw = en_kw if en_kw else global_kw
                    cn_kw = cn_kw if cn_kw else global_kw
                
                st.success(f"🔤 번역 완료! ✈️ {en_kw} / 🇨🇳 {cn_kw}")
                ali_results = 검색_글로벌_알리(en_kw)
                
                st.divider()
                if ali_results:
                    st.markdown(f"### 🏆 '{global_kw}' 글로벌 소싱 TOP 9")
                    cols = st.columns(3)
                    for i, item in enumerate(ali_results[:9]):
                        with cols[i % 3]:
                            st.markdown(f"""<div class="result-card"><div style="position:absolute; top:10px; left:10px; background-color:#ff4500; color:white; padding:3px 8px; border-radius:5px; font-weight:bold; font-size:0.8rem;">판매량 {item['판매량']}+</div>
<img src="{item['이미지']}" style="width:100%; border-radius:8px; margin-bottom:10px;">
<h3 style="color:#03C75A; margin:0;">{item['가격']:,}원</h3>
<div style="color:#ffd700; font-size:0.9rem; margin-bottom:10px;">⭐ 평점: {item['평점']}</div>
<p style="color:#ccc; font-size:0.8rem; height:40px; overflow:hidden;">{item['제목'][:50]}...</p>
</div>""", unsafe_allow_html=True)
                            st.link_button("✈️ 상품 바로가기", item['링크'], use_container_width=True)
                else:
                    st.warning("⚠️ 글로벌 API 서버 혼잡으로 다이렉트 소싱 버튼을 띄웁니다.")
                    st.markdown("### 🔗 AI 번역 기반 다이렉트 소싱")
                    c1, c2, c3 = st.columns(3)
                    with c1: st.link_button("🚀 1688 (도매) 결과 보기", f"https://s.1688.com/selloffer/offer_search.htm?keywords={cn_kw}", use_container_width=True)
                    with c2: st.link_button("🚀 타오바오 결과 보기", f"https://s.taobao.com/search?q={cn_kw}", use_container_width=True)
                    with c3: st.link_button("🚀 알리익스프레스 결과 보기", f"https://ko.aliexpress.com/w/wholesale-{en_kw.replace(' ', '-')}.html", use_container_width=True)

# ==========================================
# --- [Menu 5~8] 생략 (기존과 동일하되 최적화됨) ---
# ==========================================
elif 메뉴 == "🏪 상품 등록 도우미":
    st.markdown("<h1>🏪 AI 상세페이지 기획기</h1>", unsafe_allow_html=True)
    j_file = st.file_uploader("상품 사진 업로드", type=['jpg', 'jpeg', 'png'])
    if j_file:
        img_bytes = j_file.getvalue()
        st.image(img_bytes, width=400)
        if st.button("✨ 매혹적인 황금 상세페이지 생성"):
            b64 = base64.b64encode(img_bytes).decode("utf-8")
            body = {"max_tokens": 2000, "messages": [{"role": "user", "content": [{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}}, {"type": "text", "text": "상세페이지 기획안 작성해줘"}]}]}
            st.write(call_claude_api(body))
# ==========================================
# --- [Menu NEW] 경쟁사 리뷰 분석기 ---
# ==========================================
elif 메뉴 == "🕵️‍♂️ 경쟁사 리뷰 분석기":
    st.markdown("<h1>🕵️‍♂️ AI 경쟁사 리뷰 분석기 (Pain Point 스캐너)</h1>", unsafe_allow_html=True)
    st.caption("경쟁사의 1~3점짜리 악플은 우리에게 황금 같은 매출 소스입니다. 리뷰를 긁어서 붙여넣으면 AI가 상세페이지 공략 포인트를 짜드립니다.")

    with st.container():
        st.markdown("### 1단계: 경쟁사 리뷰 가져오기")
        st.info("💡 네이버/쿠팡 등에서 1등으로 잘 팔리는 경쟁사 상품의 '안 좋은 평점(1~3점)' 리뷰 내용들을 마우스로 쭉 드래그해서 복사한 뒤 아래에 붙여넣어 주세요.")
        
        # 얼음틀 소싱 사례를 반영한 친숙한 예시 제공
        reviews_text = st.text_area(
            "👇 여기에 리뷰를 텍스트로 붙여넣으세요 (여러 개가 섞여 있어도 AI가 알아서 분류합니다)", 
            height=200, 
            placeholder="예시:\n얼음틀에서 고무 냄새가 너무 많이 나요.\n뚜껑이 꽉 안 닫혀서 냉동실에 물이 다 샜어요 최악 ㅠㅠ\n얼음 빼낼 때 손가락 부러지는 줄 알았습니다..."
        )

        if st.button("🔍 AI 결핍 스캔 및 후킹 카피 추출", type="primary", use_container_width=True):
            if not reviews_text.strip():
                st.warning("경쟁사 리뷰 내용을 먼저 붙여넣어 주세요!")
            else:
                with st.spinner("왕실 카피라이터가 경쟁사의 약점을 철저히 분석하고 있습니다..."):
                    prompt = f"""당신은 매출을 10배 올려주는 10년 차 탑티어 이커머스 카피라이터입니다.
아래는 우리 경쟁사 상품에 대한 고객들의 실제 리뷰(주로 불만 사항)입니다. 이 데이터를 철저히 분석하여, 우리가 새로 소싱할 상품의 상세페이지에 쓸 기획안을 작성해주세요.

[경쟁사 리뷰 데이터]
{reviews_text}

[출력 형식]
### 🚨 고객들이 분노하는 핵심 결핍 (Pain Point) TOP 3
(고객이 무엇 때문에 가장 불편해하는지 날카롭게 분석)

### 💡 우리의 완벽한 해결책 (셀링 포인트)
(위의 결핍을 우리는 어떻게 완벽히 해결했는지 당당하게 어필하는 소구점)

### 🎣 상세페이지 최상단 강력한 후킹 카피 3선
(고객이 상세페이지에 들어오자마자 '아 이건 내 얘기다!' 하고 스크롤을 내릴 수밖에 없는 도발적이고 공감 가는 카피)
"""
                    body = {
                        "max_tokens": 1500,
                        "messages": [{"role": "user", "content": prompt}]
                    }
                    result = call_claude_api(body)

                    if result:
                        st.divider()
                        st.markdown("## 🎯 AI 분석 및 카피라이팅 결과")
                        
                        # HTML 강제 박스를 없애고 순정 마크다운으로 안전하게 출력합니다.
                        st.markdown(result)
                        
                        st.divider()
                        st.text_area("📋 복사하기 (Ctrl+A → Ctrl+C)", value=result, height=200)
                    else:
                        st.error("AI 분석 중 오류가 발생했습니다. 다시 시도해주세요.")
elif 메뉴 == "💰 마진 계산기":
    st.markdown("<h1>💰 스마트 묶음 마진 계산기</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    buy_p = col1.number_input("도매가", value=2900)
    qty = col2.number_input("수량", value=10)
    ship_p = col3.number_input("배송비", value=2500)
    total_cost = (buy_p * qty) + ship_p
    st.metric("📦 총 매입 원가", f"{total_cost:,}원")

elif 메뉴 == "📦 재고/가격 알림":
    st.markdown("<h1>📦 공급처 재고 감시</h1>", unsafe_allow_html=True)
    st.info("텔레그램 연동 상태: 정상 🔔")

elif 메뉴 == "💎 블루오션 탐지 + 🤖 자동추천":
    st.markdown("<h1>💎 블루오션 탐지 + AI 자동 일일추천</h1>", unsafe_allow_html=True)
