import requests
import json
import os
import time
import schedule
from datetime import datetime

NAVER_CLIENT_ID = "NmoPGi9LLT1pbGFRCQ45"
NAVER_CLIENT_SECRET = "Z60X30C0Li"
DOMEGGOOK_API_KEY = "92b80f385760c74d150e84292746cfd7"
TELEGRAM_TOKEN = "8797313748:AAFodzMuWNEBGLPnYIs4GgjcU3WJs-Sd3Bo"
CHAT_ID = "6943475461"

재고파일 = "재고모니터링.json"

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    params = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        res = requests.post(url, params=params)
        return res.json()
    except Exception as e:
        print(f"텔레그램 전송 실패: {e}")
        return None

def 도매꾹상품조회(상품번호):
    url = "https://domeggook.com/ssl/api/"
    params = {
        "ver": "4.1",
        "mode": "getItemList",
        "aid": DOMEGGOOK_API_KEY,
        "market": "dome",
        "om": "json",
        "itemNo": 상품번호,
        "dfos": "false"
    }
    try:
        response = requests.get(url, params=params)
        data = response.json()
        items = data['domeggook']['list']['item']
        if isinstance(items, dict):
            items = [items]
        return items[0] if items else None
    except:
        return None

def 재고목록불러오기():
    if not os.path.exists(재고파일):
        return []
    with open(재고파일, 'r', encoding='utf-8') as f:
        return json.load(f)

def 재고목록저장(목록):
    with open(재고파일, 'w', encoding='utf-8') as f:
        json.dump(목록, f, ensure_ascii=False, indent=2)

def 상품등록(상품번호, 상품명):
    목록 = 재고목록불러오기()
    for s in 목록:
        if s['상품번호'] == 상품번호:
            print(f"⚠️ 이미 등록된 상품이에요!")
            return

    print(f"🔍 상품 번호 {상품번호} 조회 중...")
    item = 도매꾹상품조회(상품번호)

    목록.append({
        "상품번호": 상품번호,
        "상품명": 상품명,
        "등록일시": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "마지막체크": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "상태": "판매중",
        "링크": f"http://domeggook.com/{상품번호}"
    })
    재고목록저장(목록)
    print(f"✅ '{상품명}' 재고 모니터링 등록 완료!")
    send_telegram(f"📦 <b>재고 모니터링 등록!</b>\n상품명: {상품명}\n상품번호: {상품번호}\n지금부터 품절 여부를 감시합니다!")

def 재고체크():
    목록 = 재고목록불러오기()
    if not 목록:
        return

    now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
    print(f"\n[{now_str}] 재고 체크 시작...")

    for i, 상품 in enumerate(목록):
        item = 도매꾹상품조회(상품['상품번호'])
        이전상태 = 상품['상태']

        if item is None:
            새상태 = "품절/삭제"
        else:
            새상태 = "판매중"

        목록[i]['마지막체크'] = now_str
        목록[i]['상태'] = 새상태

        if 이전상태 != 새상태:
            if 새상태 == "품절/삭제":
                msg = f"🚨 <b>품절/삭제 알림!</b>\n상품명: {상품['상품명']}\n상품번호: {상품['상품번호']}\n⚠️ 공급처에서 상품이 품절되었어요!\n🔗 {상품['링크']}"
                print(f"  🚨 품절: {상품['상품명']}")
            else:
                msg = f"✅ <b>재입고 알림!</b>\n상품명: {상품['상품명']}\n상품번호: {상품['상품번호']}\n🎉 품절됐던 상품이 다시 판매 중이에요!\n🔗 {상품['링크']}"
                print(f"  ✅ 재입고: {상품['상품명']}")
            send_telegram(msg)
        else:
            print(f"  ✅ 정상: {상품['상품명']} ({새상태})")

    재고목록저장(목록)

def 목록보기():
    목록 = 재고목록불러오기()
    if not 목록:
        print("\n등록된 상품이 없습니다.")
        return

    print(f"\n{'='*50}")
    print(f"  📦 재고 모니터링 목록 ({len(목록)}개)")
    print(f"{'='*50}")
    for i, s in enumerate(목록, 1):
        상태아이콘 = "✅" if s['상태'] == "판매중" else "🚨"
        print(f"  {i}. {상태아이콘} {s['상품명']}")
        print(f"     상품번호: {s['상품번호']} | 상태: {s['상태']}")
        print(f"     마지막체크: {s['마지막체크']}")

def 자동모니터링():
    print(f"\n{'='*50}")
    print(f"  ⏰ 재고 자동 모니터링 시작!")
    print(f"  2시간마다 품절 여부를 체크합니다.")
    print(f"{'='*50}")
    send_telegram("📦 <b>재고 모니터링 시작!</b>\n2시간마다 품절 여부를 체크합니다.")
    재고체크()
    schedule.every(2).hours.do(재고체크)
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)
    except KeyboardInterrupt:
        send_telegram("⚠️ <b>재고 모니터링 중단!</b>\n다시 실행해주세요.")
        print("\n모니터링 중단!")

if __name__ == "__main__":
    while True:
        print("\n" + "="*50)
        print("  📦 재고/품절 알림 모니터링")
        print("="*50)
        print("  1. 상품 등록 (도매꾹 상품번호로)")
        print("  2. 모니터링 목록 보기")
        print("  3. 지금 바로 재고 체크")
        print("  4. 자동 모니터링 시작 (2시간마다)")
        print("  5. 종료")
        print("="*50)

        선택 = input("  번호를 입력하세요: ")

        if 선택 == "1":
            번호 = input("  도매꾹 상품번호: ")
            이름 = input("  상품명: ")
            상품등록(번호, 이름)
        elif 선택 == "2":
            목록보기()
        elif 선택 == "3":
            재고체크()
        elif 선택 == "4":
            자동모니터링()
        elif 선택 == "5":
            print("  종료합니다.")
            break
