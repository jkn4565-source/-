import streamlit as st
import requests
import pandas as pd
import json
import xml.etree.ElementTree as ET
import base64
import os
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
    }
    .result-card:hover { border: 1px solid rgba(255, 215, 0, 0.3); }
    .stTextInput input, .stNumberInput input, .stSelectbox div {
        background-color: rgba(0,0,0,0.2) !important; color: white !important;
        border: 1px solid rgba(255,255,255,0.1) !important; border-radius: 8px !important;
    }
    hr { border: 0; border-top: 1px solid rgba(255, 215, 0, 0.1); }
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
        else:
            st.error(f"Claude API 오류 ({resp.status_code}): {resp.text}")
            return None
    except Exception as e:
        st.error(f"API 연결 중 오류 발생: {str(e)}")
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

def 출력_통합_결과_레이아웃(검색어):
    with st.spinner(f"'{검색어}' 최저가 분석 중..."):
        n_list = 필터링(네이버검색(검색어).get('items', []))
        d_list = 도매꾹검색(검색어)
        e_list = 검색_11번가(검색어)

        c1, c2, c3 = st.columns(3)
        platforms = [("🟢 네이버", n_list), ("🔵 도매꾹", d_list), ("🔴 11번가", e_list)]

        for (name, data), col in zip(platforms, [c1, c2, c3]):
            with col:
                st.markdown(f"### {name}")
                if data:
                    best = data[0]
                    st.markdown(f"""
                    <div class="result-card">
                        <img src="{best['이미지']}" style="width:100%; border-radius:8px; margin-bottom:15px;">
                        <h4 style="color:#ffd700; margin:0;">{best['총가격']:,}원</h4>
                        <p style="color:#ccc; font-size:0.9rem; margin:5px 0 15px 0;">{best['제목'][:40]}...</p>
                    </div>
                    """, unsafe_allow_html=True)
                    st.link_button("👑 왕의 소싱처로 이동", best['링크'], type="primary")
                else:
                    st.error("결과 없음")

        combined = sorted(n_list[:10] + d_list[:10] + e_list[:10], key=lambda x: x['총가격'])
        if combined:
            st.divider()
            st.markdown("## 🏆 전체 통합 최저가 순위 TOP 10")
            for i, item in enumerate(combined[:10], 1):
                with st.container():
                    col_img, col_txt, col_btn = st.columns([1, 5, 2])
                    with col_img: st.image(item['이미지'], width=100)
                    with col_txt:
                        st.markdown(f"""
                        <div style="margin-bottom:15px;">
                            <strong style="color:#ffd700; font-size:1.1rem;">{i}. [{item['출처']}]</strong>
                            <span style="color:#fff;">{item['제목']}</span><br>
                            <span style="color:#03C75A; font-weight:bold; font-size:1.2rem;">{item['총가격']:,}원</span>
                        </div>
                        """, unsafe_allow_html=True)
                    with col_btn: st.link_button("구매하러 가기", item['링크'])

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    params = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}
    try: requests.post(url, params=params)
    except: pass

# ==========================================
# 📋 이력 관리 함수 (전역)
# ==========================================
이력파일 = "추천이력.json"

def 이력_로드():
    if os.path.exists(이력파일):
        return json.load(open(이력파일, 'r', encoding='utf-8'))
    return {}

