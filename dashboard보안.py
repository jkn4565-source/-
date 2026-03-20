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
    st.error("🔑 API 키 로드 실패! Streamlit Cloud의 Secrets 설정을 확인해주세요.")
    st.stop()

# ==========================================
# 🎨 디자인 및 페이지 설정
# ==========================================
st.set_page_config(page_title="위탁배송 마스터", page_icon="🛒", layout="wide")

st.markdown("""
<style>
    .main { background-color: #FFFFFF; }
    [data-testid="stSidebar"] { background-color: #03C75A; }
    [data-testid="stSidebar"] * { color: white !important; }
    .stButton > button { background-color: #03C75A; color: white; border-radius: 4px; font-weight: bold; width: 100%; }
    [data-testid="metric-container"] { background-color: #F0FFF7; border: 1px solid #B3F0D4; border-radius: 8px; padding: 15px; }
    h1 { color: #03C75A !important; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🛰️ 데이터 수집용 함수 (핵심 로직)
# ==========================================
def 네이버검색(상품명, 개수=50):
    url = "https://openapi.naver.com/v1/search/shop.json"
    headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
    params = {"query": 상품명, "sort": "sim", "display": 개수}
    return requests.get(url, headers=headers, params=params).json()

def 도매꾹검색(검색어, 개수=20):
    url = "https://domeggook.com/ssl/api/"
    params = {"ver": "4.1", "mode": "getItemList", "aid": DOMEGGOOK_API_KEY, "om": "json", "kw": 검색어, "sz": 개수}
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
            results.append({
                "제목": item.findtext('ProductName', ''),
                "가격": int(item.findtext('SalePrice', '0').replace(',', '')),
                "링크": item.findtext('DetailPageUrl', ''),
                "출처": "11번가"
            })
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
# 📱 사이드바 메뉴 구성
# ==========================================
메뉴 = st.sidebar.radio("메뉴 선택", [
    "🏠 홈", "🔎 통합 최저가 검색", "🔍 가격 검색", "📸 이미지로 검색", 
    "📊 인기상품 분석", "🔥 트렌드 분석", "⚔️ 경쟁강도 확인", "💰 마진 계산기", "🛒 소싱 도우미"
])

# ==========================================
# 🚀 각 메뉴별 상세 실행 로직 (전체 포함)
# ==========================================

if 메뉴 == "🏠 홈":
    st.title("🛒 위탁배송 자동화 대시보드")
    st.caption(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')} 기준")
    st.divider()
    col1, col2, col3 = st.columns(3)
    col1.success("✅ 가격 수집 OK")
    col2.success("✅ 마진 계산 OK")
    col3.success("✅ 트렌드 분석 OK")
    st.info("왼쪽 사이드바에서 기능을 선택해 주세요!")

elif 메뉴 == "🔎 통합 최저가 검색":
    st.title("🔎 플랫폼 통합 최저가 검색")
    kw = st.text_input("상품명 입력")
    if kw and st.button("통합 검색"):
        n_res = 필터링(네이버검색(kw).get('items', []))
        d_res = 도매꾹검색(kw)
        e_res = 검색_11번가(kw)
        st.subheader("📊 플랫폼별 최저가 요약")
        c1, c2, c3 = st.columns(3)
        if n_res: c1.metric("네이버", f"{n_res[0]['가격']:,}원")
        if d_res: c2.metric("도매꾹", f"{int(d_res[0]['price']):,}원")
        if e_res: c3.metric("11번가", f"{e_res[0]['가격']:,}원")
        st.write("---")
        st.dataframe(pd.DataFrame(n_res + e_res))

elif 메뉴 == "🔍 가격 검색":
    st.title("🔍 네이버 가격 정밀 검색")
    kw = st.text_input("상품명")
    fee = st.number_input("기준 배송비", value=3000)
    if st.button("검색"):
        data, _ = 필터링(네이버검색(kw).get('items', []), fee)
        st.table(pd.DataFrame(data).head(10))

elif 메뉴 == "📸 이미지로 검색":
    st.title("📸 이미지 기반 상품 찾기")
    st.file_uploader("이미지를 업로드하세요")
    kw = st.text_input("이미지 속 상품 키워드를 입력하면 검색을 시작합니다.")
    if kw and st.button("검색 시작"):
        st.write(네이버검색(kw))

elif 메뉴 == "📊 인기상품 분석":
    st.title("📊 인기상품 가격 분포")
    kw = st.text_input("분석 키워드")
    if kw and st.button("분석"):
        items = 네이버검색(kw, 100).get('items', [])
        prices = [int(i['lprice']) for i in items if int(i['lprice']) > 100]
        if prices:
            st.bar_chart(pd.Series(prices).value_counts().head(20))
            st.metric("시장 평균가", f"{sum(prices)//len(prices):,}원")

elif 메뉴 == "🔥 트렌드 분석":
    st.title("🔥 네이버 쇼핑 카테고리 트렌드")
    if st.button("최신 트렌드 불러오기"):
        url = "https://openapi.naver.com/v1/datalab/shopping/categories"
        headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET, "Content-Type": "application/json"}
        body = {"startDate": "2024-01-01", "endDate": "2024-03-20", "timeUnit": "month", "category": [{"name": "패션", "param": ["50000000"]}]}
        res = requests.post(url, headers=headers, data=json.dumps(body)).json()
        st.write(res)

elif 메뉴 == "⚔️ 경쟁강도 확인":
    st.title("⚔️ 키워드 경쟁강도")
    kw = st.text_input("키워드")
    if kw and st.button("확인"):
        data = 네이버검색(kw)
        total = data.get('total', 0)
        st.metric("전체 상품 수", f"{total:,}개")
        if total < 5000: st.success("💎 블루오션입니다!")
        else: st.warning("🔥 경쟁이 치열합니다.")

elif 메뉴 == "💰 마진 계산기":
    st.title("💰 정밀 마진 계산기")
    col1, col2 = st.columns(2)
    buy = col1.number_input("매입가", value=10000)
    margin = col2.slider("목표 마진율(%)", 5, 50, 20)
    results = []
    for p, f in {"스토어": 0.06, "쿠팡": 0.11, "11번가": 0.13}.items():
        price = (buy + 3000) / (1 - f - (margin/100))