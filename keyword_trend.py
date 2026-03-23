import requests
import json
import hashlib
import hmac
import base64
import time
from datetime import datetime, timedelta

NAVER_CLIENT_ID = "NmoPGi9LLT1pbGFRCQ45"
NAVER_CLIENT_SECRET = "Z60X30C0Li"
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

def 광고API헤더생성(method, uri):
    timestamp = str(int(time.time() * 1000))
    message = f"{timestamp}.{method}.{uri}"
    hash = hmac.new(
        NAVER_AD_SECRET_KEY.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256
    )
    signature = base64.b64encode(hash.digest()).decode("utf-8")
    return {
        "Content-Type": "application/json; charset=UTF-8",
        "X-Timestamp": timestamp,
        "X-API-KEY": NAVER_AD_ACCESS_LICENSE,
        "X-Customer": NAVER_AD_CUSTOMER_ID,
        "X-Signature": signature
    }

def 해시태그추천(키워드):
    uri = "/keywordstool"
    url = f"https://api.naver.com{uri}"
    headers = 광고API헤더생성("GET", uri)
    params = {"hintKeywords": 키워드, "showDetail": 1}
    try:
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        키워드목록 = data.get('keywordList', [])
        if not 키워드목록:
            return [f"#{키워드}", f"#{키워드}추천", f"#{키워드}쇼핑",
                    f"#{키워드}코디", f"#{키워드}할인", f"#여름{키워드}",
                    f"#{키워드}구매", f"#{키워드}후기"]
        정렬목록 = sorted(
            키워드목록,
            key=lambda x: 검색량변환(x.get('monthlyPcQcCnt', 0)) + 검색량변환(x.get('monthlyMobileQcCnt', 0)),
            reverse=True
        )
        return [f"#{item['relKeyword']}" for item in 정렬목록[:8]]
    except Exception as e:
        print(f"광고 API 오류: {e}")
        return [f"#{키워드}", f"#{키워드}추천", f"#{키워드}쇼핑",
                f"#{키워드}코디", f"#{키워드}할인", f"#여름{키워드}",
                f"#{키워드}구매", f"#{키워드}후기"]

def 네이버검색량조회(키워드목록):
    url = "https://openapi.naver.com/v1/datalab/search"
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
        "Content-Type": "application/json"
    }
    오늘 = datetime.now()
    한달전 = 오늘 - timedelta(days=30)
    keywordGroups = [{"groupName": kw, "keywords": [kw]} for kw in 키워드목록[:5]]
    body = {
        "startDate": 한달전.strftime("%Y-%m-%d"),
        "endDate": 오늘.strftime("%Y-%m-%d"),
        "timeUnit": "week",
        "keywordGroups": keywordGroups
    }
    response = requests.post(url, headers=headers, data=json.dumps(body))
    return response.json()

def 쇼핑키워드트렌드(키워드목록):
    url = "https://openapi.naver.com/v1/datalab/shopping/keywords"
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
        "Content-Type": "application/json"
    }
    오늘 = datetime.now()
    한달전 = 오늘 - timedelta(days=30)
    keywordGroups = [{"groupName": kw, "keywords": [kw]} for kw in 키워드목록[:5]]
    body = {
        "startDate": 한달전.strftime("%Y-%m-%d"),
        "endDate": 오늘.strftime("%Y-%m-%d"),
        "timeUnit": "week",
        "keywordGroups": keywordGroups,
        "device": "", "ages": [], "gender": ""
    }
    response = requests.post(url, headers=headers, data=json.dumps(body))
    return response.json()

