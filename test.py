import requests

CLIENT_ID = "NmoPGi9LLT1pbGFRCQ45"
CLIENT_SECRET = "Z60X30C0Li"

def 최저가검색(상품명):
    url = "https://openapi.naver.com/v1/search/shop.json"
    headers = {
        "X-Naver-Client-Id": CLIENT_ID,
        "X-Naver-Client-Secret": CLIENT_SECRET
    }
    params = {"query": 상품명, "sort": "sim", "display": 100}
    
    response = requests.get(url, headers=headers, params=params)
    data = response.json()

    필터상품 = []
    제외목록 = []

    for item in data['items']:
        가격 = int(item['lprice'])
        제목 = item['title']
        쇼핑몰 = item['mallName']

        # ① 가짜 가격 제외
        if 가격 <= 100:
            제외목록.append(f"가격이상: {제목[:20]}")
            continue

        # ② 해외배송 제외
        해외키워드 = ['직구', '해외', '구매대행', 'USA', 'US', '중국', '일본배송']
        if any(k in 제목 or k in 쇼핑몰 for k in 해외키워드):
            제외목록.append(f"해외배송: {제목[:20]}")
            continue

        # ③ 미끼상품 의심 제외 (평균가의 30% 미만)
        필터상품.append(item)

    # 평균가 계산 후 미끼상품 제외
    if not 필터상품:
        print("조건에 맞는 상품이 없습니다.")
        return

    가격목록 = [int(i['lprice']) for i in 필터상품]
    평균가 = sum(가격목록) // len(가격목록)

    최종상품 = []
    for item in 필터상품:
        가격 = int(item['lprice'])
        if 가격 < 평균가 * 0.3:
            제외목록.append(f"미끼의심: {item['title'][:20]} ({가격:,}원)")
            continue
        최종상품.append(item)

    최종가격 = [int(i['lprice']) for i in 최종상품]
    최종정렬 = sorted(최종상품, key=lambda x: int(x['lprice']))

    print(f"===== {상품명} 가격 분석 =====")
    print(f"최저가: {min(최종가격):,}원")
    print(f"최고가: {max(최종가격):,}원")
    print(f"평균가: {sum(최종가격)//len(최종가격):,}원")
    print(f"정상 상품 수: {len(최종상품)}개")
    print()
    print("=== 추천 상품 TOP 5 ===")
    for item in 최종정렬[:5]:
        print(f"- {item['title'][:25]} | {int(item['lprice']):,}원 | {item['mallName']}")
    print()
    print(f"=== 제외된 상품 ({len(제외목록)}개) ===")
    for 제외 in 제외목록[:5]:
        print(f"  ✕ {제외}")

최저가검색("에어팟")