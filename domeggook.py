import requests

DOMEGGOOK_API_KEY = "92b80f385760c74d150e84292746cfd7"

def 도매꾹검색(검색어, 개수=20):
    url = "https://domeggook.com/ssl/api/"
    params = {
        "ver": "4.1",
        "mode": "getItemList",
        "aid": DOMEGGOOK_API_KEY,
        "market": "dome",
        "om": "json",
        "kw": 검색어,
        "sz": 개수,
        "pg": 1,
        "so": "aa",
        "dfos": "false"
    }
    response = requests.get(url, params=params)
    return response.json()

def 도매꾹가격검색(검색어):
    print(f"\n🔍 도매꾹에서 '{검색어}' 검색 중...")
    data = 도매꾹검색(검색어)

    # 응답 구조: data['domeggook']['list']['item']
    try:
        items = data['domeggook']['list']['item']
    except (KeyError, TypeError):
        print("검색 결과가 없습니다.")
        return []

    # 단일 상품일 경우 리스트로 변환
    if isinstance(items, dict):
        items = [items]

    상품목록 = []
    for item in items:
        가격 = int(item.get('price', 0))
        배송구분 = item.get('deli', {}).get('who', '')
        배송비 = int(item.get('deli', {}).get('fee', 0) or 0)
        if 배송구분 == 'S':
            배송비 = 0

        상품목록.append({
            "제목": item.get('title', ''),
            "가격": 가격,
            "배송비": 배송비,
            "총가격": 가격 + 배송비,
            "판매자": item.get('nick', item.get('id', '')),
            "최소수량": item.get('unitQty', 1),
            "링크": item.get('url', ''),
            "출처": "도매꾹"
        })

    if not 상품목록:
        print("검색 결과가 없습니다.")
        return []

    정렬상품 = sorted(상품목록, key=lambda x: x['총가격'])

    print(f"\n{'='*50}")
    print(f"  🏪 도매꾹 '{검색어}' 검색 결과")
    print(f"{'='*50}")
    print(f"  수집 상품 수: {len(상품목록)}개")
    print(f"  최저가: {정렬상품[0]['총가격']:,}원 (배송비포함)")
    print(f"\n  🏆 최저가 TOP 5")
    print(f"  {'─'*40}")
    for i, s in enumerate(정렬상품[:5], 1):
        배송표시 = "무료배송" if s['배송비'] == 0 else f"배송비 {s['배송비']:,}원"
        print(f"  {i}. {s['제목'][:30]}")
        print(f"     💰 {s['가격']:,}원 | {배송표시} | 최소 {s['최소수량']}개")
        print(f"     🔗 {s['링크']}")

    return 정렬상품

if __name__ == "__main__":
    검색어 = input("검색할 상품명: ")
    도매꾹가격검색(검색어)