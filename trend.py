import requests
import json
from datetime import datetime, timedelta

CLIENT_ID = "NmoPGi9LLT1pbGFRCQ45"
CLIENT_SECRET = "Z60X30C0Li"

def 인기검색어조회(카테고리선택):
    url = "https://openapi.naver.com/v1/datalab/shopping/categories"
    headers = {
        "X-Naver-Client-Id": CLIENT_ID,
        "X-Naver-Client-Secret": CLIENT_SECRET,
        "Content-Type": "application/json"
    }
    오늘 = datetime.now()
    한달전 = 오늘 - timedelta(days=30)

    카테고리맵 = {
        "1": {"name": "패션의류", "param": ["50000000"]},
        "2": {"name": "패션잡화", "param": ["50000001"]},
        "3": {"name": "디지털/가전", "param": ["50000003"]},
        "4": {"name": "출산/육아", "param": ["50000004"]},
        "5": {"name": "식품", "param": ["50000006"]},
        "6": {"name": "화장품/미용", "param": ["50000008"]},
    }

    선택된카테고리 = [카테고리맵[k] for k in 카테고리선택 if k in 카테고리맵]

    if not 선택된카테고리:
        print("올바른 카테고리를 선택해주세요.")
        return

    body = {
        "startDate": 한달전.strftime("%Y-%m-%d"),
        "endDate": 오늘.strftime("%Y-%m-%d"),
        "timeUnit": "date",
        "category": 선택된카테고리[:3]
    }

    response = requests.post(url, headers=headers, data=json.dumps(body))
    data = response.json()

    if 'results' not in data:
        print("❌ API 오류:", data)
        return

    print(f"\n{'='*45}")
    print(f"  📊 네이버 쇼핑 분야별 트렌드")
    print(f"  📅 최근 30일 기준")
    print(f"{'='*45}")
    for result in data['results']:
        데이터 = result['data']
        최근값 = 데이터[-1]['ratio'] if 데이터 else 0
        바 = "█" * int(최근값 / 10)
        print(f"  {result['title']:12} {바:10} {최근값:.1f}점")
    print(f"\n  💡 점수가 높을수록 요즘 많이 검색되는 분야예요!")

def 오늘인기상품():
    인기검색어목록 = [
        "트위드자켓", "원피스", "트렌치코트", "바람막이",
        "블라우스", "무선이어폰", "텀블러", "청바지"
    ]
    print(f"\n{'='*45}")
    print(f"  🔥 오늘의 인기 검색어 가격 현황")
    print(f"  📅 {datetime.now().strftime('%Y년 %m월 %d일')} 기준")
    print(f"{'='*45}")
    url = "https://openapi.naver.com/v1/search/shop.json"
    headers = {
        "X-Naver-Client-Id": CLIENT_ID,
        "X-Naver-Client-Secret": CLIENT_SECRET
    }
    for 검색어 in 인기검색어목록:
        params = {"query": 검색어, "sort": "sim", "display": 20}
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        가격목록 = []
        for item in data.get('items', []):
            가격 = int(item['lprice'])
            if 가격 > 100:
                가격목록.append(가격)
        if 가격목록:
            평균가 = sum(가격목록) // len(가격목록)
            최저가 = min(가격목록)
            print(f"  🔍 {검색어:12} 최저 {최저가:>8,}원 | 평균 {평균가:>8,}원")
    print(f"\n  💡 이 중에 마진이 남는 상품을 골라보세요!")

if __name__ == "__main__":
    while True:
        print("\n" + "="*45)
        print("  🔥 트렌드 분석 프로그램")
        print("="*45)
        print("  1. 분야별 트렌드 보기")
        print("  2. 오늘 인기 검색어 가격 보기")
        print("  3. 종료")
        print("="*45)
        선택 = input("  번호를 입력하세요: ")
        if 선택 == "1":
            print("\n  카테고리 선택 (최대 3개, 쉼표로 구분)")
            print("  1.패션의류 2.패션잡화 3.디지털/가전")
            print("  4.출산/육아 5.식품 6.화장품/미용")
            카테고리 = input("  번호 입력 (예: 1,3,4): ").split(",")
            인기검색어조회(카테고리)
        elif 선택 == "2":
            오늘인기상품()
        elif 선택 == "3":
            print("  프로그램을 종료합니다.")
            break
        else:
            print("  1, 2, 3 중에 입력해주세요!")