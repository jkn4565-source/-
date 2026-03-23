import requests
import time
from datetime import datetime

NAVER_CLIENT_ID = "NmoPGi9LLT1pbGFRCQ45"
NAVER_CLIENT_SECRET = "Z60X30C0Li"
TELEGRAM_TOKEN = "8797313748:AAFodzMuWNEBGLPnYIs4GgjcU3WJs-Sd3Bo"
TELEGRAM_CHAT_ID = "6943475461"

# 탐지할 키워드 목록 (원하는 키워드 추가 가능)
키워드목록 = [
    "아기방수턱받이", "실리콘이유식용기", "유아치발기세트",
    "캠핑랜턴고리", "텐트팩가방", "캠핑수저세트",
    "무선충전거치대차량용", "케이블클립정리", "노트북파우치14인치",
    "고양이해먹", "강아지이동가방", "반려동물물병",
    "주방서랍정리함", "냉장고정리용기", "싱크대수납",
    "욕실선반흡착", "칫솔살균기", "면도기거치대",
    "독서대접이식", "태블릿거치대침대"
]

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    params = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        requests.post(url, params=params)
    except:
        pass

def 네이버검색(상품명, 개수=10):
    url = "https://openapi.naver.com/v1/search/shop.json"
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
    }
    params = {"query": 상품명, "sort": "sim", "display": 개수}
    try:
        return requests.get(url, headers=headers, params=params).json()
    except:
        return {}

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
        return None  # 경쟁 높으면 패스

    return {
        "키워드": 키워드,
        "전체상품수": 전체상품수,
        "평균가": 평균가,
        "최저가": 최저가,
        "등급": 등급
    }

def 전체탐지():
    print(f"\n{'='*50}")
    print(f"  💎 블루오션 탐지 시작")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}")

    발견목록 = []
    for i, 키워드 in enumerate(키워드목록, 1):
        print(f"  [{i}/{len(키워드목록)}] {키워드} 분석 중...")
        결과 = 블루오션탐지(키워드)
        if 결과:
            발견목록.append(결과)
            print(f"  {결과['등급']} 발견! 상품수: {결과['전체상품수']:,}개")
        time.sleep(0.5)  # API 과부하 방지

    if 발견목록:
        발견목록.sort(key=lambda x: x['전체상품수'])
        메시지 = f"💎 <b>블루오션 상품 발견!</b>\n"
        메시지 += f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        for r in 발견목록[:5]:  # 상위 5개만
            메시지 += f"{r['등급']} <b>{r['키워드']}</b>\n"
            메시지 += f"  상품수: {r['전체상품수']:,}개\n"
            메시지 += f"  평균가: {r['평균가']:,}원\n"
            메시지 += f"  최저가: {r['최저가']:,}원\n\n"
        send_telegram(메시지)
        print(f"\n  ✅ 텔레그램 알림 전송 완료! ({len(발견목록)}개 발견)")
    else:
        print(f"\n  ℹ️ 블루오션 상품 없음")

    return 발견목록

if __name__ == "__main__":
    while True:
        print("\n" + "="*50)
        print("  💎 블루오션 자동 탐지기")
        print("="*50)
        print("  1. 지금 바로 탐지하기")
        print("  2. 자동 탐지 (3시간마다)")
        print("  3. 키워드 추가")
        print("  4. 종료")
        print("="*50)

        선택 = input("  번호: ")

        if 선택 == "1":
            전체탐지()

        elif 선택 == "2":
            print("  ✅ 3시간마다 자동 탐지 시작! (Ctrl+C로 종료)")
            send_telegram("💎 <b>블루오션 자동 탐지 시작!</b>\n3시간마다 체크할게요!")
            while True:
                전체탐지()
                print(f"\n  ⏰ 3시간 후 다시 탐지합니다...")
                time.sleep(10800)

        elif 선택 == "3":
            새키워드 = input("  추가할 키워드: ")
            키워드목록.append(새키워드.strip())
            print(f"  ✅ '{새키워드}' 추가 완료!")

        elif 선택 == "4":
            print("  종료합니다.")
            break
