import streamlit as st
import requests
import pandas as pd
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

NAVER_CLIENT_ID = "NmoPGi9LLT1pbGFRCQ45"
NAVER_CLIENT_SECRET = "Z60X30C0Li"
DOMEGGOOK_API_KEY = "92b80f385760c74d150e84292746cfd7"
ELEVENST_API_KEY = "2d88124f88de34180fd7a6f3e1736988"

st.set_page_config(page_title="위탁배송 대시보드", page_icon="🛒", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .main { background-color: #FFFFFF; }
    [data-testid="stSidebar"] { background-color: #03C75A; }
    [data-testid="stSidebar"] * { color: white !important; }
    .stButton > button {
        background-color: #03C75A; color: white;
        border: none; border-radius: 4px;
        font-weight: bold; padding: 8px 20px;
    }
    .stButton > button:hover { background-color: #02A84A; color: white; }
    [data-testid="metric-container"] {
        background-color: #F0FFF7;
        border: 1px solid #B3F0D4;
        border-radius: 8px; padding: 15px;
    }
    h1 { color: #03C75A !important; }
    h2, h3 { color: #222222 !important; }
    hr { border-color: #03C75A; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

def 네이버검색(상품명, 개수=50):
    url = "https://openapi.naver.com/v1/search/shop.json"
    headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
    params = {"query": 상품명, "sort": "sim", "display": 개수}
    return requests.get(url, headers=headers, params=params).json()

def 필터링(items, 배송비=0):
    상품목록 = []
    제외목록 = []
    해외키워드 = ['직구', '해외', '구매대행', 'USA', '중국', '헤외', '면세']
    for item in items:
        가격 = int(item['lprice'])
        제목 = item['title'].replace('<b>', '').replace('</b>', '')
        쇼핑몰 = item['mallName']
        if 가격 <= 100:
            continue
        if any(k in 제목 or k in 쇼핑몰 for k in 해외키워드):
            제외목록.append(제목)
            continue

        # 쇼핑몰별 아이콘
        if 'G마켓' in 쇼핑몰 or 'Gmarket' in 쇼핑몰:
            출처 = "G마켓"
        elif '옥션' in 쇼핑몰 or 'Auction' in 쇼핑몰:
            출처 = "옥션"
        elif '쿠팡' in 쇼핑몰 or 'Coupang' in 쇼핑몰:
            출처 = "쿠팡"
        elif '11번가' in 쇼핑몰:
            출처 = "11번가"
        elif '스마트스토어' in 쇼핑몰 or '네이버' in 쇼핑몰:
            출처 = "스마트스토어"
        elif '위메프' in 쇼핑몰:
            출처 = "위메프"
        elif '티몬' in 쇼핑몰:
            출처 = "티몬"
        else:
            출처 = 쇼핑몰

        상품목록.append({
            "제목": 제목,
            "가격": 가격,
            "배송비": 배송비,
            "총가격": 가격 + 배송비,
            "쇼핑몰": 쇼핑몰,
            "출처": 출처,
            "링크": item['link']
        })

    가격목록 = [s['가격'] for s in 상품목록]
    if 가격목록:
        평균가 = sum(가격목록) // len(가격목록)
        상품목록 = [s for s in 상품목록 if s['가격'] >= 평균가 * 0.05]
    return 상품목록, 제외목록

def 도매꾹검색(검색어, 개수=20):
    url = "https://domeggook.com/ssl/api/"
    params = {
        "ver": "4.1", "mode": "getItemList", "aid": DOMEGGOOK_API_KEY,
        "market": "dome", "om": "json", "kw": 검색어,
        "sz": 개수, "pg": 1, "so": "aa", "dfos": "false"
    }
    try:
        data = requests.get(url, params=params).json()
        items = data['domeggook']['list']['item']
        if isinstance(items, dict):
            items = [items]
        결과 = []
        for item in items:
            가격 = int(item.get('price', 0))
            배송구분 = item.get('deli', {}).get('who', '')
            배송비 = int(item.get('deli', {}).get('fee', 0) or 0)
            if 배송구분 == 'S':
                배송비 = 0
            결과.append({
                "제목": item.get('title', ''),
                "가격": 가격, "배송비": 배송비,
                "총가격": 가격 + 배송비,
                "쇼핑몰": item.get('nick', item.get('id', '')),
                "최소수량": item.get('unitQty', 1),
                "링크": item.get('url', ''),
                "출처": "도매꾹"
            })
        return sorted(결과, key=lambda x: x['총가격'])
    except:
        return []

def 검색_11번가(검색어, 개수=20):
    url = "http://openapi.11st.co.kr/openapi/OpenApiService.tmall"
    params = {
        "key": ELEVENST_API_KEY, "apiCode": "ProductSearch",
        "keyword": 검색어, "pageSize": 개수, "pageNum": 1, "sortCd": "20",
    }
    try:
        response = requests.get(url, params=params)
        content = response.content.decode('euc-kr', errors='ignore')
        root = ET.fromstring(content)
        상품목록 = []
        for item in root.findall('.//Product'):
            제목 = item.findtext('ProductName', '')
            가격 = item.findtext('SalePrice', '0') or item.findtext('Price', '0')
            배송비텍스트 = item.findtext('DeliveryFee', '0')
            링크 = item.findtext('DetailPageUrl', '')
            try:
                가격 = int(str(가격).replace(',', '').strip())
                배송비 = int(str(배송비텍스트).replace(',', '').strip()) if 배송비텍스트 else 0
            except:
                continue
            if 가격 <= 0:
                continue
            상품목록.append({
                "제목": 제목, "가격": 가격, "배송비": 배송비,
                "총가격": 가격 + 배송비, "쇼핑몰": "11번가",
                "링크": 링크, "출처": "11번가"
            })
        return sorted(상품목록, key=lambda x: x['총가격'])
    except:
        return []

카테고리맵 = {
    "패션의류": "50000000", "패션잡화": "50000001",
    "디지털/가전": "50000003", "출산/육아": "50000004",
    "식품": "50000006", "화장품/미용": "50000008",
    "가구/인테리어": "50000010",
}

묶음맵 = {
    "묶음1: 패션의류 · 디지털/가전 · 출산/육아": [
        {"name": "패션의류", "param": ["50000000"]},
        {"name": "디지털/가전", "param": ["50000003"]},
        {"name": "출산/육아", "param": ["50000004"]},
    ],
    "묶음2: 패션잡화 · 화장품/미용 · 식품": [
        {"name": "패션잡화", "param": ["50000001"]},
        {"name": "화장품/미용", "param": ["50000008"]},
        {"name": "식품", "param": ["50000006"]},
    ],
    "묶음3: 스포츠/레저 · 가구/인테리어 · 출산/육아": [
        {"name": "스포츠/레저", "param": ["50000007"]},
        {"name": "가구/인테리어", "param": ["50000010"]},
        {"name": "출산/육아", "param": ["50000004"]},
    ],
    "직접 선택": []
}

계절상품맵 = {
    "봄 (3~5월)": ["봄자켓", "나들이용품", "캠핑의자", "돗자리", "미세먼지마스크"],
    "여름 (6~8월)": ["수영복", "물놀이용품", "선크림", "아이스팩", "휴대용선풍기"],
    "가을 (9~11월)": ["아웃도어자켓", "핫팩", "보온도시락", "등산스틱"],
    "겨울 (12~2월)": ["방한용품", "전기장판", "내복", "핫팩", "가습기"]
}

st.sidebar.title("🛒 위탁배송 대시보드")
메뉴 = st.sidebar.radio("메뉴 선택", [
    "🏠 홈",
    "🔎 통합 최저가 검색",
    "📸 이미지로 검색",
    "🔍 가격 검색",
    "📊 인기상품 분석",
    "🔥 트렌드 분석",
    "🏷️ 키워드 트렌드 분석",
    "⚔️ 경쟁강도 확인",
    "💰 마진 계산기",
    "🛒 소싱 도우미",
    "📒 수익 관리 장부",
    "📦 재고/품절 알림",
    "🏪 상품 등록 도우미",
    "💎 블루오션 탐지"
])

if 메뉴 == "🏠 홈":
    st.title("🛒 위탁배송 자동화 대시보드")
    st.caption(f"📅 {datetime.now().strftime('%Y년 %m월 %d일 %H시 %M분')} 기준")
    st.divider()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.success("✅ 가격 수집\n최저가·평균가 자동 수집")
    with col2:
        st.success("✅ 필터링\n해외배송·미끼상품 제외")
    with col3:
        st.success("✅ 트렌드\n네이버 인기검색어 분석")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.success("✅ 경쟁강도\n블루오션 상품 탐색")
    with col2:
        st.success("✅ 마진계산\n플랫폼별 최소 판매가")
    with col3:
        st.success("✅ 소싱도우미\n마진 좋은 상품 자동 탐색")
    st.divider()
    st.info("왼쪽 메뉴에서 원하는 기능을 선택하세요!")

elif 메뉴 == "🔎 통합 최저가 검색":
    st.title("🔎 통합 최저가 검색")
    st.caption("네이버 · 도매꾹 · 11번가 동시 비교!")
    상품명 = st.text_input("검색할 상품명", placeholder="예: 미키식판, 무선이어폰")
    if st.button("통합 검색하기", type="primary"):
        if 상품명:
            col1, col2, col3 = st.columns(3)
            with col1:
                with st.spinner("네이버 검색 중..."):
                    data = 네이버검색(상품명)
                    naver결과, _ = 필터링(data.get('items', []))
                    if naver결과:
                        정렬 = sorted(naver결과, key=lambda x: x['총가격'])
                        st.success("✅ 네이버")
                        st.metric("최저가", f"{정렬[0]['총가격']:,}원")
                        st.write(f"**{정렬[0]['제목'][:25]}**")
                        st.write(f"{정렬[0]['가격']:,}원 | 배송비 {정렬[0].get('배송비',0):,}원")
                        st.link_button("구매링크", 정렬[0]['링크'])
                    else:
                        st.error("네이버 결과 없음")
            with col2:
                with st.spinner("도매꾹 검색 중..."):
                    dome결과 = 도매꾹검색(상품명)
                    if dome결과:
                        st.success("✅ 도매꾹")
                        st.metric("최저가", f"{dome결과[0]['총가격']:,}원")
                        st.write(f"**{dome결과[0]['제목'][:25]}**")
                        st.write(f"{dome결과[0]['가격']:,}원 | 배송비 {dome결과[0]['배송비']:,}원")
                        st.write(f"최소수량: {dome결과[0]['최소수량']}개")
                        st.link_button("구매링크", dome결과[0]['링크'])
                    else:
                        st.error("도매꾹 결과 없음")
            with col3:
                with st.spinner("11번가 검색 중..."):
                    eleven결과 = 검색_11번가(상품명)
                    if eleven결과:
                        st.success("✅ 11번가")
                        st.metric("최저가", f"{eleven결과[0]['총가격']:,}원")
                        st.write(f"**{eleven결과[0]['제목'][:25]}**")
                        st.write(f"{eleven결과[0]['가격']:,}원 | 배송비 {eleven결과[0]['배송비']:,}원")
                        st.link_button("구매링크", eleven결과[0]['링크'])
                    else:
                        st.error("11번가 결과 없음")
            st.divider()
            st.subheader("🏆 전체 통합 최저가 순위 TOP 10")
            전체목록 = []
            if naver결과:
                전체목록 += sorted(naver결과, key=lambda x: x['총가격'])[:5]
            if dome결과:
                전체목록 += dome결과[:5]
            if eleven결과:
                전체목록 += eleven결과[:5]
            전체정렬 = sorted(전체목록, key=lambda x: x['총가격'])[:10]
            for i, s in enumerate(전체정렬, 1):
                출처색 = "🟢" if s['출처'] == "네이버" else "🔵" if s['출처'] == "도매꾹" else "🔴"
                c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
                c1.write(f"**{i}. {출처색} [{s['출처']}] {s['제목'][:30]}**")
                c2.write(f"{s['가격']:,}원")
                c3.write(f"총 {s['총가격']:,}원")
                c4.link_button("구매", s['링크'])
    
elif 메뉴 == "📸 이미지로 검색":
    st.title("📸 이미지로 최저가 검색")
    st.caption("상품 이미지를 올리면 자동으로 최저가를 찾아드려요!")
    업로드파일 = st.file_uploader("상품 이미지 업로드", type=['jpg', 'jpeg', 'png', 'webp'])
    if 업로드파일:
        st.image(업로드파일, width=300, caption="업로드된 이미지")
        st.divider()
        st.info("💡 이미지를 보고 검색어를 직접 입력해주세요!")
        검색어 = st.text_input("상품명 입력", placeholder="예: 미키마우스 실리콘 식판")
        if st.button("이미지 상품 검색하기", type="primary"):
            if 검색어:
                col1, col2, col3 = st.columns(3)
                with col1:
                    with st.spinner("네이버 검색 중..."):
                        data = 네이버검색(검색어)
                        naver결과, _ = 필터링(data.get('items', []))
                        if naver결과:
                            정렬 = sorted(naver결과, key=lambda x: x['총가격'])
                            st.success("✅ 네이버")
                            st.metric("최저가", f"{정렬[0]['총가격']:,}원")
                            st.write(f"**{정렬[0]['제목'][:25]}**")
                            st.link_button("구매링크", 정렬[0]['링크'])
                with col2:
                    with st.spinner("도매꾹 검색 중..."):
                        dome결과 = 도매꾹검색(검색어)
                        if dome결과:
                            st.success("✅ 도매꾹")
                            st.metric("최저가", f"{dome결과[0]['총가격']:,}원")
                            st.write(f"**{dome결과[0]['제목'][:25]}**")
                            st.link_button("구매링크", dome결과[0]['링크'])
                with col3:
                    with st.spinner("11번가 검색 중..."):
                        eleven결과 = 검색_11번가(검색어)
                        if eleven결과:
                            st.success("✅ 11번가")
                            st.metric("최저가", f"{eleven결과[0]['총가격']:,}원")
                            st.write(f"**{eleven결과[0]['제목'][:25]}**")
                            st.link_button("구매링크", eleven결과[0]['링크'])
    st.divider()
    st.info("🤖 Claude API 크레딧 충전 후 AI가 이미지를 자동으로 분석해서 검색어를 찾아드릴 수 있어요!")

elif 메뉴 == "🔍 가격 검색":
    st.title("🔍 상품 가격 검색")
    col1, col2 = st.columns([3, 1])
    with col1:
        상품명 = st.text_input("검색할 상품명", placeholder="예: 에어팟, 바람막이")
    with col2:
        배송비 = st.number_input("배송비", min_value=0, value=3000, step=500)
    if st.button("검색하기", type="primary"):
        if 상품명:
            with st.spinner("검색 중..."):
                data = 네이버검색(상품명)
                상품목록, 제외목록 = 필터링(data.get('items', []), 배송비)
                if 상품목록:
                    최종가격 = [s['총가격'] for s in 상품목록]
                    c1, c2, c3 = st.columns(3)
                    c1.metric("최저가 (배송비포함)", f"{min(최종가격):,}원")
                    c2.metric("평균가 (배송비포함)", f"{sum(최종가격)//len(최종가격):,}원")
                    c3.metric("정상 상품 수", f"{len(상품목록)}개")
                    st.divider()
                    st.subheader("🏆 추천 상품 TOP 10")
                    정렬상품 = sorted(상품목록, key=lambda x: x['총가격'])[:10]
                    for i, s in enumerate(정렬상품, 1):
                        c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
                        c1.write(f"**{i}. {s['제목'][:35]}**")
                        c2.write(f"{s['가격']:,}원")
                        c3.write(f"총 {s['총가격']:,}원")
                        c4.link_button("구매링크", s['링크'])
                else:
                    st.error("조건에 맞는 상품이 없습니다.")

elif 메뉴 == "📊 인기상품 분석":
    st.title("📊 인기상품 분석")
    인기검색어목록 = ["트위드자켓", "원피스", "트렌치코트", "바람막이", "블라우스", "무선이어폰", "텀블러", "청바지"]
    검색어 = st.text_input("분석할 상품명", placeholder="예: 무선이어폰")
    if st.button("분석하기", type="primary"):
        if 검색어:
            with st.spinner("분석 중..."):
                data = 네이버검색(검색어, 개수=50)
                상품목록, _ = 필터링(data.get('items', []))
                if 상품목록:
                    가격목록 = [s['가격'] for s in 상품목록]
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("최저가", f"{min(가격목록):,}원")
                    c2.metric("평균가", f"{sum(가격목록)//len(가격목록):,}원")
                    c3.metric("최고가", f"{max(가격목록):,}원")
                    c4.metric("수집 상품", f"{len(상품목록)}개")
                    st.divider()
                    st.subheader("📦 가격대별 분포")
                    구간 = {"1만원 이하": 0, "1~3만원": 0, "3~5만원": 0, "5~10만원": 0, "10만원 이상": 0}
                    for s in 상품목록:
                        g = s['가격']
                        if g < 10000: 구간["1만원 이하"] += 1
                        elif g < 30000: 구간["1~3만원"] += 1
                        elif g < 50000: 구간["3~5만원"] += 1
                        elif g < 100000: 구간["5~10만원"] += 1
                        else: 구간["10만원 이상"] += 1
                    st.bar_chart(pd.DataFrame.from_dict(구간, orient='index', columns=['상품수']))
    st.divider()
    st.subheader("🔥 오늘의 인기 검색어 현황")
    if st.button("인기 검색어 가격 불러오기"):
        with st.spinner("불러오는 중..."):
            결과목록 = []
            for kw in 인기검색어목록:
                data = 네이버검색(kw, 개수=20)
                상품목록, _ = 필터링(data.get('items', []))
                if 상품목록:
                    가격목록 = [s['가격'] for s in 상품목록]
                    결과목록.append({"검색어": kw, "최저가": min(가격목록), "평균가": sum(가격목록)//len(가격목록), "상품수": len(상품목록)})
            if 결과목록:
                df = pd.DataFrame(결과목록)
                st.dataframe(df, use_container_width=True)

elif 메뉴 == "🔥 트렌드 분석":
    st.title("🔥 네이버 쇼핑 트렌드")
    묶음선택 = st.radio("카테고리 묶음 선택", list(묶음맵.keys()))
    if 묶음선택 == "직접 선택":
        카테고리선택 = st.multiselect(
            "분석할 카테고리 선택 (최대 3개)",
            list(카테고리맵.keys()),
            default=["패션의류", "디지털/가전", "출산/육아"],
            max_selections=3
        )
        선택카테고리 = [{"name": k, "param": [카테고리맵[k]]} for k in 카테고리선택]
    else:
        선택카테고리 = 묶음맵[묶음선택]
    if st.button("트렌드 불러오기", type="primary"):
        if not 선택카테고리:
            st.warning("카테고리를 1개 이상 선택해주세요!")
        else:
            with st.spinner("트렌드 분석 중..."):
                url = "https://openapi.naver.com/v1/datalab/shopping/categories"
                headers = {
                    "X-Naver-Client-Id": NAVER_CLIENT_ID,
                    "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
                    "Content-Type": "application/json"
                }
                오늘 = datetime.now()
                한달전 = 오늘 - timedelta(days=30)
                body = {
                    "startDate": 한달전.strftime("%Y-%m-%d"),
                    "endDate": 오늘.strftime("%Y-%m-%d"),
                    "timeUnit": "date",
                    "category": 선택카테고리
                }
                response = requests.post(url, headers=headers, data=json.dumps(body))
                data = response.json()
                if 'results' in data:
                    st.subheader("📈 분야별 트렌드 (최근 30일)")
                    모든데이터 = {}
                    for result in data['results']:
                        for d in result['data']:
                            날짜 = d['period']
                            if 날짜 not in 모든데이터:
                                모든데이터[날짜] = {}
                            모든데이터[날짜][result['title']] = d['ratio']
                    df = pd.DataFrame.from_dict(모든데이터, orient='index')
                    df.index.name = '날짜'
                    st.line_chart(df)
                else:
                    st.error("트렌드 데이터를 불러오지 못했습니다.")
elif 메뉴 == "🏷️ 키워드 트렌드 분석":
    st.title("🏷️ 키워드 트렌드 분석")
    st.caption("실제 검색량 기준 해시태그 추천 + 트렌드 분석!")

    import hashlib, hmac, base64, time as time_module

    NAVER_AD_CUSTOMER_ID = "3243643"
    NAVER_AD_ACCESS_LICENSE = "0100000000432b8470231aa2f8b9c0e0ead165de5b9d08b05b12bc7c7b14b5834270295daa"
    NAVER_AD_SECRET_KEY = "AQAAAABDK4RwIxqi+LnA4OrRZd5bJ54kuAilmVD9E13ktwNDIQ=="

    def 검색량변환(값):
        try:
            v = str(값).replace(',', '').strip()
            if v.startswith('<'):
                return 0
            return int(v)
        except:
            return 0

    def 광고헤더(method, uri):
        timestamp = str(int(time_module.time() * 1000))
        message = f"{timestamp}.{method}.{uri}"
        h = hmac.new(NAVER_AD_SECRET_KEY.encode("utf-8"), message.encode("utf-8"), hashlib.sha256)
        signature = base64.b64encode(h.digest()).decode("utf-8")
        return {
            "Content-Type": "application/json; charset=UTF-8",
            "X-Timestamp": timestamp,
            "X-API-KEY": NAVER_AD_ACCESS_LICENSE,
            "X-Customer": NAVER_AD_CUSTOMER_ID,
            "X-Signature": signature
        }

    def 해시태그가져오기(키워드):
        uri = "/keywordstool"
        url = f"https://api.naver.com{uri}"
        headers = 광고헤더("GET", uri)
        params = {"hintKeywords": 키워드, "showDetail": 1}
        try:
            response = requests.get(url, headers=headers, params=params)
            data = response.json()
            목록 = data.get('keywordList', [])
            if not 목록:
                return []
            정렬 = sorted(목록, key=lambda x: 검색량변환(x.get('monthlyPcQcCnt', 0)) + 검색량변환(x.get('monthlyMobileQcCnt', 0)), reverse=True)
            return [f"#{item['relKeyword']}" for item in 정렬[:8]]
        except:
            return []

    키워드묶음 = {
        "여름 패션": ["수영복", "반바지", "샌들", "선글라스", "비키니"],
        "여름 용품": ["선크림", "물놀이", "아이스팩", "휴대용선풍기", "모기장"],
        "육아용품": ["유아식판", "젖병", "기저귀", "유모차", "아기욕조"],
        "주방용품": ["에어프라이어", "텀블러", "도시락통", "냄비", "프라이팬"],
        "인테리어": ["캔들", "무드등", "화분", "쿠션", "러그"],
    }

    탭1, 탭2 = st.tabs(["🏷️ 해시태그 추천", "🔥 트렌드 분석"])

    with 탭1:
        st.subheader("🏷️ 실제 검색량 기준 해시태그 추천")
        col1, col2 = st.columns(2)
        with col1:
            검색어 = st.text_input("키워드 입력", placeholder="예: 수영복, 에어프라이어")
        with col2:
            묶음선택 = st.selectbox("또는 묶음 선택", ["직접입력"] + list(키워드묶음.keys()))

        if st.button("해시태그 추천받기", type="primary"):
            분석키워드 = []
            if 검색어:
                분석키워드 = [k.strip() for k in 검색어.split(",")][:5]
            elif 묶음선택 != "직접입력":
                분석키워드 = 키워드묶음[묶음선택]

            if 분석키워드:
                for kw in 분석키워드:
                    with st.spinner(f"{kw} 해시태그 분석 중..."):
                        tags = 해시태그가져오기(kw)
                        if tags:
                            st.subheader(f"🏷️ {kw}")
                            st.success(" ".join(tags))
                            # 복사용
                            st.code(" ".join(tags))
                        else:
                            st.warning(f"{kw} 결과 없음")

    with 탭2:
        st.subheader("🔥 트렌드 분석")
        묶음선택2 = st.selectbox("카테고리 선택", list(키워드묶음.keys()), key="트렌드묶음")
        직접입력2 = st.text_input("또는 직접 입력 (쉼표로 구분)", placeholder="수영복,선글라스,비키니")

        if st.button("트렌드 분석하기", type="primary"):
            분석목록 = [k.strip() for k in 직접입력2.split(",")][:5] if 직접입력2 else 키워드묶음[묶음선택2]

            with st.spinner("트렌드 분석 중..."):
                url = "https://openapi.naver.com/v1/datalab/search"
                headers = {
                    "X-Naver-Client-Id": NAVER_CLIENT_ID,
                    "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
                    "Content-Type": "application/json"
                }
                오늘 = datetime.now()
                한달전 = 오늘 - timedelta(days=30)
                body = {
                    "startDate": 한달전.strftime("%Y-%m-%d"),
                    "endDate": 오늘.strftime("%Y-%m-%d"),
                    "timeUnit": "week",
                    "keywordGroups": [{"groupName": kw, "keywords": [kw]} for kw in 분석목록]
                }
                response = requests.post(url, headers=headers, data=json.dumps(body))
                data = response.json()

                if 'results' in data:
                    결과 = []
                    for result in data['results']:
                        데이터 = result['data']
                        if not 데이터:
                            continue
                        최근값 = 데이터[-1]['ratio'] if 데이터 else 0
                        이전값 = 데이터[-2]['ratio'] if len(데이터) >= 2 else 최근값
                        변화율 = ((최근값 - 이전값) / 이전값 * 100) if 이전값 > 0 else 0
                        결과.append({
                            "키워드": result['title'],
                            "최근검색량": 최근값,
                            "변화율": round(변화율, 1),
                            "트렌드": "🔥 급상승" if 변화율 > 20 else "📈 상승" if 변화율 > 0 else "📉 하락"
                        })

                    결과.sort(key=lambda x: x['최근검색량'], reverse=True)
                    c1, c2, c3 = st.columns(3)
                    c1.metric("1위 키워드", 결과[0]['키워드'])
                    c2.metric("최고 검색량", f"{결과[0]['최근검색량']:.1f}")
                    c3.metric("트렌드", 결과[0]['트렌드'])
                    st.divider()
                    df = pd.DataFrame(결과)
                    st.dataframe(df, use_container_width=True, hide_index=True)

elif 메뉴 == "⚔️ 경쟁강도 확인":
    st.title("⚔️ 경쟁강도 분석")
    상품명 = st.text_input("분석할 상품명", placeholder="예: 무선이어폰")
    if st.button("경쟁강도 분석", type="primary"):
        if 상품명:
            with st.spinner("분석 중..."):
                data = 네이버검색(상품명, 개수=100)
                전체상품수 = data.get('total', 0)
                상품목록, _ = 필터링(data.get('items', []))
                if 상품목록:
                    가격목록 = [s['가격'] for s in 상품목록]
                    쇼핑몰수 = len(set(s['쇼핑몰'] for s in 상품목록))
                    if 전체상품수 >= 50000:
                        등급 = "🔴 매우 치열"
                        추천 = "⚠️ 경쟁이 너무 치열해요. 다른 상품을 찾아보세요!"
                    elif 전체상품수 >= 10000:
                        등급 = "🟠 치열"
                        추천 = "🤔 차별화 전략이 필요해요"
                    elif 전체상품수 >= 3000:
                        등급 = "🟡 보통"
                        추천 = "😊 적당한 경쟁이에요. 도전해볼 만해요!"
                    elif 전체상품수 >= 500:
                        등급 = "🟢 낮음"
                        추천 = "✅ 경쟁이 적어요. 진입하기 좋아요!"
                    else:
                        등급 = "💎 블루오션"
                        추천 = "🎯 블루오션! 지금 당장 시작하세요!"
                    c1, c2, c3 = st.columns(3)
                    c1.metric("전체 상품 수", f"{전체상품수:,}개")
                    c2.metric("판매자 수", f"{쇼핑몰수}개")
                    c3.metric("평균가", f"{sum(가격목록)//len(가격목록):,}원")
                    st.divider()
                    st.subheader(f"경쟁등급: {등급}")
                    st.info(추천)
                    st.divider()
                    st.subheader("📦 주요 판매자")
                    쇼핑몰카운트 = {}
                    for s in 상품목록:
                        쇼핑몰카운트[s['쇼핑몰']] = 쇼핑몰카운트.get(s['쇼핑몰'], 0) + 1
                    df = pd.DataFrame(list(쇼핑몰카운트.items()), columns=['쇼핑몰', '상품수'])
                    df = df.sort_values('상품수', ascending=False).head(10)
                    st.bar_chart(df.set_index('쇼핑몰'))

elif 메뉴 == "💰 마진 계산기":
    st.title("💰 마진 계산기")
    st.caption("플랫폼별 최소 판매가를 계산해드려요!")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        매입가 = st.number_input("매입가 (원)", min_value=0, value=10000, step=100)
    with col2:
        배송비 = st.number_input("배송비 (원)", min_value=0, value=3000, step=500)
    with col3:
        수량 = st.number_input("판매 수량", min_value=1, value=1, step=1)
    with col4:
        목표마진 = st.number_input("목표 마진율 (%)", min_value=0, value=20, step=1)
    개당배송비 = 배송비 / 수량
    st.divider()
    if st.button("계산하기", type="primary"):
        플랫폼목록 = {
            "스마트스토어": 0.055, "쿠팡": 0.108,
            "G마켓": 0.12, "옥션": 0.12,
            "11번가": 0.09, "카카오쇼핑": 0.05,
        }
        결과목록 = []
        for 플랫폼, 수수료 in 플랫폼목록.items():
            손익분기가 = (매입가 + 개당배송비) / (1 - 수수료 - 0.036)
            목표마진가 = (매입가 + 개당배송비) / (1 - 수수료 - 0.036 - 목표마진 / 100)
            결과목록.append({
                "플랫폼": 플랫폼,
                "수수료": f"{수수료*100:.1f}%",
                "손익분기가": f"{손익분기가:,.0f}원",
                "목표마진가": f"{목표마진가:,.0f}원",
            })
        c1, c2, c3 = st.columns(3)
        c1.metric("매입가", f"{매입가:,}원")
        c2.metric("개당 배송비", f"{개당배송비:,.0f}원")
        c3.metric("목표 마진율", f"{목표마진}%")
        st.divider()
        df = pd.DataFrame(결과목록)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.divider()
        if 수량 > 1:
            st.info(f"💡 {수량}개 묶음 판매시 개당 배송비가 {배송비:,}원 → {개당배송비:,.0f}원으로 줄어들어요!")
        st.caption("손익분기가 = 이 가격 아래로 팔면 손해 | 목표마진가 = 목표 마진율 달성 가격")

elif 메뉴 == "🛒 소싱 도우미":
    st.title("🛒 상품 소싱 도우미")
    st.caption("도매꾹에서 마진 좋은 상품을 자동으로 찾아드려요!")

    현재월 = datetime.now().month
    if 3 <= 현재월 <= 5: 현재계절 = "봄 (3~5월)"
    elif 6 <= 현재월 <= 8: 현재계절 = "여름 (6~8월)"
    elif 9 <= 현재월 <= 11: 현재계절 = "가을 (9~11월)"
    else: 현재계절 = "겨울 (12~2월)"

    수수료율맵 = {"스마트스토어": 0.055, "쿠팡": 0.108, "G마켓": 0.12, "11번가": 0.09}

    탭1, 탭2 = st.tabs(["🔍 상품 소싱 분석", "🌸 계절 추천 상품"])

    with 탭1:
        col1, col2, col3 = st.columns(3)
        with col1:
            검색어 = st.text_input("분석할 상품명", placeholder="예: 수영가방, 핫팩")
        with col2:
            목표마진 = st.number_input("목표 마진율 (%)", min_value=1, value=20, step=1)
        with col3:
            플랫폼선택 = st.selectbox("판매 플랫폼", ["스마트스토어", "쿠팡", "G마켓", "11번가"])

        if st.button("소싱 분석하기", type="primary"):
            if 검색어:
                with st.spinner(f"'{검색어}' 소싱 분석 중..."):
                    naver_data = 네이버검색(검색어, 개수=30)
                    가격목록 = []
                    for item in naver_data.get('items', []):
                        가격 = int(item['lprice'])
                        if 가격 <= 100: continue
                        해외키워드 = ['직구', '해외', '구매대행', 'USA', '중국', '헤외', '면세']
                        if any(k in item['title'] or k in item['mallName'] for k in 해외키워드): continue
                        가격목록.append(가격)

                    if not 가격목록:
                        st.error("네이버 시장 데이터를 가져올 수 없습니다.")
                    else:
                        가격목록.sort()
                        시장평균가 = 가격목록[len(가격목록)//2]
                        dome_data = 도매꾹검색(검색어, 개수=50)
                        추천상품 = []
                        수수료 = 수수료율맵[플랫폼선택]

                        for s in dome_data:
                            도매가 = s['가격']
                            배송비 = s['배송비']
                            if 도매가 <= 0: continue
                            플랫폼수수료 = 시장평균가 * 수수료
                            결제수수료 = 시장평균가 * 0.036
                            순이익 = 시장평균가 - 도매가 - 배송비 - 플랫폼수수료 - 결제수수료
                            마진율 = round((순이익 / 시장평균가) * 100, 1)
                            if 마진율 >= 목표마진:
                                추천상품.append({**s, "시장평균가": 시장평균가, "마진율": 마진율, "순이익": round(순이익)})

                        추천상품.sort(key=lambda x: x['마진율'], reverse=True)
                        c1, c2, c3 = st.columns(3)
                        c1.metric("네이버 시장 평균가", f"{시장평균가:,}원")
                        c2.metric("소싱 가능 상품", f"{len(추천상품)}개")
                        c3.metric("최고 마진율", f"{추천상품[0]['마진율']}%" if 추천상품 else "0%")

                        if 추천상품:
                            st.divider()
                            st.subheader(f"✅ 마진 {목표마진}% 이상 추천 상품 TOP 10")
                            for i, s in enumerate(추천상품[:10], 1):
                                배송표시 = "무료배송" if s['배송비'] == 0 else f"배송비 {s['배송비']:,}원"
                                마진색 = "🟢" if s['마진율'] >= 30 else "🟡" if s['마진율'] >= 20 else "🔴"
                                c1, c2, c3, c4, c5 = st.columns([3, 1, 1, 1, 1])
                                c1.write(f"**{i}. {s['제목'][:30]}**")
                                c2.write(f"도매가 {s['가격']:,}원")
                                c3.write(f"{배송표시}")
                                c4.write(f"{마진색} {s['마진율']}%")
                                c5.link_button("구매링크", s['링크'])
                        else:
                            st.warning(f"마진 {목표마진}% 이상 상품이 없어요. 목표 마진율을 낮춰보세요!")

    with 탭2:
        st.subheader(f"🌸 현재 계절 추천 상품 ({현재계절})")
        추천목록 = 계절상품맵[현재계절]
        cols = st.columns(len(추천목록))
        for i, (col, 상품) in enumerate(zip(cols, 추천목록)):
            with col:
                st.info(f"🔍 {상품}")

        st.divider()
        if st.button("🚀 계절 상품 전체 자동 소싱 분석", type="primary"):
            수수료 = 수수료율맵.get("스마트스토어", 0.055)
            전체추천 = []
            진행바 = st.progress(0)
            for idx, 상품명 in enumerate(추천목록):
                st.write(f"🔍 {상품명} 분석 중...")
                naver_data = 네이버검색(상품명, 개수=20)
                가격목록 = [int(item['lprice']) for item in naver_data.get('items', []) if int(item['lprice']) > 100]
                if not 가격목록: continue
                가격목록.sort()
                시장평균가 = 가격목록[len(가격목록)//2]
                dome_data = 도매꾹검색(상품명, 개수=20)
                for s in dome_data:
                    도매가 = s['가격']
                    배송비 = s['배송비']
                    if 도매가 <= 0: continue
                    순이익 = 시장평균가 - 도매가 - 배송비 - 시장평균가 * 0.055 - 시장평균가 * 0.036
                    마진율 = round((순이익 / 시장평균가) * 100, 1)
                    if 마진율 >= 20:
                        전체추천.append({**s, "검색어": 상품명, "시장평균가": 시장평균가, "마진율": 마진율, "순이익": round(순이익)})
                진행바.progress((idx + 1) / len(추천목록))

            if 전체추천:
                전체추천.sort(key=lambda x: x['마진율'], reverse=True)
                st.divider()
                st.subheader("🏆 계절 상품 중 마진 TOP 10")
                for i, s in enumerate(전체추천[:10], 1):
                    마진색 = "🟢" if s['마진율'] >= 30 else "🟡"
                    c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
                    c1.write(f"**{i}. [{s['검색어']}] {s['제목'][:25]}**")
                    c2.write(f"도매가 {s['가격']:,}원")
                    c3.write(f"{마진색} {s['마진율']}%")
                    c4.link_button("구매", s['링크'])
            else:
                st.warning("마진 20% 이상 상품을 찾지 못했어요.")
elif 메뉴 == "📒 수익 관리 장부":
    st.title("📒 수익 관리 장부")
    st.caption("판매 내역을 기록하고 수익을 자동으로 계산해드려요!")

    import os

    장부파일 = "장부.json"

    def 장부불러오기():
        if os.path.exists(장부파일):
            with open(장부파일, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []

    def 장부저장(데이터):
        with open(장부파일, 'w', encoding='utf-8') as f:
            json.dump(데이터, f, ensure_ascii=False, indent=2)

    수수료율맵 = {
        "스마트스토어": 0.055, "쿠팡": 0.108,
        "G마켓": 0.12, "옥션": 0.12,
        "11번가": 0.09, "카카오쇼핑": 0.05
    }

    탭1, 탭2, 탭3 = st.tabs(["📝 판매 등록", "📊 수익 현황", "📅 월별 분석"])

    with 탭1:
        st.subheader("📝 판매 내역 등록")
        col1, col2 = st.columns(2)
        with col1:
            판매상품 = st.text_input("상품명", placeholder="예: 미키마우스 식판")
            매입가 = st.number_input("매입가 (원)", min_value=0, value=5000, step=100)
            배송비 = st.number_input("배송비 (원)", min_value=0, value=3000, step=500)
        with col2:
            판매가 = st.number_input("판매가 (원)", min_value=0, value=15000, step=100)
            판매수량 = st.number_input("판매 수량", min_value=1, value=1, step=1)
            플랫폼 = st.selectbox("판매 플랫폼", list(수수료율맵.keys()))
            판매일 = st.date_input("판매일", value=datetime.now())

        if st.button("판매 등록하기", type="primary"):
            if 판매상품:
                수수료 = 수수료율맵[플랫폼]
                플랫폼수수료 = 판매가 * 수수료
                결제수수료 = 판매가 * 0.036
                순이익 = (판매가 - 매입가 - 배송비 - 플랫폼수수료 - 결제수수료) * 판매수량
                매출 = 판매가 * 판매수량

                장부 = 장부불러오기()
                장부.append({
                    "날짜": 판매일.strftime("%Y-%m-%d"),
                    "상품명": 판매상품,
                    "플랫폼": 플랫폼,
                    "매입가": 매입가,
                    "판매가": 판매가,
                    "수량": 판매수량,
                    "배송비": 배송비,
                    "매출": round(매출),
                    "순이익": round(순이익),
                    "마진율": round((순이익 / 매출) * 100, 1) if 매출 > 0 else 0
                })
                장부저장(장부)

                c1, c2, c3 = st.columns(3)
                c1.metric("매출", f"{매출:,}원")
                c2.metric("순이익", f"{순이익:,.0f}원")
                c3.metric("마진율", f"{round((순이익/매출)*100, 1)}%")
                st.success(f"✅ '{판매상품}' 판매 등록 완료!")

    with 탭2:
        st.subheader("📊 전체 수익 현황")
        장부 = 장부불러오기()

        if not 장부:
            st.info("아직 등록된 판매 내역이 없어요. 판매 등록 탭에서 추가해주세요!")
        else:
            총매출 = sum(s['매출'] for s in 장부)
            총순이익 = sum(s['순이익'] for s in 장부)
            총판매건수 = len(장부)
            평균마진율 = round(sum(s['마진율'] for s in 장부) / 총판매건수, 1)

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("총 매출", f"{총매출:,}원")
            c2.metric("총 순이익", f"{총순이익:,}원")
            c3.metric("총 판매건수", f"{총판매건수}건")
            c4.metric("평균 마진율", f"{평균마진율}%")

            st.divider()

            # 플랫폼별 수익
            st.subheader("🏪 플랫폼별 수익")
            플랫폼별 = {}
            for s in 장부:
                p = s['플랫폼']
                if p not in 플랫폼별:
                    플랫폼별[p] = {"매출": 0, "순이익": 0, "건수": 0}
                플랫폼별[p]["매출"] += s['매출']
                플랫폼별[p]["순이익"] += s['순이익']
                플랫폼별[p]["건수"] += 1

            플랫폼df = pd.DataFrame([
                {"플랫폼": k, "매출": f"{v['매출']:,}원", "순이익": f"{v['순이익']:,}원", "건수": f"{v['건수']}건"}
                for k, v in 플랫폼별.items()
            ])
            st.dataframe(플랫폼df, use_container_width=True, hide_index=True)

            st.divider()
            st.subheader("📋 전체 판매 내역")
            df = pd.DataFrame(장부)
            df['매출'] = df['매출'].apply(lambda x: f"{x:,}원")
            df['순이익'] = df['순이익'].apply(lambda x: f"{x:,}원")
            df['마진율'] = df['마진율'].apply(lambda x: f"{x}%")
            st.dataframe(df[['날짜', '상품명', '플랫폼', '판매가', '수량', '매출', '순이익', '마진율']], 
                        use_container_width=True, hide_index=True)

            if st.button("🗑️ 전체 내역 초기화", type="secondary"):
                장부저장([])
                st.success("초기화 완료!")
                st.rerun()

    with 탭3:
        st.subheader("📅 월별 수익 분석")
        장부 = 장부불러오기()

        if not 장부:
            st.info("아직 등록된 판매 내역이 없어요!")
        else:
            월별 = {}
            for s in 장부:
                월 = s['날짜'][:7]
                if 월 not in 월별:
                    월별[월] = {"매출": 0, "순이익": 0, "건수": 0}
                월별[월]["매출"] += s['매출']
                월별[월]["순이익"] += s['순이익']
                월별[월]["건수"] += 1

            월별df = pd.DataFrame([
                {"월": k, "매출": v['매출'], "순이익": v['순이익'], "건수": v['건수']}
                for k, v in sorted(월별.items())
            ])

            st.bar_chart(월별df.set_index('월')[['매출', '순이익']])
            st.divider()
            월별df['매출'] = 월별df['매출'].apply(lambda x: f"{x:,}원")
            월별df['순이익'] = 월별df['순이익'].apply(lambda x: f"{x:,}원")
            st.dataframe(월별df, use_container_width=True, hide_index=True)
elif 메뉴 == "📦 재고/품절 알림":
    st.title("📦 재고/품절 알림")
    st.caption("도매꾹 공급처 품절 시 텔레그램으로 즉시 알림!")

    import os

    재고파일 = "재고모니터링.json"

    def 재고목록불러오기():
        if os.path.exists(재고파일):
            with open(재고파일, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []

    def 재고목록저장(목록):
        with open(재고파일, 'w', encoding='utf-8') as f:
            json.dump(목록, f, ensure_ascii=False, indent=2)

    def 도매꾹상품조회(상품번호):
        url = "https://domeggook.com/ssl/api/"
        params = {
            "ver": "4.1", "mode": "getItemList",
            "aid": DOMEGGOOK_API_KEY, "market": "dome",
            "om": "json", "itemNo": 상품번호
        }
        try:
            data = requests.get(url, params=params).json()
            items = data['domeggook']['list']['item']
            if isinstance(items, dict):
                items = [items]
            return items[0] if items else None
        except:
            return None

    def send_telegram(text):
        url = f"https://api.telegram.org/bot8797313748:AAFodzMuWNEBGLPnYIs4GgjcU3WJs-Sd3Bo/sendMessage"
        params = {"chat_id": "6943475461", "text": text, "parse_mode": "HTML"}
        try:
            requests.post(url, params=params)
        except:
            pass

    탭1, 탭2 = st.tabs(["📋 모니터링 목록", "➕ 상품 등록"])

    with 탭2:
        st.subheader("➕ 재고 모니터링 상품 등록")
        st.info("💡 도매꾹 상품 주소에서 숫자 부분이 상품번호예요!\n예: http://domeggook.com/44049099 → 상품번호: 44049099")
        col1, col2 = st.columns(2)
        with col1:
            상품번호 = st.text_input("도매꾹 상품번호", placeholder="예: 44049099")
        with col2:
            상품명입력 = st.text_input("상품명", placeholder="예: 미키마우스 식판")

        if st.button("모니터링 등록하기", type="primary"):
            if 상품번호 and 상품명입력:
                목록 = 재고목록불러오기()
                이미등록 = any(s['상품번호'] == 상품번호 for s in 목록)
                if 이미등록:
                    st.warning("이미 등록된 상품이에요!")
                else:
                    목록.append({
                        "상품번호": 상품번호,
                        "상품명": 상품명입력,
                        "등록일시": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "마지막체크": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "상태": "판매중",
                        "링크": f"http://domeggook.com/{상품번호}"
                    })
                    재고목록저장(목록)
                    send_telegram(f"📦 <b>재고 모니터링 등록!</b>\n상품명: {상품명입력}\n상품번호: {상품번호}")
                    st.success(f"✅ '{상품명입력}' 모니터링 등록 완료!")

    with 탭1:
        st.subheader("📋 모니터링 중인 상품 목록")
        목록 = 재고목록불러오기()

        if not 목록:
            st.info("등록된 상품이 없어요. 상품 등록 탭에서 추가해주세요!")
        else:
            if st.button("🔄 지금 바로 재고 체크", type="primary"):
                with st.spinner("재고 체크 중..."):
                    변동있음 = False
                    for i, 상품 in enumerate(목록):
                        item = 도매꾹상품조회(상품['상품번호'])
                        이전상태 = 상품['상태']
                        새상태 = "판매중" if item else "품절/삭제"
                        목록[i]['상태'] = 새상태
                        목록[i]['마지막체크'] = datetime.now().strftime("%Y-%m-%d %H:%M")

                        if 이전상태 != 새상태:
                            변동있음 = True
                            if 새상태 == "품절/삭제":
                                send_telegram(f"🚨 <b>품절 알림!</b>\n상품명: {상품['상품명']}\n⚠️ 품절되었어요!\n🔗 {상품['링크']}")
                                st.error(f"🚨 품절! {상품['상품명']}")
                            else:
                                send_telegram(f"✅ <b>재입고 알림!</b>\n상품명: {상품['상품명']}\n🎉 다시 판매 중이에요!")
                                st.success(f"✅ 재입고! {상품['상품명']}")

                    재고목록저장(목록)
                    if not 변동있음:
                        st.success("✅ 모든 상품 정상 판매 중!")

            st.divider()
            for i, s in enumerate(목록):
                상태색 = "🟢" if s['상태'] == "판매중" else "🔴"
                c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
                c1.write(f"**{상태색} {s['상품명']}**")
                c2.write(f"{s['상태']}")
                c3.write(f"체크: {s['마지막체크']}")
                if c4.button("삭제", key=f"del_{i}"):
                    목록.pop(i)
                    재고목록저장(목록)
                    st.rerun()
elif 메뉴 == "🏪 상품 등록 도우미":
    st.title("🏪 상품 등록 도우미")
    st.caption("도매꾹 상품번호 입력 → 스마트스토어/쿠팡 등록 형식 자동 변환!")

    def 도매꾹상품상세조회(상품번호):
        url = "https://domeggook.com/ssl/api/"
        params = {
            "ver": "4.1", "mode": "getItemList",
            "aid": DOMEGGOOK_API_KEY, "market": "dome",
            "om": "json", "itemNo": 상품번호
        }
        try:
            data = requests.get(url, params=params).json()
            items = data['domeggook']['list']['item']
            if isinstance(items, dict):
                items = [items]
            return items[0] if items else None
        except:
            return None

    col1, col2 = st.columns([2, 1])
    with col1:
        상품번호 = st.text_input("도매꾹 상품번호", placeholder="예: 44049099")
    with col2:
        목표마진 = st.number_input("목표 마진율 (%)", min_value=1, value=30, step=1)

    st.info("💡 도매꾹 상품 주소에서 숫자 부분이 상품번호예요!\n예: http://domeggook.com/44049099 → 44049099")

    if st.button("상품 정보 불러오기", type="primary"):
        if 상품번호:
            with st.spinner("도매꾹 상품 조회 중..."):
                item = 도매꾹상품상세조회(상품번호)

                if not item:
                    st.error("상품을 찾을 수 없어요. 상품번호를 확인해주세요!")
                else:
                    제목 = item.get('title', '')
                    매입가 = int(item.get('price', 0))
                    배송구분 = item.get('deli', {}).get('who', '')
                    배송비 = int(item.get('deli', {}).get('fee', 0) or 0)
                    if 배송구분 == 'S':
                        배송비 = 0
                    최소수량 = item.get('unitQty', 1)
                    링크 = item.get('url', '')

                    st.divider()
                    st.subheader("📦 도매꾹 상품 정보")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("매입가", f"{매입가:,}원")
                    c2.metric("배송비", f"{배송비:,}원")
                    c3.metric("최소수량", f"{최소수량}개")
                    st.write(f"**상품명:** {제목}")
                    st.link_button("도매꾹 상품 보기", 링크)

                    st.divider()
                    st.subheader("🏪 플랫폼별 등록 정보")

                    수수료율맵 = {
                        "스마트스토어": 0.055,
                        "쿠팡": 0.108,
                        "G마켓": 0.12,
                        "옥션": 0.12,
                        "11번가": 0.09,
                        "카카오쇼핑": 0.05
                    }

                    결과목록 = []
                    for 플랫폼, 수수료 in 수수료율맵.items():
                        추천판매가 = int((매입가 + 배송비) / (1 - 수수료 - 0.036 - 목표마진/100))
                        예상순이익 = int(추천판매가 * (목표마진/100))
                        결과목록.append({
                            "플랫폼": 플랫폼,
                            "수수료": f"{수수료*100:.1f}%",
                            "추천 판매가": f"{추천판매가:,}원",
                            "예상 순이익": f"{예상순이익:,}원"
                        })

                    df = pd.DataFrame(결과목록)
                    st.dataframe(df, use_container_width=True, hide_index=True)

                    st.divider()
                    st.subheader("📋 스마트스토어 등록 체크리스트")
                    스마트판매가 = int((매입가 + 배송비) / (1 - 0.055 - 0.036 - 목표마진/100))

                    st.markdown(f"""
                                elif 메뉴 == "💎 블루오션 탐지":
    st.title("💎 블루오션 상품 탐지")
    st.caption("경쟁 적은 블루오션 상품을 자동으로 찾아드려요!")

    import os

    블루키워드파일 = "블루오션키워드.json"

    def 키워드불러오기():
        if os.path.exists(블루키워드파일):
            with open(블루키워드파일, 'r', encoding='utf-8') as f:
                return json.load(f)
        return ["아기방수턱받이", "실리콘이유식용기", "유아치발기세트",
                "캠핑랜턴고리", "텐트팩가방", "캠핑수저세트",
                "무선충전거치대차량용", "케이블클립정리", "노트북파우치14인치",
                "고양이해먹", "강아지이동가방", "반려동물물병",
                "주방서랍정리함", "냉장고정리용기", "싱크대수납",
                "욕실선반흡착", "칫솔살균기", "면도기거치대",
                "독서대접이식", "태블릿거치대침대"]

    def 키워드저장(목록):
        with open(블루키워드파일, 'w', encoding='utf-8') as f:
            json.dump(목록, f, ensure_ascii=False, indent=2)

    def send_telegram(text):
        url = f"https://api.telegram.org/bot8797313748:AAFodzMuWNEBGLPnYIs4GgjcU3WJs-Sd3Bo/sendMessage"
        params = {"chat_id": "6943475461", "text": text, "parse_mode": "HTML"}
        try:
            requests.post(url, params=params)
        except:
            pass

    def 블루오션탐지(키워드):
        data = 네이버검색(키워드, 개수=20)
        전체상품수 = data.get('total', 0)
        items = data.get('items', [])
        if not items:
            return None
        가격목록 = []
        for item in items:
            try:
                가격 = int(item['lprice'])
                if 가격 > 100:
                    가격목록.append(가격)
            except:
                continue
        if not 가격목록:
            return None
        평균가 = sum(가격목록) // len(가격목록)
        최저가 = min(가격목록)
        if 전체상품수 < 500:
            등급 = "💎 블루오션"
        elif 전체상품수 < 3000:
            등급 = "🟢 경쟁낮음"
        elif 전체상품수 < 10000:
            등급 = "🟡 보통"
        else:
            return None
        return {"키워드": 키워드, "전체상품수": 전체상품수, "평균가": 평균가, "최저가": 최저가, "등급": 등급}

    탭1, 탭2 = st.tabs(["🔍 블루오션 탐지", "⚙️ 키워드 관리"])

    with 탭1:
        st.subheader("🔍 블루오션 상품 탐지")
        경쟁기준 = st.selectbox("탐지 기준", ["💎 블루오션만 (500개 미만)", "🟢 경쟁낮음 포함 (3000개 미만)", "🟡 보통 포함 (10000개 미만)"])

        if st.button("💎 블루오션 탐지 시작", type="primary"):
            키워드목록 = 키워드불러오기()
            발견목록 = []
            진행바 = st.progress(0)
            상태창 = st.empty()

            for i, 키워드 in enumerate(키워드목록):
                상태창.write(f"🔍 {키워드} 분석 중... ({i+1}/{len(키워드목록)})")
                결과 = 블루오션탐지(키워드)
                if 결과:
                    if "블루오션만" in 경쟁기준 and 결과['전체상품수'] < 500:
                        발견목록.append(결과)
                    elif "경쟁낮음" in 경쟁기준 and 결과['전체상품수'] < 3000:
                        발견목록.append(결과)
                    elif "보통" in 경쟁기준:
                        발견목록.append(결과)
                진행바.progress((i + 1) / len(키워드목록))

            상태창.empty()

            if 발견목록:
                발견목록.sort(key=lambda x: x['전체상품수'])
                c1, c2 = st.columns(2)
                c1.metric("발견된 상품", f"{len(발견목록)}개")
                c2.metric("최고 블루오션", 발견목록[0]['키워드'])
                st.divider()
                for r in 발견목록:
                    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
                    c1.write(f"**{r['등급']} {r['키워드']}**")
                    c2.write(f"상품수 {r['전체상품수']:,}개")
                    c3.write(f"평균가 {r['평균가']:,}원")
                    c4.write(f"최저가 {r['최저가']:,}원")

                if st.button("📱 텔레그램으로 결과 전송", type="secondary"):
                    메시지 = f"💎 <b>블루오션 탐지 결과!</b>\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
                    for r in 발견목록[:5]:
                        메시지 += f"{r['등급']} <b>{r['키워드']}</b>\n상품수: {r['전체상품수']:,}개 | 평균가: {r['평균가']:,}원\n\n"
                    send_telegram(메시지)
                    st.success("✅ 텔레그램 전송 완료!")
            else:
                st.warning("블루오션 상품을 찾지 못했어요. 기준을 낮추거나 키워드를 추가해보세요!")

    with 탭2:
        st.subheader("⚙️ 키워드 관리")
        키워드목록 = 키워드불러오기()

        col1, col2 = st.columns([3, 1])
        with col1:
            새키워드 = st.text_input("새 키워드 추가", placeholder="예: 아기욕조의자")
        with col2:
            if st.button("추가", type="primary"):
                if 새키워드 and 새키워드 not in 키워드목록:
                    키워드목록.append(새키워드.strip())
                    키워드저장(키워드목록)
                    st.success(f"✅ '{새키워드}' 추가!")
                    st.rerun()

        st.divider()
        st.write(f"**현재 키워드 목록 ({len(키워드목록)}개)**")
        for i, kw in enumerate(키워드목록):
            c1, c2 = st.columns([4, 1])
            c1.write(f"• {kw}")
            if c2.button("삭제", key=f"del_kw_{i}"):
                키워드목록.pop(i)
                키워드저장(키워드목록)
                st.rerun()

| 항목 | 내용 |
|------|------|
| 상품명 | {제목[:50]} |
| 판매가 | {스마트판매가:,}원 |
| 재고수량 | 999개 (위탁배송) |
| 배송방법 | 택배 |
| 배송비 | {배송비:,}원 |
| 최소구매수량 | {최소수량}개 |
| 출고지 | 공급업체 직배송 |
""")
elif 메뉴 == "💎 블루오션 탐지":
    st.title("💎 블루오션 상품 탐지")
    st.caption("경쟁 적은 블루오션 상품을 자동으로 찾아드려요!")

    import os

    블루키워드파일 = "블루오션키워드.json"

    def 키워드불러오기():
        if os.path.exists(블루키워드파일):
            with open(블루키워드파일, 'r', encoding='utf-8') as f:
                return json.load(f)
        return ["아기방수턱받이", "실리콘이유식용기", "유아치발기세트",
                "캠핑랜턴고리", "텐트팩가방", "캠핑수저세트",
                "무선충전거치대차량용", "케이블클립정리", "노트북파우치14인치",
                "고양이해먹", "강아지이동가방", "반려동물물병",
                "주방서랍정리함", "냉장고정리용기", "싱크대수납",
                "욕실선반흡착", "칫솔살균기", "면도기거치대",
                "독서대접이식", "태블릿거치대침대"]

    def 키워드저장(목록):
        with open(블루키워드파일, 'w', encoding='utf-8') as f:
            json.dump(목록, f, ensure_ascii=False, indent=2)

    def send_telegram_blue(text):
        url = f"https://api.telegram.org/bot8797313748:AAFodzMuWNEBGLPnYIs4GgjcU3WJs-Sd3Bo/sendMessage"
        params = {"chat_id": "6943475461", "text": text, "parse_mode": "HTML"}
        try:
            requests.post(url, params=params)
        except:
            pass

    def 블루오션탐지단건(키워드):
        data = 네이버검색(키워드, 개수=20)
        전체상품수 = data.get('total', 0)
        items = data.get('items', [])
        if not items:
            return None
        가격목록 = []
        for item in items:
            try:
                가격 = int(item['lprice'])
                if 가격 > 100:
                    가격목록.append(가격)
            except:
                continue
        if not 가격목록:
            return None
        평균가 = sum(가격목록) // len(가격목록)
        최저가 = min(가격목록)
        if 전체상품수 < 500:
            등급 = "💎 블루오션"
        elif 전체상품수 < 3000:
            등급 = "🟢 경쟁낮음"
        elif 전체상품수 < 10000:
            등급 = "🟡 보통"
        else:
            return None
        return {"키워드": 키워드, "전체상품수": 전체상품수, "평균가": 평균가, "최저가": 최저가, "등급": 등급}

    탭1, 탭2 = st.tabs(["🔍 블루오션 탐지", "⚙️ 키워드 관리"])

    with 탭1:
        st.subheader("🔍 블루오션 상품 탐지")
        경쟁기준 = st.selectbox("탐지 기준", ["💎 블루오션만 (500개 미만)", "🟢 경쟁낮음 포함 (3000개 미만)", "🟡 보통 포함 (10000개 미만)"])
        if st.button("💎 블루오션 탐지 시작", type="primary"):
            키워드목록 = 키워드불러오기()
            발견목록 = []
            진행바 = st.progress(0)
            상태창 = st.empty()
            for i, 키워드 in enumerate(키워드목록):
                상태창.write(f"🔍 {키워드} 분석 중... ({i+1}/{len(키워드목록)})")
                결과 = 블루오션탐지단건(키워드)
                if 결과:
                    if "블루오션만" in 경쟁기준 and 결과['전체상품수'] < 500:
                        발견목록.append(결과)
                    elif "경쟁낮음" in 경쟁기준 and 결과['전체상품수'] < 3000:
                        발견목록.append(결과)
                    elif "보통" in 경쟁기준:
                        발견목록.append(결과)
                진행바.progress((i + 1) / len(키워드목록))
            상태창.empty()
            if 발견목록:
                발견목록.sort(key=lambda x: x['전체상품수'])
                c1, c2 = st.columns(2)
                c1.metric("발견된 상품", f"{len(발견목록)}개")
                c2.metric("최고 블루오션", 발견목록[0]['키워드'])
                st.divider()
                for r in 발견목록:
                    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
                    c1.write(f"**{r['등급']} {r['키워드']}**")
                    c2.write(f"상품수 {r['전체상품수']:,}개")
                    c3.write(f"평균가 {r['평균가']:,}원")
                    c4.write(f"최저가 {r['최저가']:,}원")
                if st.button("📱 텔레그램 전송", type="secondary"):
                    메시지 = f"💎 <b>블루오션 탐지 결과!</b>\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
                    for r in 발견목록[:5]:
                        메시지 += f"{r['등급']} <b>{r['키워드']}</b>\n상품수: {r['전체상품수']:,}개 | 평균가: {r['평균가']:,}원\n\n"
                    send_telegram_blue(메시지)
                    st.success("✅ 텔레그램 전송 완료!")
            else:
                st.warning("블루오션 상품을 찾지 못했어요. 기준을 낮추거나 키워드를 추가해보세요!")

    with 탭2:
        st.subheader("⚙️ 키워드 관리")
        키워드목록 = 키워드불러오기()
        col1, col2 = st.columns([3, 1])
        with col1:
            새키워드 = st.text_input("새 키워드 추가", placeholder="예: 아기욕조의자")
        with col2:
            if st.button("추가", type="primary"):
                if 새키워드 and 새키워드 not in 키워드목록:
                    키워드목록.append(새키워드.strip())
                    키워드저장(키워드목록)
                    st.success(f"✅ '{새키워드}' 추가!")
                    st.rerun()
        st.divider()
        st.write(f"**현재 키워드 목록 ({len(키워드목록)}개)**")
        for i, kw in enumerate(키워드목록):
            c1, c2 = st.columns([4, 1])
            c1.write(f"• {kw}")
            if c2.button("삭제", key=f"del_kw_{i}"):
                키워드목록.pop(i)
                키워드저장(키워드목록)
                st.rerun()