def 트렌드분석(키워드목록):
    print(f"\n{'='*55}")
    print(f"  🔥 트렌드 키워드 분석")
    print(f"{'='*55}")

    print("\n📊 통합 검색량 트렌드 (최근 4주)")
    data = 네이버검색량조회(키워드목록)

    if 'results' not in data:
        print("데이터 없음:", data)
        return

    결과목록 = []
    for result in data['results']:
        키워드 = result['title']
        데이터 = result['data']
        if not 데이터:
            continue
        최근값 = 데이터[-1]['ratio'] if 데이터 else 0
        이전값 = 데이터[-2]['ratio'] if len(데이터) >= 2 else 최근값
        변화율 = ((최근값 - 이전값) / 이전값 * 100) if 이전값 > 0 else 0
        결과목록.append({
            "키워드": 키워드,
            "최근검색량": 최근값,
            "변화율": round(변화율, 1),
            "트렌드": "🔥 급상승" if 변화율 > 20 else "📈 상승" if 변화율 > 0 else "📉 하락"
        })

    결과목록.sort(key=lambda x: x['최근검색량'], reverse=True)
    print(f"\n  {'키워드':<15} {'최근검색량':>10} {'변화율':>8} {'트렌드'}")
    print(f"  {'─'*50}")
    for r in 결과목록:
        print(f"  {r['키워드']:<15} {r['최근검색량']:>10.1f} {r['변화율']:>7.1f}% {r['트렌드']}")

    print("\n\n🛒 쇼핑 검색량 트렌드")
    shop_data = 쇼핑키워드트렌드(키워드목록)
    if 'results' in shop_data:
        쇼핑결과 = []
        for result in shop_data['results']:
            키워드 = result['title']
            데이터 = result['data']
            if not 데이터:
                continue
            최근값 = 데이터[-1]['ratio'] if 데이터 else 0
            이전값 = 데이터[-2]['ratio'] if len(데이터) >= 2 else 최근값
            변화율 = ((최근값 - 이전값) / 이전값 * 100) if 이전값 > 0 else 0
            쇼핑결과.append({
                "키워드": 키워드,
                "쇼핑검색량": 최근값,
                "변화율": round(변화율, 1),
                "트렌드": "🔥 급상승" if 변화율 > 20 else "📈 상승" if 변화율 > 0 else "📉 하락"
            })
        쇼핑결과.sort(key=lambda x: x['쇼핑검색량'], reverse=True)
        print(f"\n  {'키워드':<15} {'쇼핑검색량':>10} {'변화율':>8} {'트렌드'}")
        print(f"  {'─'*50}")
        for r in 쇼핑결과:
            print(f"  {r['키워드']:<15} {r['쇼핑검색량']:>10.1f} {r['변화율']:>7.1f}% {r['트렌드']}")

    print(f"\n\n🏷️ 키워드별 추천 해시태그 (실제 검색량 순)")
    print(f"  {'─'*50}")
    for r in 결과목록:
        tags = 해시태그추천(r['키워드'])
        print(f"\n  {r['트렌드']} {r['키워드']}")
        print(f"  {' '.join(tags)}")

    return 결과목록

키워드묶음 = {
    "여름 패션": ["수영복", "반바지", "샌들", "선글라스", "비키니"],
    "여름 용품": ["선크림", "물놀이", "아이스팩", "휴대용선풍기", "모기장"],
    "육아용품": ["유아식판", "젖병", "기저귀", "유모차", "아기욕조"],
    "주방용품": ["에어프라이어", "텀블러", "도시락통", "냄비", "프라이팬"],
    "인테리어": ["캔들", "무드등", "화분", "쿠션", "러그"],
    "직접입력": []
}

if __name__ == "__main__":
    while True:
        print("\n" + "="*55)
        print("  🔥 트렌드 키워드 분석기")
        print("="*55)
        print("  1. 키워드 묶음으로 분석")
        print("  2. 직접 키워드 입력")
        print("  3. 종료")
        print("="*55)
        선택 = input("  번호: ")
        if 선택 == "1":
            print("\n  키워드 묶음 선택:")
            목록 = list(키워드묶음.keys())
            for i, k in enumerate(목록[:-1], 1):
                print(f"  {i}. {k}: {키워드묶음[k]}")
            번호 = int(input("  번호: ")) - 1
            선택키워드 = 키워드묶음[목록[번호]]
            트렌드분석(선택키워드)
        elif 선택 == "2":
            print("  분석할 키워드를 쉼표로 구분해서 입력하세요")
            print("  (최대 5개, 예: 수영복,선크림,샌들,비키니,물놀이)")
            입력 = input("  키워드: ")
            키워드목록 = [k.strip() for k in 입력.split(",")][:5]
            트렌드분석(키워드목록)
        elif 선택 == "3":
            print("  종료합니다.")
            break
