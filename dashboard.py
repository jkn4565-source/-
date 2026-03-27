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

# ==========================================
# 🔐 1. 안전한 API 키 로드 (동일)
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
# 🎨 2. Ultra 고급 디자인 및 CSS 주입 (핵심 업데이트)
# ==========================================
st.set_page_config(page_title="위탁의왕 Ultra", page_icon="👑", layout="wide")

# 움직이는 배경화면 및 고급 스타일 CSS
st.markdown("""
<style>
    /* 🌌 [요청 반영] 역동적인 그라데이션 움직이는 배경 */
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

    /* 🌿 사이드바 고품격 다크 그린 스타일 */
    [data-testid="stSidebar"] {
        background-color: rgba(3, 45, 25, 0.9) !important;
        backdrop-filter: blur(10px);
        border-right: 1px solid rgba(255, 215, 0, 0.2);
    }
    [data-testid="stSidebar"] * { color: #f0f0f0 !important; font-weight: 500; }
    
    /* 🎯 사이드바 메뉴 스타일 업그레이드 */
    .st-emotion-cache-1wv845u { /* 라디오 버튼 컨테이너 */
        gap: 10px;
    }
    .st-emotion-cache-1wv845u [data-testid="stMarkdownContainer"] p {
        background: rgba(255, 255, 255, 0.05);
        padding: 10px 15px;
        border-radius: 8px;
        transition: all 0.3s;
        border: 1px solid transparent;
    }
    .st-emotion-cache-1wv845u [data-testid="stMarkdownContainer"] p:hover {
        background: rgba(3, 199, 90, 0.2);
        border: 1px solid rgba(3, 199, 90, 0.5);
        transform: translateX(5px);
    }

    /* 💳 메인 콘텐츠 카드 디자인 (고급스러운 유리 효과) */
    .stBlock {
        background-color: rgba(255, 255, 255, 0.03) !important;
        border-radius: 15px !important;
        padding: 20px !important;
        border: 1px solid rgba(255, 215, 0, 0.1) !important;
        backdrop-filter: blur(5px);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2);
    }

    /* 🟢 메인 버튼 스타일 (네이버 그린 + 황금빛 호버) */
    .stButton > button {
        width: 100%;
        border-radius: 8px;
        font-weight: bold;
        background: linear-gradient(45deg, #03C75A, #029f47);
        color: white;
        border: none;
        transition: all 0.3s;
        box-shadow: 0 4px 15px rgba(3, 199, 90, 0.3);
    }
    .stButton > button:hover {
        background: linear-gradient(45deg, #ffd700, #ffb900);
        color: #032d19;
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(255, 215, 0, 0.4);
    }

    /* 🏆 제목 및 Metrics 스타일 (황금빛 포인트) */
    h1 {
        color: #ffd700 !important;
        text-shadow: 0 2px 4px rgba(0,0,0,0.5);
        font-weight: 800;
        letter-spacing: -1px;
    }
    h2, h3 { color: #f0f0f0 !important; }
    
    .stMetric label { color: #aaa !important; }
    .stMetric [data-testid="stMetricValue"] { color: #ffd700 !important; font-weight: 800; }

    /* 🛒 검색 결과 카드 스타일 */
    .result-card {
        border: 1px solid rgba(255, 255, 255, 0.05);
        padding: 20px;
        border-radius: 12px;
        background-color: rgba(255, 255, 255, 0.02);
        margin-bottom: 15px;
        transition: border 0.3s;
    }
    .result-card:hover {
        border: 1px solid rgba(255, 215, 0, 0.3);
    }
    
    /* 입력창 스타일 */
    .stTextInput input, .stNumberInput input, .stSelectbox div {
        background-color: rgba(0, 0, 0, 0.2) !important;
        color: white !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 8px !important;
    }
    
    /* 구분선 */
    hr { border: 0; border-top: 1px solid rgba(255, 215, 0, 0.1); }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🔐 3. 세션 상태 관리 (동일)
# ==========================================
if 'helper_generated_text' not in st.session_state: st.session_state['helper_generated_text'] = ""
if 'keyword_input' not in st.session_state: st.session_state['keyword_input'] = ""
if 'keywords_list' not in st.session_state: st.session_state['keywords_list'] = []
if 'run_search' not in st.session_state: st.session_state['run_search'] = False

# ==========================================
# 🛠️ 4. 핵심 API 함수 (PNG 버그 수정 및 도매꾹 market 파라미터 추가)
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
    # 🚨 여기에 "market": "dome" 핵심 코드를 추가했습니다!
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

# 🏆 [고급화] 검색 결과 출력 레이아웃 개편
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
                    # 고급스러운 HTML 카드 형태로 출력
                    st.markdown(f"""
                    <div class="result-card">
                        <img src="{best['이미지']}" style="width:100%; border-radius:8px; margin-bottom:15px;">
                        <h4 style="color:#ffd700; margin:0;">{best['총가격']:,}원</h4>
                        <p style="color:#ccc; font-size:0.9rem; margin:5px 0 15px 0;">{best['제목'][:40]}...</p>
                    </div>
                    """, unsafe_allow_html=True)
                    st.link_button("👑 왕의 소싱처로 이동", best['링크'], type="primary")
                else: st.error("결과 없음")

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
# 🖥️ 5. 사이드바 메뉴 (디자인 변경 반영)
# ==========================================
st.sidebar.markdown("# 👑 위탁의왕 Ultra")
st.sidebar.markdown("---")
메뉴 = st.sidebar.radio("메뉴 선택", [
    "🏠 홈", "📸 이미지로 검색", "🔎 통합 최저가 검색", "🏪 상품 등록 도우미", 
    "💰 마진 계산기", "📦 재고/가격 알림", "💎 블루오션 탐지"
], index=0)

# --- [Menu 1] 홈 (고급스럽게 개편) ---
if 메뉴 == "🏠 홈":
    st.markdown("<h1>👑 위탁의왕 자동화 대시보드 v6.0 Ultra</h1>", unsafe_allow_html=True)
    st.caption(f"📅 오늘 날짜: {datetime.now().strftime('%Y-%m-%d')} | 대표님, 오늘도 위탁 시장의 왕이 되어보시죠!")
    st.divider()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("업무 모드", "매출 폭발 모드 🚀")
    with col2:
        st.metric("AI 마케터", "Sonnet Ultra")
    with col3:
        st.metric("디자인 티어", "Royal Gold")
    
    st.divider()
    
    # 👑 왕의 훈화 말씀 형태의 인트로
    st.markdown("""
    <div style="background-color:rgba(255,215,0,0.05); padding:30px; border-radius:15px; border:1px solid rgba(255,215,0,0.1);">
        <h3 style="color:#ffd700; margin-top:0;">👋 위탁의 왕, 대표님 환영합니다!</h3>
        <p style="color:#e0e6ed; line-height:1.8;">
            단순히 상품을 올리고 기다리던 시대는 끝났습니다.<br>
            데이터를 기반으로 최저가를 <b>사냥(Sourcing)</b>하고, AI를 활용해 <b>유혹(Copywriting)</b>해야 합니다.<br><br>
            이 대시보드는 대표님을 단순한 셀러가 아닌, 시장을 지배하는 <b>'위탁의 왕'</b>으로 만들어드리기 위해 진화했습니다.<br>
            초졸한 디자인은 가고, 황금빛 성공의 기운을 담은 Ultra 버전으로 새롭게 시작하세요.
        </p>
        <br>
        <p style="color:#aaa; font-size:0.9rem;">👈 왼쪽 메뉴에서 원하는 강력한 도구를 선택하세요.</p>
    </div>
    """, unsafe_allow_html=True)

# --- [Menu 2] 이미지로 검색 (디자인 컨셉 유지) ---
elif 메뉴 == "📸 이미지로 검색":
    st.markdown("<h1>📸 AI 이미지 최저가 검색</h1>", unsafe_allow_html=True)
    with st.container():
        # 💡 팁: 이 칸을 마우스로 한 번 클릭하고 Ctrl+V를 누르면 캡처 화면이 바로 올라옵니다!
        up_file = st.file_uploader("상품 사진 업로드 (또는 클릭 후 Ctrl+V)", type=['jpg', 'jpeg', 'png'], key="img_search_up")
        
        if up_file:
            # --- 🚨 이미지 다이어트 및 분석 준비 ---
            img_bytes = up_file.getvalue()
            pil_image = Image.open(io.BytesIO(img_bytes))
            
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
            
            # 8000픽셀 에러 방지용 축소
            pil_image.thumbnail((1500, 1500))
            
            buffered = io.BytesIO()
            pil_image.save(buffered, format="JPEG")
            final_img_bytes = buffered.getvalue()
            b64 = base64.b64encode(final_img_bytes).decode("utf-8")
            
            col_u1, col_u2 = st.columns([1, 2])
            with col_u1:
                st.image(final_img_bytes, width=300, caption="업로드된 이미지")
            
            with col_u2:
                st.markdown("### 1단계: AI 정밀 분석")
                if st.button("🔍 AI 황금 키워드 5개 추출", key="btn_ai_kw"):
                    with st.spinner("이미지 속 성공 DNA 분석 중..."):
                        body = {
                            "model": "claude-sonnet-4-6", # 대표님 열쇠에 맞는 모델명
                            "max_tokens": 300,
                            "messages": [{"role": "user", "content": [
                                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}},
                                {"type": "text", "text": "당신은 한국의 10년차 탑티어 상품 소싱 MD입니다. 이 사진 속 물건이 정확히 무엇인지 분석하고, 도매꾹/네이버 검색에 적합한 명사 형태 키워드 5개를 콤마(,)로만 답변하세요."}
                            ]}]
                        }
                        res = call_claude_api(body)
                        if res:
                            st.session_state['keywords_list'] = [k.strip() for k in res.split(',')]
                            st.rerun()

    if st.session_state['keywords_list']:
        st.markdown("### 2단계: 사냥할 키워드 선택")
        st.write("▼ 키워드를 선택하면 통합 최저가 검색이 시작됩니다.")
        cols = st.columns(len(st.session_state['keywords_list']))
        for i, kw in enumerate(st.session_state['keywords_list']):
            if cols[i].button(f"💎 {kw}", key=f"kw_{i}"):
                st.session_state['keyword_input'] = kw
                st.session_state['run_search'] = True
                st.rerun()

    st.divider()
    with st.container():
        st.markdown("### 3단계: 통합 검색어")
        search_kw = st.text_input("🔎 검색어 수정 (선택한 키워드가 자동 입력됩니다)", value=st.session_state['keyword_input'], key="input_search_kw")
        if st.button("🛒 실시간 통합 최저가 사냥 시작", type="primary", key="btn_main_search") or st.session_state['run_search']:
            st.session_state['run_search'] = False
            if search_kw: 출력_통합_결과_레이아웃(search_kw)

# --- [Menu 3] 통합 최저가 검색 ---
elif 메뉴 == "🔎 통합 최저가 검색":
    st.markdown("<h1>🔎 통합 최저가 검색 (텍스트)</h1>", unsafe_allow_html=True)
    with st.container():
        st.caption("텍스트만 입력하여 네이버/도매꾹/11번가의 실시간 최저가를 10위까지 비교합니다.")
        text_kw = st.text_input("사냥할 상품명을 입력하세요", placeholder="예: 무선 가습기", key="input_text_kw")
        if st.button("🚀 왕의 명령: 실시간 통합 비교 시작", type="primary", use_container_width=True, key="btn_text_search"):
            if text_kw: 출력_통합_결과_레이아웃(text_kw)

# --- [Menu 4] 상품 등록 도우미 (마케팅 버전 디자인 유지) ---
elif 메뉴 == "🏪 상품 등록 도우미":
    st.markdown("<h1>🏪 AI 상세페이지 기획기 (Royal Copywriter)</h1>", unsafe_allow_html=True)
    with st.container():
        j_file = st.file_uploader("상품 사진 업로드", type=['jpg', 'jpeg', 'png'], key="j_up")
        if j_file:
            img_type = j_file.type # 🚀 [버그 수정 반영] PNG/JPG 자동 인식
            img_bytes = j_file.getvalue()
            col_j1, col_j2 = st.columns([1, 2])
            with col_j1:
                st.image(img_bytes, width=400)
            
            with col_j2:
                p_info = st.text_input("상품명 또는 핵심 강조 포인트 (선택사항)", placeholder="예: 무소음, 파스텔 핑크, 안전 인증 완료")
                c1, c2 = st.columns(2)
                target = c1.selectbox("타겟 고객", ["전체", "깐깐한 육아맘", "가성비 따지는 자취생", "트렌디한 2030 직장인", "건강을 챙기는 5060"])
                tone = c2.selectbox("글의 톤앤매너", ["감성을 자극하는 따뜻한 톤", "전문가 느낌의 신뢰감 있는 톤", "유머러스하고 친근한 톤", "결핍을 찌르는 강력한 톤"])

                if st.button("✨ 매혹적인 황금 상세페이지 생성", type="primary", use_container_width=True, key="btn_desc_gen"):
                    with st.spinner("왕실 카피라이터가 기획서를 작성 중입니다..."):
                        b64 = base64.b64encode(img_bytes).decode("utf-8")
                        prompt = f"""
                        (프롬프트 내용은 v5.5와 동일하게 유지)
                         당신은 매출을 10배 올려주는 10년 차 탑티어 이커머스 카피라이터입니다.
                         첨부된 상품 이미지를 철저히 분석하고, 아래의 조건에 맞춰 고객이 당장 사고 싶게 만드는 상세페이지 기획안을 작성해주세요.
                         [기본 조건] - 타겟 고객: {target} - 글의 톤앤매너: {tone} - 상품 핵심 키워드/특징: {p_info if p_info else "이미지 분석 내용을 바탕으로 창의적으로 도출"}
                        """
                        body = {
                            "max_tokens": 2000,
                            "messages": [{"role": "user", "content": [
                                {"type": "image", "source": {"type": "base64", "media_type": img_type, "data": b64}}, # 🚀 동적 형식 적용!
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
                rec = (buy_p + ship_p) / (1 - fee - 0.036 - (target_m/100))
                with f_cols[i]:
                    st.success(f"{name}")
                    st.metric("판매가", f"{int(rec):,}원")
                    st.write(f"예상마진: {int(rec * (target_m/100)):,}원")

elif 메뉴 == "📦 재고/가격 알림":
    st.markdown("<h1>📦 공급처 가격 및 재고 감시</h1>", unsafe_allow_html=True)
    
    # 보안상 개인정보는 마스킹 처리하여 출력 (캡처 방지)
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
                # 🚨 여기도 market=dome 추가 완료!
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
                    # 🚨 여기도 market=dome 추가 완료!
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

elif 메뉴 == "💎 블루오션 탐지":
    st.markdown("<h1>💎 블루오션 키워드 탐지기</h1>", unsafe_allow_html=True)
    with st.container():
        st.caption("키워드를 입력하면 네이버 전체 등록 상품수를 분석하여 경쟁 강도를 알려드립니다.")
        col_b1, col_b2 = st.columns([3, 1])
        kw = col_b1.text_input("분석할 사냥감(키워드) 입력", key="input_blue_kw")
        btn_ana = col_b2.button("실시간 시장 분석", type="primary", key="btn_blue_ana")
        
        if btn_ana:
            if kw:
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
                        st.error("🔴경쟁이 매우 치열한 레드오션입니다. 다른 키워드를 추천합니다.")
