import requests
import json

DOMEGGOOK_API_KEY = "92b80f385760c74d150e84292746cfd7"

def 도매꾹상품상세조회(상품번호):
    url = "https://domeggook.com/ssl/api/"
    params = {
        "ver": "4.1",
        "mode": "getItemDetail",
        "aid": DOMEGGOOK_API_KEY,
        "market": "dome",
        "om": "json",
        "no": 상품번호
    }
    try:
        response = requests.get(url, params=params)
        data = response.json()
        return data.get('domeggook', {})
    except Exception as e:
        print(f"오류: {e}")
        return None

def 스마트스토어형식변환(상품데이터):
    print("\n" + "="*60)
    print("  🏪 스마트스토어 상품 등록 형식")
    print("="*60)

    제목 = 상품데이터.get('title', '')
    가격 = 상품데이터.get('price', 0)
    배송비 = 상품데이터.get('deli', {}).get('fee', 3000)
    최소수량 = 상품데이터.get('unitQty', 1)
    이미지 = 상품데이터.get('thumb', '')

    # 판매가 자동 계산 (마진 30% 기준)
    매입가 = int(가격)
    배송비 = int(배송비) if 배송비 else 3000
    추천판매가 = int((매입가 + 배송비) / (1 - 0.055 - 0.036 - 0.30))

    print(f"""
📌 상품명 (스마트스토어용):
   {제목}

💰 가격 정보:
   - 도매꾹 매입가: {매입가:,}원
   - 배송비: {배송비:,}원
   - 추천 판매가 (마진 30%): {추천판매가:,}원
   - 최소 구매 수량: {최소수량}개

📦 배송 정보:
   - 배송방법: 택배
   - 배송비 조건: 유료 ({배송비:,}원)

🖼️ 대표 이미지:
   {이미지}

📋 스마트스토어 등록 시 필요한 정보:
   ✅ 상품명: {제목[:50]}
   ✅ 판매가: {추천판매가:,}원
   ✅ 재고수량: 999개 (위탁배송)
   ✅ 배송방법: 택배
   ✅ 배송비: {배송비:,}원
   ✅ 출고지: 공급업체 직배송
   ✅ 반품/교환지: 공급업체 동일
""")
    return {
        "상품명": 제목,
        "매입가": 매입가,
        "배송비": 배송비,
        "추천판매가": 추천판매가,
        "최소수량": 최소수량,
        "이미지": 이미지
    }

def 쿠팡형식변환(상품데이터):
    print("\n" + "="*60)
    print("  🛒 쿠팡 상품 등록 형식")
    print("="*60)

    제목 = 상품데이터.get('title', '')
    가격 = int(상품데이터.get('price', 0))
    배송비 = int(상품데이터.get('deli', {}).get('fee', 3000) or 3000)
    추천판매가 = int((가격 + 배송비) / (1 - 0.108 - 0.036 - 0.25))

    print(f"""
📌 상품명 (쿠팡용):
   {제목}

💰 가격 정보:
   - 도매꾹 매입가: {가격:,}원
   - 추천 판매가 (마진 25%): {추천판매가:,}원

📋 쿠팡 등록 시 필요한 정보:
   ✅ 상품명: {제목[:50]}
   ✅ 판매가: {추천판매가:,}원
   ✅ 로켓배송: X (일반배송)
   ✅ 배송비: 무료 (판매가에 포함)
   ✅ 재고: 위탁배송 (수량 제한 없음)
""")

def 상품등록도우미(상품번호):
    print(f"\n🔍 도매꾹 상품번호 {상품번호} 조회 중...")
    data = 도매꾹상품상세조회(상품번호)

    if not data:
        print("❌ 상품을 찾을 수 없어요.")
        return

    print(f"✅ 상품 조회 완료!")

    while True:
        print("\n" + "="*50)
        print("  🏪 어느 플랫폼에 등록할까요?")
        print("="*50)
        print("  1. 스마트스토어")
        print("  2. 쿠팡")
        print("  3. 전체 플랫폼")
        print("  4. 뒤로가기")
        print("="*50)

        선택 = input("  번호: ")

        if 선택 == "1":
            스마트스토어형식변환(data)
        elif 선택 == "2":
            쿠팡형식변환(data)
        elif 선택 == "3":
            스마트스토어형식변환(data)
            쿠팡형식변환(data)
        elif 선택 == "4":
            break

if __name__ == "__main__":
    while True:
        print("\n" + "="*50)
        print("  🏪 상품 등록 도우미")
        print("="*50)
        print("  도매꾹 상품번호를 입력하면")
        print("  스마트스토어/쿠팡 등록 형식으로")
        print("  자동 변환해드려요!")
        print("="*50)
        print("  1. 상품 등록 형식 변환")
        print("  2. 종료")
        print("="*50)

        선택 = input("  번호: ")

        if 선택 == "1":
            번호 = input("  도매꾹 상품번호: ")
            상품등록도우미(번호)
        elif 선택 == "2":
            print("  종료합니다.")
            break
