import requests

CLIENT_ID = "NmoPGi9LLT1pbGFRCQ45"
CLIENT_SECRET = "Z60X30C0Li"

def 상품검색(상품명, 배송비=0):
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
        제목 = item['title'].replace('<b>', '').replace('</b>', '')
        쇼핑몰 = item['mallName']

        if 가격 <= 100:
            continue

        해외키워드 = ['직구', '해외', '구매대행', 'USA', '중국', '헤외', '면세']
        if any(k in 제목 or k in 쇼핑몰 for k in 해외키워드):
            제외목록.append(f"해외배송: {제목[:20]}")
            continue

        필터상품.append({
            "제목": 제목,
            "가격": 가격,
            "총가격": 가격 + 배송비,
            "쇼핑몰": 쇼핑몰,
            "링크": item['link']
        })

    if not 필터상품:
        print("조건에 맞는 상품이 없습니다.")
        return None

    가격목록 = [i['가격'] for i in 필터상품]
    평균가 = sum(가격목록) // len(가격목록)

    최종상품 = []
    for item in 필터상품:
        if item['가격'] < 평균가 * 0.3:
            제외목록.append(f"미끼상품: {item['제목'][:20]}")
            continue
        최종상품.append(item)

    if not 최종상품:
        print("필터 후 상품이 없습니다.")
        return None

    최종정렬 = sorted(최종상품, key=lambda x: x['총가격'])

    결과 = {
        "상품명": 상품명,
        "최저가": min(i['총가격'] for i in 최종상품),
        "평균가": sum(i['총가격'] for i in 최종상품) // len(최종상품),
        "상품수": len(최종상품),
        "제외수": len(제외목록),
        "추천상품": 최종정렬[:5]
    }
    return 결과

def 결과출력(결과):
    if not 결과:
        return
    print(f"\n{'='*45}")
    print(f"  {결과['상품명']} 검색 결과")
    print(f"{'='*45}")
    print(f"  최저가 (배송비포함): {결과['최저가']:,}원")
    print(f"  평균가 (배송비포함): {결과['평균가']:,}원")
    print(f"  정상상품: {결과['상품수']}개 | 제외: {결과['제외수']}개")
    print(f"{'='*45}")
    print("  추천 상품 TOP 5")
    print(f"{'='*45}")
    for i, item in enumerate(결과['추천상품'], 1):
        print(f"  {i}. {item['제목'][:28]}")
        print(f"     {int(item['총가격']):,}원 | {item['쇼핑몰']}")
        print(f"     {item['링크']}")
    print()

if __name__ == "__main__":
    while True:
        검색어 = input("검색할 상품명 (종료: q): ")
        if 검색어.lower() == 'q':
            break
        배송비 = input("배송비 (없으면 0): ")
        결과 = 상품검색(검색어, int(배송비) if 배송비 else 0)
        결과출력(결과)