def 이력_저장(날짜, 키워드목록):
    data = 이력_로드()
    기존 = data.get(날짜, [])
    data[날짜] = list(set(기존 + 키워드목록))
    json.dump(data, open(이력파일, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

def 전체_사용된_키워드():
    data = 이력_로드()
    모든키워드 = []
    for kw_list in data.values():
        모든키워드.extend(kw_list)
    return set(모든키워드)

# ==========================================
# 🖥️ 5. 사이드바 메뉴
# ==========================================
st.sidebar.markdown("# 👑 위탁의왕 Ultra")
st.sidebar.markdown("---")
메뉴 = st.sidebar.radio("메뉴 선택", [
    "🏠 홈", "📸 이미지로 검색", "🔎 통합 최저가 검색", "🏪 상품 등록 도우미",
    "💰 마진 계산기", "📦 재고/가격 알림", "💎 블루오션 탐지 + 🤖 자동추천"
], index=0)

# ==========================================
# --- [Menu 1] 홈 ---
# ==========================================
if 메뉴 == "🏠 홈":
    st.markdown("<h1>👑 위탁의왕 자동화 대시보드 v6.0 Ultra</h1>", unsafe_allow_html=True)
    st.caption(f"📅 오늘 날짜: {datetime.now().strftime('%Y-%m-%d')} | 대표님, 오늘도 위탁 시장의 왕이 되어보시죠!")
    st.divider()

    col1, col2, col3 = st.columns(3)
    with col1: st.metric("업무 모드", "매출 폭발 모드 🚀")
    with col2: st.metric("AI 마케터", "Sonnet Ultra")
    with col3: st.metric("디자인 티어", "Royal Gold")

    st.divider()
    st.markdown("""
    <div style="background-color:rgba(255,215,0,0.05); padding:30px; border-radius:15px; border:1px solid rgba(255,215,0,0.1);">
        <h3 style="color:#ffd700; margin-top:0;">👋 위탁의 왕, 대표님 환영합니다!</h3>
        <p style="color:#e0e6ed; line-height:1.8;">
            단순히 상품을 올리고 기다리던 시대는 끝났습니다.<br>
            데이터를 기반으로 최저가를 <b>사냥(Sourcing)</b>하고, AI를 활용해 <b>유혹(Copywriting)</b>해야 합니다.<br><br>
            이 대시보드는 대표님을 단순한 셀러가 아닌, 시장을 지배하는 <b>'위탁의 왕'</b>으로 만들어드리기 위해 진화했습니다.
        </p>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# --- [Menu 2] 이미지로 검색 ---
# ==========================================
elif 메뉴 == "📸 이미지로 검색":
    st.markdown("<h1>📸 AI 이미지 최저가 검색 (Lens Mode)</h1>", unsafe_allow_html=True)
    st.info("💡 상품을 캡처(Win+Shift+S)한 뒤, 아래 초록색 버튼을 클릭만 하세요!")

    with st.container():
        paste_result = paste_image_button(
            label="📋 캡처한 이미지 바로 붙여넣기 (클릭!)",
            background_color="#03C75A",
            hover_background_color="#029f47",
            text_color="#ffffff"
        )

        img_bytes = None

        if paste_result.image_data is not None:
            pil_image = paste_result.image_data
            if pil_image.mode != 'RGB': pil_image = pil_image.convert('RGB')
            pil_image.thumbnail((1500, 1500))
            buffered = io.BytesIO()
            pil_image.save(buffered, format="JPEG")
            img_bytes = buffered.getvalue()

        st.write("---")
        with st.expander("또는 내 컴퓨터의 파일로 업로드하기"):
            up_file = st.file_uploader("파일 선택", type=['jpg', 'jpeg', 'png'])
            if up_file:
                img_bytes = up_file.getvalue()
                pil_image = Image.open(io.BytesIO(img_bytes))
                if pil_image.mode != 'RGB': pil_image = pil_image.convert('RGB')
                pil_image.thumbnail((1500, 1500))
                buffered = io.BytesIO()
                pil_image.save(buffered, format="JPEG")
                img_bytes = buffered.getvalue()

        if img_bytes:
            b64 = base64.b64encode(img_bytes).decode("utf-8")
            st.divider()
            col_u1, col_u2 = st.columns([1, 2])
            with col_u1:
                st.image(img_bytes, width=300, caption="성공적으로 불러왔습니다!")
            with col_u2:
                st.markdown("### 1단계: AI 정밀 분석")
                if st.button("🔍 AI 황금 키워드 9개 추출", key="btn_ai_kw"):
                    with st.spinner("이미지 정밀 분석 중..."):
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

    if st.session_state['keywords_list']:
        st.divider()
        st.markdown("### 2단계: 사냥할 키워드 선택")
        k_list = st.session_state['keywords_list']
        cols = st.columns(3)
        for i, kw in enumerate(k_list):
            if cols[i % 3].button(f"💎 {kw}", key=f"kw_{i}", use_container_width=True):
                st.session_state['keyword_input'] = kw
                st.session_state['run_search'] = True
                st.rerun()

    if 'keyword_input' in st.session_state and st.session_state['keyword_input']:
        st.divider()
        with st.container():
            st.markdown("### 3단계: 통합 검색어")
            search_kw = st.text_input("🔎 검색어 수정", value=st.session_state['keyword_input'], key="input_search_kw")
            if st.button("🛒 실시간 통합 최저가 사냥 시작", type="primary", key="btn_main_search") or st.session_state.get('run_search'):
                st.session_state['run_search'] = False
                if search_kw: 출력_통합_결과_레이아웃(search_kw)

# ==========================================
# --- [Menu 3] 통합 최저가 검색 ---
# ==========================================
elif 메뉴 == "🔎 통합 최저가 검색":
    st.markdown("<h1>🔎 통합 최저가 검색 (텍스트)</h1>", unsafe_allow_html=True)
    with st.container():
        st.caption("텍스트만 입력하여 네이버/도매꾹/11번가의 실시간 최저가를 10위까지 비교합니다.")
        text_kw = st.text_input("사냥할 상품명을 입력하세요", placeholder="예: 무선 가습기", key="input_text_kw")
        if st.button("🚀 왕의 명령: 실시간 통합 비교 시작", type="primary", use_container_width=True, key="btn_text_search"):
            if text_kw: 출력_통합_결과_레이아웃(text_kw)

# ==========================================
# --- [Menu 4] 상품 등록 도우미 ---
# ==========================================
elif 메뉴 == "🏪 상품 등록 도우미":
    st.markdown("<h1>🏪 AI 상세페이지 기획기 (Royal Copywriter)</h1>", unsafe_allow_html=True)
    with st.container():
        j_file = st.file_uploader("상품 사진 업로드", type=['jpg', 'jpeg', 'png'], key="j_up")
        if j_file:
            img_type = j_file.type
            img_bytes = j_file.getvalue()
            col_j1, col_j2 = st.columns([1, 2])
            with col_j1: st.image(img_bytes, width=400)
            with col_j2:
                p_info = st.text_input("상품명 또는 핵심 강조 포인트 (선택사항)", placeholder="예: 무소음, 파스텔 핑크, 안전 인증 완료")
                c1, c2 = st.columns(2)
                target = c1.selectbox("타겟 고객", ["전체", "깐깐한 육아맘", "가성비 따지는 자취생", "트렌디한 2030 직장인", "건강을 챙기는 5060"])
                tone = c2.selectbox("글의 톤앤매너", ["감성을 자극하는 따뜻한 톤", "전문가 느낌의 신뢰감 있는 톤", "유머러스하고 친근한 톤", "결핍을 찌르는 강력한 톤"])
                if st.button("✨ 매혹적인 황금 상세페이지 생성", type="primary", use_container_width=True, key="btn_desc_gen"):
                    with st.spinner("왕실 카피라이터가 기획서를 작성 중입니다..."):
                        b64 = base64.b64encode(img_bytes).decode("utf-8")
                        prompt = f"""당신은 매출을 10배 올려주는 10년 차 탑티어 이커머스 카피라이터입니다.
첨부된 상품 이미지를 철저히 분석하고, 아래의 조건에 맞춰 고객이 당장 사고 싶게 만드는 상세페이지 기획안을 작성해주세요.
[기본 조건] - 타겟 고객: {target} - 글의 톤앤매너: {tone} - 상품 핵심 키워드/특징: {p_info if p_info else "이미지 분석 내용을 바탕으로 창의적으로 도출"}"""
                        body = {
                            "max_tokens": 2000,
                            "messages": [{"role": "user", "content": [
                                {"type": "image", "source": {"type": "base64", "media_type": img_type, "data": b64}},
                                {"type": "text", "text": prompt}
                            ]}]
                        }
                        desc = call_claude_api(body)
                        if desc:
                            st.session_state['helper_generated_text'] = desc
                            st.rerun()

    if st.session_state['helper_generated_text']:
        st.divider()
        with st.container():
            st.markdown("### 📊 완벽한 황금 상세페이지 기획안")
            st.markdown(st.session_state['helper_generated_text'])
            st.divider()
            st.text_area("📋 복사하기 (Ctrl+A로 전체 선택)", value=st.session_state['helper_generated_text'], height=300, key="txt_area_desc")

# ==========================================
# --- [Menu 5] 마진 계산기 ---
# ==========================================
elif 메뉴 == "💰 마진 계산기":
    st.markdown("<h1>💰 스마트 마진 계산기</h1>", unsafe_allow_html=True)
    with st.container():
        col1, col2 = st.columns(2)
        buy_p = col1.number_input("도매가(매입가)", value=10000, key="buy_p")
        ship_p = col1.number_input("매입 배송비", value=3000, key="ship_p")
        target_m = col2.number_input("목표 마진율 (%)", value=30, key="target_m")
        if st.button("🎯 플랫폼별 추천 판매가 계산", type="primary", use_container_width=True):
            fees = {"스마트스토어(6%)": 0.06, "쿠팡(11%)": 0.11, "11번가(13%)": 0.13}
            st.divider()
            f_cols = st.columns(3)
            for i, (name, fee) in enumerate(fees.items()):
                rec = (buy_p + ship_p) / (1 - fee - 0.036 - (target_m / 100))
                with f_cols[i]:
                    st.success(f"{name}")
                    st.metric("판매가", f"{int(rec):,}원")
                    st.write(f"예상마진: {int(rec * (target_m / 100)):,}원")

# ==========================================
# --- [Menu 6] 재고/가격 알림 ---
# ==========================================
elif 메뉴 == "📦 재고/가격 알림":
    st.markdown("<h1>📦 공급처 가격 및 재고 감시</h1>", unsafe_allow_html=True)

    def mask_chat_id(chat_id): return chat_id[:3] + "****" + chat_id[-2:] if chat_id else "미등록"
    st.info(f"🔔 텔레그램 수신 ID: {mask_chat_id(TELEGRAM_CHAT_ID)}")

    재고파일 = "재고모니터링.json"
    def 로드(): return json.load(open(재고파일, 'r', encoding='utf-8')) if os.path.exists(재고파일) else []
    def 저장(d): json.dump(d, open(재고파일, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

    목록 = 로드()
    with st.container():
        with st.expander("➕ 감시 상품 추가", expanded=True):
            c1, c2 = st.columns([2, 1])
            n_no = c1.text_input("도매꾹 상품번호 입력", key="n_no")
            n_name = c2.text_input("관리 이름 입력", key="n_name")
            if st.button("👑 모니터링 명단에 등록", use_container_width=True):
                p = {"ver": "4.1", "aid": DOMEGGOOK_API_KEY, "market": "dome", "om": "json", "mode": "getItemList", "itemNo": n_no}
                item_data = requests.get("https://domeggook.com/ssl/api/", params=p).json()
                if 'domeggook' in item_data and 'list' in item_data['domeggook'] and 'item' in item_data['domeggook']['list']:
                    item_res = item_data['domeggook']['list']['item']
                    item = item_res[0] if isinstance(item_res, list) else item_res
                    if item:
                        목록.append({"no": n_no, "name": n_name, "price": int(item['price']), "상태": "판매중"})
                        저장(목록)
                        st.success("등록되었습니다.")
                        st.rerun()

    st.divider()
    with st.container():
        if st.button("🔄 전수 점검 및 텔레그램 가격체크 시작", type="primary", use_container_width=True):
            with st.spinner("공급처 데이터 전수 확인 중..."):
                for i, s in enumerate(목록):
                    p = {"ver": "4.1", "aid": DOMEGGOOK_API_KEY, "market": "dome", "om": "json", "mode": "getItemList", "itemNo": s['no']}
                    res_data = requests.get("https://domeggook.com/ssl/api/", params=p).json()
                    if 'domeggook' in res_data and 'list' in res_data['domeggook'] and 'item' in res_data['domeggook']['list']:
                        res = res_data['domeggook']['list']['item']
                        res = res[0] if isinstance(res, list) else res
                        if res:
                            now_p = int(res['price'])
                            if now_p > s['price']:
                                send_telegram(f"🔺 <b>가격인상!</b>\n{s['name']}\n{s['price']:,}원 ➔ <b>{now_p:,}원</b>")
                            목록[i]['price'] = now_p
                            목록[i]['상태'] = "판매중"
                    else:
                        if s['상태'] == "판매중":
                            send_telegram(f"🚫 <b>품절!</b>\n{s['name']} 품절발생")
                            목록[i]['상태'] = "품절"
                저장(목록)
                st.success("전수 점검 완료!")
                st.rerun()

        st.divider()
        st.markdown("### 📋 감시 중인 영토")
        for idx, s in enumerate(목록):
            with st.container():
                c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
                c1.markdown(f"**{s['name']}** <span style='color:#777; font-size:0.8rem;'>({s['no']})</span>", unsafe_allow_html=True)
                c2.markdown(f"<strong style='color:#ffd700;'>{s['price']:,}원</strong>", unsafe_allow_html=True)
                상태스타일 = "color:#03C75A; font-weight:bold;" if s['상태'] == "판매중" else "color:#ff4b4b; font-weight:bold;"
                c3.markdown(f"<span style='{상태스타일}'>{s['상태']}</span>", unsafe_allow_html=True)
                if c4.button("삭제", key=f"d_{idx}", type="secondary"):
                    목록.pop(idx)
                    저장(목록)
                    st.rerun()

# ==========================================
# --- [Menu 7] 블루오션 탐지 + AI 자동추천 ---
# ==========================================
elif 메뉴 == "💎 블루오션 탐지 + 🤖 자동추천":
    st.markdown("<h1>💎 블루오션 탐지 + 🤖 AI 자동 일일추천</h1>", unsafe_allow_html=True)

    탭1, 탭2 = st.tabs(["🔍 단일 키워드 분석", "🚀 AI 자동 일일추천 (하루 10개 사냥)"])

    # ── TAB 1 ──────────────────────────────────────────────────────
    with 탭1:
        st.caption("키워드를 입력하면 네이버 전체 등록 상품수를 분석하여 경쟁 강도를 알려드립니다.")
        col_b1, col_b2 = st.columns([3, 1])
        kw = col_b1.text_input("분석할 사냥감(키워드) 입력", key="input_blue_kw")
        btn_ana = col_b2.button("실시간 시장 분석", type="primary", key="btn_blue_ana")
        if btn_ana and kw:
            with st.spinner("네이버 시장 데이터 분석 중..."):
                res = 네이버검색(kw)
                total = res.get('total', 0)
            st.metric("네이버 등록 상품수", f"{total:,}개")
            st.divider()
            if total < 2000:
                st.success("🏆 확실한 블루오션입니다! 지금 바로 소싱하세요.")
                st.balloons()
            elif total < 10000:
                st.info("🟢 경쟁해볼 만한 시장입니다. 상세페이지 차별화가 필요합니다.")
            else:
                st.error("🔴 경쟁이 매우 치열한 레드오션입니다. 다른 키워드를 추천합니다.")

    # ── TAB 2 ──────────────────────────────────────────────────────
    with 탭2:
        st.caption("AI 트렌드 분석 → 블루오션 스캔 → 최저가 소싱 → 이미지 기반 상세페이지 자동 생성")

        # 설정 패널
        col_s1, col_s2, col_s3 = st.columns(3)
        카테고리 = col_s1.selectbox("타겟 카테고리", [
            "자동 탐지 (AI 추천)", "생활용품", "주방용품", "뷰티/헬스",
            "반려동물", "스포츠/레저", "디지털/가전", "패션잡화", "유아동"
        ], key="sel_category")
        타겟가격대 = col_s2.selectbox("타겟 판매가대", [
            "전체", "1만원 이하", "1~3만원", "3~5만원", "5만원 이상"
        ], key="sel_price_range")
        추천수 = col_s3.number_input("추천 상품 수", min_value=3, max_value=10, value=5, key="num_recommend")
        send_tg = st.checkbox("📲 완료 후 텔레그램 발송", value=True, key="chk_telegram")

        st.divider()

        # 이력 현황 표시
        이력data = 이력_로드()
        총키워드수 = sum(len(v) for v in 이력data.values())
        col_hist1, col_hist2, col_hist3 = st.columns([2, 2, 1])
        col_hist1.metric("📋 누적 추천 키워드", f"{총키워드수}개")
        col_hist2.metric("📅 추천 실행 일수", f"{len(이력data)}일")
        with col_hist3:
            if st.button("🗑️ 이력 초기화", key="btn_reset_history", type="secondary"):
                if os.path.exists(이력파일):
                    os.remove(이력파일)
                st.success("초기화 완료!")
                st.rerun()

        if 이력data:
            with st.expander("📖 날짜별 추천 이력 보기"):
                for 날짜, kw_list in sorted(이력data.items(), reverse=True):
                    st.markdown(f"**{날짜}** — {', '.join(kw_list)}")

        st.divider()

        # ── 내부 함수 정의 ─────────────────────────────────────────

        def ai_트렌드_키워드_생성(카테고리, 타겟가격대, 추천수):
            사용된키워드 = 전체_사용된_키워드()
            제외목록 = ", ".join(사용된키워드) if 사용된키워드 else "없음"
            prompt = f"""당신은 한국 스마트스토어/쿠팡 위탁판매 전문 MD입니다.
아래 조건에 맞게 '하루 10개 이상' 팔릴 가능성이 높은 상품 키워드를 추천해주세요.

[조건]
- 카테고리: {카테고리}
- 가격대: {타겟가격대}
- 추천 개수: {추천수}개
- 기준: 계절성/트렌드 반영, 검색량 대비 경쟁 적은 블루오션 위주
- 레드오션(무선이어폰, 텀블러 등) 제외
- ⚠️ 아래 키워드는 이미 추천된 적 있으므로 절대 중복 추천 금지: [{제외목록}]

[출력] 반드시 JSON 배열만. 설명 없음.
[
  {{"keyword":"키워드","reason":"추천이유 한 줄","price_range":"소싱가~판매가"}},
  ...
]"""
            body = {"max_tokens": 1500, "messages": [{"role": "user", "content": prompt}]}
            res = call_claude_api(body)
            if res:
                try:
                    결과 = json.loads(res.replace("```json", "").replace("```", "").strip())
                    결과 = [item for item in 결과 if item['keyword'] not in 사용된키워드]
                    return 결과
                except:
                    st.error("AI 응답 파싱 실패. 다시 시도해주세요.")
            return []

        def 경쟁강도_필터(키워드목록):
            결과 = []
            bar = st.progress(0, text="네이버 경쟁강도 분석 중...")
            for i, item in enumerate(키워드목록):
                res = 네이버검색(item['keyword'], 개수=10)
                total = res.get('total', 999999)
                item['total_count'] = total
                if total < 15000:   item['ocean'], item['score'] = "🟢 블루오션", "상"
                elif total < 50000: item['ocean'], item['score'] = "🟡 중간", "중"
                else:               item['ocean'], item['score'] = "🔴 레드오션", "하"
                결과.append(item)
                bar.progress((i + 1) / len(키워드목록), text=f"분석 중: {item['keyword']} ({total:,}개)")
            bar.empty()
            return sorted(결과, key=lambda x: x['total_count'])

        def 소싱데이터_조회(keyword):
            n = 필터링(네이버검색(keyword, 개수=10).get('items', []))
            d = 도매꾹검색(keyword, 개수=5)
            combined = sorted(n[:5] + d[:5], key=lambda x: x['총가격'])
            return combined[0] if combined else None

        def ai_상세페이지_생성(keyword, 소싱, 추천이유):
            price_info = f"소싱가 {소싱['총가격']:,}원 ({소싱['출처']})" if 소싱 else "소싱가 미확인"
            img_url = 소싱.get('이미지', '') if 소싱 else ''
            img_content = []
            if img_url:
                try:
                    r = requests.get(img_url, timeout=10)
                    if r.status_code == 200:
                        ct = r.headers.get('Content-Type', 'image/jpeg')
                        mt = 'image/png' if 'png' in ct else 'image/gif' if 'gif' in ct else 'image/webp' if 'webp' in ct else 'image/jpeg'
                        b64 = base64.b64encode(r.content).decode('utf-8')
                        img_content = [{"type": "image", "source": {"type": "base64", "media_type": mt, "data": b64}}]
                except:
                    pass

            prompt = f"""당신은 매출을 10배 올려주는 이커머스 카피라이터입니다.
{'첨부 이미지를 분석하고' if img_content else '아래 정보를 바탕으로'} 스마트스토어 상세페이지 기획안을 작성하세요.

[상품 정보]
- 키워드: {keyword}
- {price_info}
- 추천 이유: {추천이유}

### 🏷️ 상품 타이틀 후보 3가지
### 💡 핵심 셀링포인트 3가지
### 📝 상단 후킹 문구
### ✅ 상품 특징 5가지
### 🎯 추천 검색 키워드 10개
### 💰 가격 전략"""

            body = {"max_tokens": 2000, "messages": [{"role": "user", "content": img_content + [{"type": "text", "text": prompt}]}]}
            return call_claude_api(body)

        # ── 실행 버튼 ──────────────────────────────────────────────
        if st.button("🚀 AI 자동 분석 시작 — 오늘의 황금 상품 사냥", type="primary", use_container_width=True, key="btn_auto_daily"):

            결과_목록 = []

            st.markdown("### 🧠 STEP 1 — AI 트렌드 분석")
            with st.spinner("Claude AI가 블루오션 키워드 분석 중..."):
                키워드목록 = ai_트렌드_키워드_생성(카테고리, 타겟가격대, 추천수)
            if not 키워드목록:
                st.error("키워드 생성 실패. 다시 시도해주세요.")
                st.stop()
            st.success(f"✅ {len(키워드목록)}개 키워드 생성 완료!")

            # 이력 저장
            오늘 = datetime.now().strftime('%Y-%m-%d')
            이력_저장(오늘, [item['keyword'] for item in 키워드목록])

            st.markdown("### 📊 STEP 2 — 네이버 경쟁강도 분석")
            키워드목록 = 경쟁강도_필터(키워드목록)

            st.markdown("### 💎 STEP 3 — 소싱 & 상세페이지 자동 생성")
            tg_msg = f"👑 <b>오늘의 위탁왕 자동추천</b> ({datetime.now().strftime('%Y-%m-%d')})\n\n"

            for idx, item in enumerate(키워드목록):
                kw_item = item['keyword']
                icon = '🟢' if item['score'] == '상' else '🟡' if item['score'] == '중' else '🔴'

                with st.expander(f"{icon} #{idx+1} [{item['ocean']}] **{kw_item}** — 경쟁상품 {item['total_count']:,}개", expanded=(idx == 0)):
                    col_a, col_b = st.columns([2, 1])
                    with col_a:
                        st.markdown(f"**추천 이유:** {item['reason']}")
                        st.markdown(f"**예상 가격대:** {item['price_range']}")
                        st.markdown(f"**경쟁 강도:** {item['ocean']} ({item['total_count']:,}개)")
                    with col_b:
                        with st.spinner("최저가 소싱 확인 중..."):
                            소싱 = 소싱데이터_조회(kw_item)
                        if 소싱:
                            st.metric("최저 소싱가", f"{소싱['총가격']:,}원")
                            st.caption(f"출처: {소싱['출처']}")
                            if 소싱.get('이미지'):
                                st.image(소싱['이미지'], width=120, caption="소싱 이미지")
                            st.link_button("소싱처 바로가기 →", 소싱['링크'])
                        else:
                            st.warning("소싱 데이터 없음")

                    st.divider()
                    with st.spinner(f"'{kw_item}' 상세페이지 생성 중..."):
                        상세 = ai_상세페이지_생성(kw_item, 소싱, item['reason'])

                    if 상세:
                        st.markdown("#### 📄 AI 자동 생성 상세페이지 기획안")
                        st.markdown(상세)
                        st.text_area("📋 복사하기 (Ctrl+A → Ctrl+C)", value=상세, height=180, key=f"copy_{idx}")
                        결과_목록.append({
                            "keyword": kw_item, "ocean": item['ocean'],
                            "count": item['total_count'],
                            "소싱가": 소싱['총가격'] if 소싱 else 0,
                            "출처": 소싱['출처'] if 소싱 else "-"
                        })
                        소싱가_txt = f"{소싱['총가격']:,}원 ({소싱['출처']})" if 소싱 else "미확인"
                        tg_msg += f"{idx+1}. <b>{kw_item}</b> {item['ocean']}\n   경쟁: {item['total_count']:,}개 | 소싱가: {소싱가_txt}\n\n"

            if send_tg and 결과_목록:
                tg_msg += f"총 <b>{len(결과_목록)}개</b> 분석 완료 ✅"
                send_telegram(tg_msg)
                st.success("📲 텔레그램으로 결과 발송 완료!")

            if 결과_목록:
                st.divider()
                st.markdown("### 🏆 오늘의 추천 상품 최종 요약")
                df = pd.DataFrame([{
                    "순위": i + 1, "상품키워드": r['keyword'], "경쟁강도": r['ocean'],
                    "네이버경쟁수": f"{r['count']:,}개",
                    "최저소싱가": f"{r['소싱가']:,}원" if r['소싱가'] else "미확인",
                    "소싱출처": r['출처']
                } for i, r in enumerate(결과_목록)])
                st.dataframe(df, use_container_width=True, hide_index=True)
