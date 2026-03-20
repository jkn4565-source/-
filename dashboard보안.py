import streamlit as st
import requests
import pandas as pd
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

# ==========================================
# 🔐 보안 설정 (Secrets 관리)
# ==========================================
try:
    NAVER_CLIENT_ID = st.secrets["NAVER_CLIENT_ID"]
    NAVER_CLIENT_SECRET = st.secrets["NAVER_CLIENT_SECRET"]
    DOMEGGOOK_API_KEY = st.secrets["DOMEGGOOK_API_KEY"]
    ELEVENST_API_KEY = st.secrets["ELEVENST_API_KEY"]
except Exception as e:
    st.error(f"🔑 API 키 로드 실패! .streamlit/secrets.toml 파일을 확인하세요. 에러: {e}")
    st.stop()

# ==========================================
# 🎨 UI/디자인 설정
# ==========================================
st.set_page_config(page_title="위탁배송 마스터 대시보드", page_icon="🛒", layout="wide")

st.markdown("""
<style>
    .main { background-color: #FFFFFF; }
    [data-testid="stSidebar"] { background-color: #03C75A; }
    [data-testid="stSidebar"] * { color: white !important; }
    .stButton > button { background-color: #03C75A; color: white; border-radius: 4px; font-weight: bold; width: 100%; }
    [data-testid="metric-container"] { background-color: #F0FFF7; border: 1px solid #B3F0D4; border-radius: 8px; padding: 15px; }
    h1 { color: #03C75A !important; }
    .stTable { border: 1px solid #eee; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🛰️ 데이터 수집 및 유틸리티 함수
# ==========================================
def 네이버검색(상품명, 개수=50):
    url = "https://openapi.naver.com/v1/search/shop.json"
    headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
    params = {"query": 상품명, "sort": "sim", "display": 개수}
    return requests.get(url, headers=headers, params=params).json()

def 도매꾹검색(검색어, 개수=20):
    url = "https://domeggook.com/ssl/api/"
    params = {"ver": "4.1", "mode": "getItemList", "aid": DOMEGGOOK_API_KEY, "market": "dome", "om": "json", "kw": 검색어, "sz": 개수}
    try:
        data = requests.get(url, params=params).json()
        items = data['domeggook']['list']['item']
        return [items] if isinstance(items, dict) else items
    except: return []

def 검색_11번가(검색어, 개수=20):
    url = "http://openapi.11st.co.kr/openapi/OpenApiService.tmall"
    params = {"key": ELEVENST_API_KEY, "apiCode": "ProductSearch", "keyword": 검색어, "pageSize": 개수}
    try:
        res = requests.get(url, params=params)
        root = ET.fromstring(res.content.decode('euc-kr', errors='ignore'))
        results = []
        for item in root.findall('.//Product'):
            price = int(item.findtext('SalePrice', '0').replace(',', ''))
            results.append({"제목": item.findtext('ProductName', ''), "가격": price, "링크": item.findtext('DetailPageUrl', ''), "출처": "11번가"})
        return results
    except: return []

def 필터링(items, 배송비=0):
    상품목록, 해외키워드 = [], ['직구', '해외', '구매대행', 'USA', '중국', '헤외', '면세']
    for item in items:
        가격 = int(item['lprice'])
        제목 = item['title'].replace('<b>', '').replace('</b>', '')
        if 가격 <= 100 or any(k in 제목 or k in item['mallName'] for k in 해외키워드): continue
        상품목록.append({"제목": 제목, "가격": 가격, "배송비": 배송비, "총가격": 가격 + 배송비, "쇼핑몰": item['mallName'], "링크": item['link'], "출처": "네이버"})
    return 상품목록

# ==========================================
# 📱 사이드바 메뉴
# ==========================================
메뉴 = st.sidebar.radio("메뉴 선택", ["🏠 홈", "🔎 통합 최저가 검색", "🔍 가격 검색", "📊 인기상품 분석", "🔥 트렌드 분석", "⚔️ 경쟁강도 확인", "💰 마진 계산기", "🛒 소싱 도우미"])

# --- [🏠 홈] ---
if 메뉴 == "🏠 홈":
    st.title("🛒 위탁배송 자동화 컨트롤 타워")
    st.markdown("### 사장님의 성공적인 위탁판매를 돕는 AI 비서입니다.")
    st.divider()
    c1, c2, c3 = st.columns(3)
    c1.metric("API 상태", "정상 가동")
    c2.metric("보안 모드", "ON (Secrets 적용)")
    c3.metric("최종 업데이트", datetime.now().strftime("%H:%M"))
    st.info("왼쪽 메뉴를 선택하여 분석을 시작하세요!")

# --- [🔎 통합 최저가 검색] ---
elif 메뉴 == "🔎 통합 최저가 검색":
    st.title("🔎 플랫폼 통합 최저가 비교")
    kw = st.text_input("검색어 입력")
    if st.button("실시간 비교 시작"):
        with st.spinner("데이터 수집 중..."):
            n_res = 필터링(네이버검색(kw).get('items', []))
            d_res = 도매꾹검색(kw)
            e_res = 검색_11번가(kw)
            
            c1, c2, c3 = st.columns(3)
            if n_res: c1.metric("네이버 최저가", f"{sorted(n_res, key=lambda x:x['가격'])[0]['가격']:,}원")
            if d_res: c2.metric("도매꾹 최저가", f"{int(d_res[0]['price']):,}원")
            if e_res: c3.metric("11번가 최저가", f"{sorted(e_res, key=lambda x:x['가격'])[0]['가격']:,}원")
            
            st.divider()
            st.subheader("🏆 전체 상품 리스트 (최저가순)")
            all_data = n_res + e_res # 도매꾹 데이터도 가공하여 합칠 수 있음
            st.dataframe(pd.DataFrame(all_data).sort_values('가격'))

# --- [📊 인기상품 분석] ---
elif 메뉴 == "📊 인기상품 분석":
    st.title("📊 가격 분포 및 인기 분석")
    kw = st.text_input("분석할 키워드")
    if st.button("시장 분석"):
        res = 필터링(네이버검색(kw, 100).get('items', []))
        if res:
            prices = [item['가격'] for item in res]
            df = pd.DataFrame(prices, columns=['가격'])
            st.subheader("💰 가격 분포 그래프")
            st.bar_chart(df.value_counts().sort_index())
            st.metric("평균 시장가", f"{sum(prices)//len(prices):,}원")

# --- [⚔️ 경쟁강도 확인] ---
elif 메뉴 == "⚔️ 경쟁강도 확인":
    st.title("⚔️ 키워드 경쟁강도 분석")
    kw = st.text_input("키워드 입력")
    if st.button("경쟁도 측정"):
        data = 네이버검색(kw)
        total = data.get('total', 0)
        st.metric("전체 상품 수", f"{total:,}개")
        if total > 100000: st.error("🔴 매우 치열 (진입 주의)")
        elif total > 10000: st.warning("🟡 보통 (차별화 필요)")
        else: st.success("🟢 블루오션 (적극 추천)")

# --- [💰 마진 계산기] ---
elif 메뉴 == "💰 마진 계산기":
    st.title("💰 플랫폼별 정밀 마진 계산")
    c1, c2, c3 = st.columns(3)
    buy = c1.number_input("매입가", value=10000)
    ship = c2.number_input("배송비", value=3000)
    margin_goal = c3.slider("목표 마진율(%)", 5, 50, 20)
    
    st.latex(r"Profit = SalePrice - (BuyPrice + Shipping) - (Fees \times SalePrice)")
    
    fees = {"스마트스토어": 0.055, "쿠팡": 0.108, "11번가": 0.13, "G마켓": 0.12}
    results = []
    for p, f in fees.items():
        # 마진율 공식 적용: 판매가 = (매입가+배송비) / (1 - 수수료 - 마진율)
        target = (buy + ship) / (1 - f - (margin_goal/100))
        results.append({"플랫폼": p, "수수료": f"{f*100}%", "권장판매가": f"{int(target):,}원"})
    st.table(pd.DataFrame(results))

# --- [🛒 소싱 도우미] ---
elif 메뉴 == "🛒 소싱 도우미":
    st.title("🛒 계절별 황금 소싱 리스트")
    month = datetime.now().month
    seasons = {3:"봄", 4:"봄", 5:"봄", 6:"여름", 7:"여름", 8:"여름", 9:"가을", 10:"가을", 11:"가을", 12:"겨울", 1:"겨울", 2:"겨울"}
    items = {"봄":["나들이용품", "캠핑의자", "미세먼지마스크"], "여름":["휴대용선풍기", "물놀이용품", "제습기"], "가을":["가습기", "등산용품", "무릎담요"], "겨울":["전기장판", "핫팩", "방한장갑"]}
    
    st.subheader(f"📅 지금은 {seasons[month]} 시즌입니다.")
    for item in items[seasons[month]]:
        st.info(f"👉 추천 키워드: {item}")