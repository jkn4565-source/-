import requests
import json
import os
import time
import schedule
from datetime import datetime

# ==========================================
# 1. 텔레그램 및 네이버 설정
# ==========================================
NAVER_CLIENT_ID = "NmoPGi9LLT1pbGFRCQ45"
NAVER_CLIENT_SECRET = "Z60X30C0Li"

# 봇파더에게 받은 토큰을 입력했습니다.
TELEGRAM_TOKEN = "8797313748:AAFodzMuWNEBGLPnYIs4GgjcU3WJs-Sd3Bo"

# 여기에 @myidbot 등을 통해 확인한 본인의 숫자 ID를 입력하세요.
CHAT_ID = "6943475461" 

관심상품파일 = "관심상품.json"

def send_telegram(text):
    """텔레그램 메시지 전송 함수"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    params = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        res = requests.post(url, params=params)
        return res.json()
    except Exception as e:
        print(f"텔레그램 전송 실패: {e}")
        return None

def 네이버검색(상품명, 개수=20):
    url = "https://openapi.naver.com/v1/search/shop.json"
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
    }
    params = {"query": 상품명, "sort": "sim", "display": 개수}
    response = requests.get(url, headers=headers, params=params)
    return response.json()

def 현재최저가조회(상품명):
    data = 네이버검색(상품명)
    가격목록 = []
    for item in data.get('items', []):
        가격 = int(item['lprice'])
        if 가격 <= 100: continue
        해외키워드 = ['직구', '해외', '구매대행', 'USA', '중국', '헤외', '면세']
        if any(k in item['title'] or k in item['mallName'] for k in 해외키워드): continue
        가격목록.append({
            "가격": 가격,
            "제목": item['title'].replace('<b>', '').replace('</b>', ''),
            "쇼핑몰": item['mallName'],
            "링크": item['link']
        })
    if not 가격목록: return None
    가격목록정렬 = sorted(가격목록, key=lambda x: x['가격'])
    return 가격목록정렬[0]

def 관심상품불러오기():
    if not os.path.exists(관심상품파일): return []
    with open(관심상품파일, 'r', encoding='utf-8') as f:
        return json.load(f)

def 관심상품저장(목록):
    with open(관심상품파일, 'w', encoding='utf-8') as f:
        json.dump(목록, f, ensure_ascii=False, indent=2)

def 가격체크():
    목록 = 관심상품불러오기()
    if not 목록: return

    now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
    print(f"\n[{now_str}] 가격 체크 시작...")
    
    변동있음 = []
    for i, 상품 in enumerate(목록):
        결과 = 현재최저가조회(상품['검색어'])
        if not 결과: continue

        새가격 = 결과['가격']
        이전가격 = 상품['현재가격']
        변동금액 = 새가격 - 이전가격

        if 변동금액 != 0:
            목록[i]['현재가격'] = 새가격
            목록[i]['마지막체크'] = now_str
            변동있음.append({
                "상품명": 상품['검색어'],
                "이전가격": 이전가격,
                "새가격": 새가격,
                "변동금액": 변동금액,
                "링크": 결과['링크']
            })

    if 변동있음:
        관심상품저장(목록)
        알림전송(변동있음)
    else:
        print("  ✅ 가격 변동 없음")

def 알림전송(변동목록):
    """변동 내역을 화면과 텔레그램으로 동시 알림"""
    for 항목 in 변동목록:
        변동 = 항목['변동금액']
        if 변동 > 0:
            msg = f"<b>🔴 [가격 상승 경고!]</b>\n상품명: {항목['상품명']}\n{항목['이전가격']:,}원 → <b>{항목['새가격']:,}원</b> (+{변동:,}원)\n⚠️ 공급처 가격 인상! 마진을 확인하세요."
        else:
            msg = f"<b>🔵 [가격 하락 알림]</b>\n상품명: {항목['상품명']}\n{항목['이전가격']:,}원 → <b>{항목['새가격']:,}원</b> ({변동:,}원)\n✅ 경쟁력이 확보되었습니다!"
        
        # 텔레그램 전송
        send_telegram(msg)
        send_telegram(f"🔗 링크: {항목['링크']}")
        print(f"  [알림] {항목['상품명']} 변동 보고 완료")

def 자동모니터링시작():
    print(f"\n{'='*45}")
    print(f"  ⏰ 실시간 모니터링 모드 가동!")
    print(f"  텔레그램 비서가 1시간마다 보고합니다.")
    print(f"{'='*45}")
    send_telegram("⏰ <b>자동 모니터링 시작!</b>\n1시간마다 가격을 체크합니다.")
    가격체크()
    schedule.every(1).hours.do(가격체크)
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)
    except KeyboardInterrupt:
        send_telegram("⚠️ <b>모니터링이 중단되었습니다!</b>\n프로그램이 종료되었어요. 다시 실행해주세요!")
        print("\n모니터링 중단 - 텔레그램으로 알림 전송 완료")
    except Exception as e:
        send_telegram(f"🚨 <b>오류로 모니터링 중단!</b>\n오류내용: {str(e)}\n다시 실행해주세요!")
        print(f"\n오류 발생: {e}")

if __name__ == "__main__":
    # 실행 시 테스트 메시지 전송 (연결 확인용)
    test_res = send_telegram("🤖 <b>가격 감시 비서가 연결되었습니다!</b>\n지금부터 실시간으로 보고하겠습니다.")
    if test_res and test_res.get('ok'):
        print("✅ 텔레그램 연결 성공!")
    else:
        print("⚠️ 텔레그램 연결 실패. CHAT_ID를 확인하세요.")

    while True:
        print("\n" + "="*45)
        print("  📋 관심상품 가격 모니터링 (Telegram Ver.)")
        print("="*45)
        print("  1. 관심상품 등록")
        print("  2. 관심상품 목록 보기")
        print("  3. 지금 바로 가격 체크")
        print("  4. 자동 모니터링 시작 (1시간마다)")
        print("  6. 종료")
        print("="*45)
        선택 = input("  번호를 입력하세요: ")
        if 선택 == "1":
            상품명 = input("  등록할 상품명: ")
            # (관심상품등록 로직 호출... 기존 코드 참조)
        elif 선택 == "3": 가격체크()
        elif 선택 == "4": 자동모니터링시작()
        elif 선택 == "6": break