import streamlit as st
import requests
import pandas as pd
import json
import xml.etree.ElementTree as ET
import base64
import os
from datetime import datetime

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
    st.error(f"시크릿 키 설정 오류: {e}\n.streamlit/secrets.toml 파일을 확인해주세요.")
    st.stop()

# ==========================================
# 🎨 2. 디자인 및 CSS 설정
# ==========================================
st.set_page_config(page_title="위탁의왕", page_icon="👑", layout="wide")

st.markdown("""
<style>
    .main { background-color: #FFFFFF; }
    [data-testid="stSidebar"] { background-color: #03C75A; }
    [data-testid="stSidebar"] * { color: white !important; }
    .stButton > button { width: 100%; border-radius: 5px; font-weight: bold; background-color: #03C75A; color: white; }
    .stButton > button:hover { background-color: #02A84A; color: white; }
    .result-card { border: 1px solid #eee; padding: 15px; border-radius: 10px; background-color: #fcfcfc; margin-bottom: 10px; }
    h1 { color: #03C75A !important; }
    h2, h3 { color: #333 !important; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🔐 3. 세션 상태 관리 (기억 보관소)
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
    params = {"ver": "4.1", "mode": "getItemList", "aid": DOMEGGOOK_API_KEY, "om": "json", "kw": 검색어, "sz": 개수}
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
        for (name, data), col in zip([("🟢 네이버", n_list), ("🔵 도매꾹", d_list), ("🔴 11번가", e_list)], [c1, c2, c3]):
            with col:
                st.subheader(name)
                if data:
                    best = data[0]
                    st.image(best['이미지'], use_container_width=True)
                    st.metric("최저가", f"{best['총가격']:,}원")
                    st.write(f"**{best['제목'][:35]}**")
                    st.link_button("상품 바로가기", best['링크'])
                else: st.error("결과 없음")

        combined = sorted(n_list[:10] + d_list[:10] + e_list[:10], key=lambda x: x['총가격'])
        if combined:
            st.divider()
            st.subheader("🏆 전체 통합 최저가 순위 TOP 10 (배송비 포함)")
            for i, item in enumerate(combined[:10], 1):
                with st.container():
                    col_img, col_txt, col_btn = st.columns([1, 4, 1.5])
                    with col_img: st.image(item['이미지'], width=100)
                    with col_txt:
                        st.write(f"**{i}. {item['출처']}** | {item['제목'][:65]}")
                        st.write(f"💰 {item['총가격']:,}원")
                    with col_btn: st.link_button("구매하러 가기", item['링크'])

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    params = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}
    try: requests.post(url, params=params)
    except: pass

# ==========================================
# 🖥️ 5. 사이드바 메뉴 
# ==========================================
st.sidebar.title("👑 위탁의왕")
메뉴 = st.sidebar.radio("메뉴 선택", [
    "🏠 홈", "📸 이미지로 검색", "🔎 통합 최저가 검색", "🏪 상품 등록 도우미", 
    "💰 마진 계산기", "📦 재고/가격 알림", "💎 블루오션 탐지"
])

# --- [Menu 1] 홈 ---
if 메뉴 == "🏠 홈":
    st.title("👑 위탁의왕 자동화 대시보드 v5.6")
    st.caption(f"📅 오늘 날짜: {datetime.now().strftime('%Y-%m-%d')}")
    st.divider()
    col1, col2, col3 = st.columns(3)
    col1.metric("업무 모드", "매출 폭발 모드 🚀")
    col2.metric("이미지 처리", "JPG/PNG 완벽 호환")
    col3.metric("최저가 랭킹", "TOP 10 지원")
    st.info("왼쪽 메뉴를 선택하세요. PNG 파일 에러가 완벽하게 수정되었습니다!")

# --- [Menu 2] 이미지로 검색 ---
elif 메뉴 == "📸 이미지로 검색":
    st.title("📸 AI 이미지 최저가 검색")
    up_file = st.file_uploader("상품 사진 업로드", type=['jpg', 'jpeg', 'png'], key="img_search_up")
    
    if up_file:
        img_type = up_file.type # 🚀 [버그 수정] 업로드된 파일의 진짜 형식을 추출! (image/png 등)
        img_bytes = up_file.getvalue()
        st.image(img_bytes, width=300)
        
        if st.button("🔍 AI 키워드 5개 추출"):
            with st.spinner("이미지 정밀 분석 중..."):
                b64 = base64.b64encode(img_bytes).decode("utf-8")
                body = {
                    "max_tokens": 300,
                    "messages": [{"role": "user", "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": img_type, "data": b64}}, # 🚀 동적 형식 적용!
                        {"type": "text", "text": "한국 쇼핑몰 검색용 핵심 키워드 5개를 콤마로만 답변하세요."}
                    ]}]
                }
                res = call_claude_api(body)
                if res:
                    st.session_state['keywords_list'] = [k.strip() for k in res.split(',')]
                    st.rerun()

    if st.session_state['keywords_list']:
        st.write("▼ 키워드를 선택하세요.")
        cols = st.columns(len(st.session_state['keywords_list']))
        for i, kw in enumerate(st.session_state['keywords_list']):
            if cols[i].button(kw, key=f"kw_{i}"):
                st.session_state['keyword_input'] = kw
                st.session_state['run_search'] = True
                st.rerun()

    st.divider()
    search_kw = st.text_input("🔎 검색어 수정", value=st.session_state['keyword_input'])
    if st.button("🛒 통합 최저가 검색 시작") or st.session_state['run_search']:
        st.session_state['run_search'] = False
        if search_kw: 출력_통합_결과_레이아웃(search_kw)

# --- [Menu 3] 통합 최저가 검색 ---
elif 메뉴 == "🔎 통합 최저가 검색":
    st.title("🔎 통합 최저가 검색 (텍스트)")
    text_kw = st.text_input("상품명을 입력하세요", placeholder="예: 무선 가습기")
    if st.button("🚀 실시간 통합 비교", type="primary"):
        if text_kw: 출력_통합_결과_레이아웃(text_kw)

# --- [Menu 4] 상품 등록 도우미 (🔥 마케팅 특화 버전) ---
elif 메뉴 == "🏪 상품 등록 도우미":
    st.title("🏪 AI 상세페이지 기획기 (고급 마케터 버전)")
    st.caption("단순한 설명을 넘어, 고객의 지갑을 열게 만드는 매혹적인 스토리텔링 상세페이지를 만듭니다.")
    
    j_file = st.file_uploader("상품 사진 업로드", type=['jpg', 'jpeg', 'png'], key="j_up")
    if j_file:
        img_type = j_file.type # 🚀 [버그 수정] 여기서도 파일의 진짜 형식을 추출!
        img_bytes = j_file.getvalue()
        st.image(img_bytes, width=400)
        
        p_info = st.text_input("상품명 또는 핵심 강조 포인트 (선택사항)", placeholder="예: 무소음, 파스텔 핑크, 안전 인증 완료")
        
        c1, c2 = st.columns(2)
        target = c1.selectbox("타겟 고객", ["전체", "깐깐한 육아맘", "가성비 따지는 자취생", "트렌디한 2030 직장인", "건강을 챙기는 5060"])
        tone = c2.selectbox("글의 톤앤매너", ["감성을 자극하는 따뜻한 톤", "전문가 느낌의 신뢰감 있는 톤", "유머러스하고 친근한 톤", "결핍을 찌르는 강력한 톤"])

        if st.button("✨ 매혹적인 상세페이지 생성", type="primary", use_container_width=True):
            with st.spinner("매출을 10배 올려주는 탑티어 카피라이터가 기획서를 작성 중입니다..."):
                b64 = base64.b64encode(img_bytes).decode("utf-8")
                
                prompt = f"""
                당신은 매출을 10배 올려주는 10년 차 탑티어 이커머스 카피라이터입니다.
                첨부된 상품 이미지를 철저히 분석하고, 아래의 조건에 맞춰 고객이 당장 사고 싶게 만드는 상세페이지 기획안을 작성해주세요.

                [기본 조건]
                - 타겟 고객: {target}
                - 글의 톤앤매너: {tone}
                - 상품 핵심 키워드/특징: {p_info if p_info else "이미지 분석 내용을 바탕으로 창의적으로 도출"}

                [상세페이지 구성 필수 요건]
                1. 🧲 강력한 훅(Hook) 헤드라인: 타겟 고객의 가장 큰 고민이나 결핍을 건드리며 시선을 사로잡는 한 줄.
                2. 🥺 공감대 형성 (Pain Point): "그동안 OO하시느라 힘드셨죠?" 등 타겟의 일상 속 불편함을 섬세하게 짚어주기.
                3. 💡 명쾌한 해결책 (Solution): 이 상품이 어떻게 그 문제를 우아하고 확실하게 해결해주는지 이미지의 특징을 바탕으로 설명.
                4. ✨ 3가지 핵심 매력 포인트: 기능(Feature)이 아닌 고객이 얻는 가치와 혜택(Benefit) 중심으로 변환하여 강조.
                5. 🎁 감성적인 클로징 & 구매 유도: 이 상품과 함께할 때 달라질 기분 좋은 일상을 상상하게 만들며 구매 버튼을 누르게 하는 매끄러운 마무리.
                6. 🏷️ 추천 노출 해시태그 7개

                * 가독성을 위해 마크다운(Markdown) 문법과 찰떡같이 어울리는 이모지를 적극적으로 활용해주세요.
                * 딱딱한 제품 설명서가 절대 아닙니다. 친한 지인이 강력 추천하거나 전문 큐레이터가 소개하는 듯한 섬세하고 매력적인 글로 작성해주세요.
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
        st.subheader("📊 생성된 상세페이지 기획안")
        st.markdown(st.session_state['helper_generated_text'])
        st.divider()
        st.subheader("📋 전체 텍스트 복사하기")
        st.text_area("Ctrl+A로 전체 선택 후 쇼핑몰 에디터에 붙여넣으세요.", value=st.session_state['helper_generated_text'], height=400)

# --- [Menu 5] 마진 계산기 ---
elif 메뉴 == "💰 마진 계산기":
    st.title("💰 마진 계산기")
    col1, col2 = st.columns(2)
    buy_p = col1.number_input("도매가(매입가)", value=10000)
    ship_p = col1.number_input("매입 배송비", value=3000)
    target_m = col2.number_input("목표 마진율 (%)", value=30)
    if st.button("🎯 추천 판매가 계산"):
        fees = {"스마트스토어(6%)": 0.06, "쿠팡(11%)": 0.11, "11번가(13%)": 0.13}
        for name, fee in fees.items():
            rec = (buy_p + ship_p) / (1 - fee - 0.036 - (target_m/100))
            st.success(f"{name} 추천가: {int(rec):,}원")

# --- [Menu 6] 재고/가격 알림 ---
elif 메뉴 == "📦 재고/가격 알림":
    st.title("📦 가격 및 재고 감시")
    재고파일 = "재고모니터링.json"
    def 로드(): return json.load(open(재고파일, 'r', encoding='utf-8')) if os.path.exists(재고파일) else []
    def 저장(d): json.dump(d, open(재고파일, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

    목록 = 로드()
    with st.expander("➕ 감시 상품 추가"):
        c1, c2 = st.columns([2, 1])
        n_no = c1.text_input("도매꾹 상품번호")
        n_name = c2.text_input("관리 이름")
        if st.button("등록"):
            p = {"ver": "4.1", "aid": DOMEGGOOK_API_KEY, "om": "json", "mode": "getItemList", "itemNo": n_no}
            item = requests.get("https://domeggook.com/ssl/api/", params=p).json()['domeggook']['list']['item']
            item = item[0] if isinstance(item, list) else item
            if item:
                목록.append({"no": n_no, "name": n_name, "price": int(item['price']), "상태": "판매중"})
                저장(목록)
                st.rerun()

    if st.button("🔄 전수 점검 및 가격체크"):
        for i, s in enumerate(목록):
            p = {"ver": "4.1", "aid": DOMEGGOOK_API_KEY, "om": "json", "mode": "getItemList", "itemNo": s['no']}
            res = requests.get("https://domeggook.com/ssl/api/", params=p).json()['domeggook']['list']['item']
            res = res[0] if isinstance(res, list) else res
            if res:
                now_p = int(res['price'])
                if now_p > s['price']:
                    send_telegram(f"🔺 <b>가격인상!</b>\n{s['name']}\n{s['price']:,}원 ➔ {now_p:,}원")
                목록[i]['price'] = now_p
                목록[i]['상태'] = "판매중"
            else:
                send_telegram(f"🚫 <b>품절!</b>\n{s['name']}")
                목록[i]['상태'] = "품절"
        저장(목록)
        st.rerun()
    
    for idx, s in enumerate(목록):
        st.write(f"{s['name']} | {s['price']:,}원 | {s['상태']}")
        if st.button(f"삭제 {idx}", key=f"d_{idx}"):
            목록.pop(idx)
            저장(목록)
            st.rerun()

# --- [Menu 7] 블루오션 탐지 ---
elif 메뉴 == "💎 블루오션 탐지":
    st.title("💎 블루오션 분석")
    kw = st.text_input("분석할 키워드")
    if st.button("시장 분석"):
        total = 네이버검색(kw).get('total', 0)
        st.metric("상품수", f"{total:,}개")
        if total < 2000: st.success("💎 블루오션")
        else: st.error("🔴 경쟁 치열")