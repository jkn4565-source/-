import requests
from datetime import datetime

CLIENT_ID = "NmoPGi9LLT1pbGFRCQ45"
CLIENT_SECRET = "Z60X30C0Li"

def 경쟁강도분석(상품명):
    url = "https://openapi.naver.com/v1/search/shop.json"
    headers = {
        "X-Naver-Client-Id": CLIENT_ID,
        "X-Naver-Client-Secret": CLIENT_SECRET
    }
    params = {"query": 상품명, "sort": "sim", "display": 100}
    response = requests.get(url, headers=headers, params=params)
    data = response.json()

    전체상품수 = data.get('total', 0)
    상품목록 = data.get('items', [])
    쇼핑몰목록 = {}
    가격목록 = []
    국내상품 = []
    해외키워드 = ['직구', '해외', '구매대행', 'USA', '중국', '헤외', '면세']

    for item in 상품목록:
        가격 = int(item['lprice'])
        제목 = item['title'].replace('<b>', '').replace('</b>', '')
        쇼핑몰 = item['mallName']
        if 가격 <= 100:
            continue
        if any(k in 제목 or k in 쇼핑몰 for k in 해외키워드):
            continue
        국내상품.append(item)
        가격목록.append(가격)
        if 쇼핑몰 not in 쇼핑몰목록:
            쇼핑몰목록[쇼핑몰] = 0
        쇼핑몰목록[쇼핑몰] += 1

    if not 국내상품:
        print("분석할 상품이 없습니다.")
        return

    평균가 = sum(가격목록) // len(가격목록)
    최저가 = min(가격목록)
    최고가 = max(가격목록)
    가격차이 = 최고가 - 최저가
    판매자수 = len(쇼핑몰목록)

    if 전체상품수 >= 50000:
        경쟁등급 = "🔴 매우 치열"
        경쟁점수 = 5
    elif 전체상품수 >= 10000:
        경쟁등급 = "🟠 치열"
        경쟁점수 = 4
    elif 전체상품수 >= 3000:
        경쟁등급 = "🟡 보통"
        경쟁점수 = 3
    elif 전체상품수 >= 500:
        경쟁등급 = "🟢 낮음"
        경쟁점수 = 2
    else:
        경쟁등급 = "💎 블루오션"
        경쟁점수 = 1

    가격범위비율 = (가격차이 / 평균가) * 100
    if 가격범위비율 > 100:
        마진가능성 = "높음 (가격 차이가 커서 마진 여지 있음)"
    elif 가격범위비율 > 50:
        마진가능성 = "보통"
    else:
        마진가능성 = "낮음 (가격이 촘촘해서 마진 내기 어려움)"

    print(f"\n{'='*45}")
    print(f"  🔍 {상품명} 경쟁강도 분석")
    print(f"  📅 {datetime.now().strftime('%Y년 %m월 %d일 %H시')} 기준")
    print(f"{'='*45}")
    print(f"  네이버 전체 상품 수  : {전체상품수:,}개")
    print(f"  국내 판매자 수       : {판매자수}개")
    print(f"{'='*45}")
    print(f"  경쟁강도   : {경쟁등급}")
    print(f"  최저가     : {최저가:,}원")
    print(f"  평균가     : {평균가:,}원")
    print(f"  최고가     : {최고가:,}원")
    print(f"  마진가능성 : {마진가능성}")
    print(f"{'='*45}")
    print(f"  📦 주요 판매자 TOP 5")
    print(f"  {'─'*35}")
    정렬판매자 = sorted(쇼핑몰목록.items(), key=lambda x: x[1], reverse=True)
    for 쇼핑몰, 수량 in 정렬판매자[:5]:
        바 = "█" * 수량
        print(f"  {쇼핑몰:15} {바[:15]:15} {수량}개")
    print(f"\n{'='*45}")
    if 경쟁점수 <= 2:
        print(f"  ✅ 추천! 경쟁이 적어 진입하기 좋아요!")
    elif 경쟁점수 == 3:
        print(f"  🤔 신중하게! 차별화 전략이 필요해요")
    else:
        print(f"  ⚠️  경쟁이 치열해요. 다른 상품을 찾아보세요")
    print(f"{'='*45}\n")

if __name__ == "__main__":
    while True:
        검색어 = input("경쟁강도 분석할 상품명 (종료: q): ")
        if 검색어.lower() == 'q':
            break
        경쟁강도분석(검색어)