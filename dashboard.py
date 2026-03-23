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

st.set_page_config(page_title="위탁배송 대시보드", page_icon="🛒", layout="wide")

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
    header {visibility: hidden;}
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
    "⚔️ 경쟁강도 확인",
    "💰 마진 계산기",
    "🛒 소싱 도우미"
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
            출처아이콘 = {
                "G마켓": "🟡", "옥션": "🟠", "쿠팡": "🟠",
                "11번가": "🔴", "스마트스토어": "🟢", "도매꾹": "🔵"
}
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