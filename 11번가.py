import requests
import xml.etree.ElementTree as ET

ELEVENST_API_KEY = "2d88124f88de34180fd7a6f3e1736988"

def 검색_11번가(검색어, 개수=20):
    url = "http://openapi.11st.co.kr/openapi/OpenApiService.tmall"
    params = {
        "key": ELEVENST_API_KEY,
        "apiCode": "ProductSearch",
        "keyword": 검색어,
        "pageSize": 개수,
        "pageNum": 1,
        "sortCd": "20",
    }
    response = requests.get(url, params=params)
    
    # EUC-KR 인코딩으로 디코딩
    content = response.content.decode('euc-kr', errors='ignore')

    try:
        root = ET.fromstring(content)
        상품목록 = []

        for item in root.findall('.//Product'):
            제목 = item.findtext('ProductName', '')
            가격 = item.findtext('SalePrice', '0') or item.findtext('Price', '0')
            배송비텍스트 = item.findtext('DeliveryFee', '0')
            링크 = item.findtext('DetailPageUrl', '')
            쇼핑몰 = item.findtext('SellerNick', '')

            try:
                가격 = int(str(가격).replace(',', '').strip())
                배송비 = int(str(배송비텍스트).replace(',', '').strip()) if 배송비텍스트 else 0
            except:
                계속 = True
                continue

            if 가격 <= 0:
                continue

            상품목록.append({
                "제목": 제목,
                "가격": 가격,
                "배송비": 배송비,
                "총가격": 가격 + 배송비,
                "쇼핑몰": "11번가",
                "링크": 링크,
                "출처": "11번가"
            })

        return sorted(상품목록, key=lambda x: x['총가격'])

    except Exception as e:
        print("오류:", e)
        print("응답:", content[:500])
        return []

def 가격검색_11번가(검색어):
    print(f"\n🔍 11번가에서 '{검색어}' 검색 중...")
    결과 = 검색_11번가(검색어)

    if not 결과:
        print("검색 결과가 없습니다.")
        return []

    print(f"\n{'='*50}")
    print(f"  🏪 11번가 '{검색어}' 검색 결과")
    print(f"{'='*50}")
    print(f"  수집 상품 수: {len(결과)}개")
    print(f"  최저가: {결과[0]['총가격']:,}원 (배송비포함)")
    print(f"\n  🏆 최저가 TOP 5")
    print(f"  {'─'*40}")
    for i, s in enumerate(결과[:5], 1):
        배송표시 = "무료배송" if s['배송비'] == 0 else f"배송비 {s['배송비']:,}원"
        print(f"  {i}. {s['제목'][:30]}")
        print(f"     💰 {s['가격']:,}원 | {배송표시}")
        print(f"     🔗 {s['링크']}")

    return 결과

if __name__ == "__main__":
    검색어 = input("검색할 상품명: ")
    가격검색_11번가(검색어)