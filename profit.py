import json
import os
from datetime import datetime

장부파일 = "수익장부.json"

def 장부불러오기():
    if not os.path.exists(장부파일):
        return []
    with open(장부파일, 'r', encoding='utf-8') as f:
        return json.load(f)

def 장부저장(목록):
    with open(장부파일, 'w', encoding='utf-8') as f:
        json.dump(목록, f, ensure_ascii=False, indent=2)

def 판매등록():
    print("\n📝 판매 내역 등록")
    상품명 = input("  상품명: ")
    플랫폼 = input("  판매 플랫폼 (스마트스토어/쿠팡/G마켓/11번가): ")
    판매가 = int(input("  판매가 (원): "))
    매입가 = int(input("  매입가 (원): "))
    배송비 = int(input("  배송비 (원): "))
    수량 = int(input("  판매 수량: "))

    수수료율 = {"스마트스토어": 0.055, "쿠팡": 0.108, "G마켓": 0.12, "11번가": 0.09}
    수수료 = 수수료율.get(플랫폼, 0.055)

    총매출 = 판매가 * 수량
    총매입 = (매입가 + 배송비) * 수량
    플랫폼수수료 = 총매출 * 수수료
    결제수수료 = 총매출 * 0.036
    순이익 = 총매출 - 총매입 - 플랫폼수수료 - 결제수수료
    마진율 = round((순이익 / 총매출) * 100, 1)

    내역 = {
        "날짜": datetime.now().strftime("%Y-%m-%d"),
        "시간": datetime.now().strftime("%H:%M"),
        "상품명": 상품명,
        "플랫폼": 플랫폼,
        "판매가": 판매가,
        "매입가": 매입가,
        "배송비": 배송비,
        "수량": 수량,
        "총매출": 총매출,
        "총매입": 총매입,
        "플랫폼수수료": round(플랫폼수수료),
        "결제수수료": round(결제수수료),
        "순이익": round(순이익),
        "마진율": 마진율
    }

    목록 = 장부불러오기()
    목록.append(내역)
    장부저장(목록)

    print(f"\n✅ 등록 완료!")
    print(f"   총매출: {총매출:,}원")
    print(f"   순이익: {round(순이익):,}원 (마진율 {마진율}%)")

def 통계보기():
    목록 = 장부불러오기()
    if not 목록:
        print("\n등록된 판매 내역이 없습니다.")
        return

    오늘 = datetime.now().strftime("%Y-%m-%d")
    이번달 = datetime.now().strftime("%Y-%m")

    오늘내역 = [s for s in 목록 if s['날짜'] == 오늘]
    이번달내역 = [s for s in 목록 if s['날짜'].startswith(이번달)]

    print(f"\n{'='*55}")
    print(f"  📊 수익 통계")
    print(f"{'='*55}")

    print(f"\n  📅 오늘 ({오늘})")
    if 오늘내역:
        print(f"     판매 건수: {len(오늘내역)}건")
        print(f"     총 매출: {sum(s['총매출'] for s in 오늘내역):,}원")
        print(f"     순이익: {sum(s['순이익'] for s in 오늘내역):,}원")
    else:
        print(f"     오늘 판매 내역 없음")

    print(f"\n  📅 이번달 ({이번달})")
    if 이번달내역:
        print(f"     판매 건수: {len(이번달내역)}건")
        print(f"     총 매출: {sum(s['총매출'] for s in 이번달내역):,}원")
        print(f"     순이익: {sum(s['순이익'] for s in 이번달내역):,}원")
        평균마진 = sum(s['마진율'] for s in 이번달내역) / len(이번달내역)
        print(f"     평균 마진율: {평균마진:.1f}%")
    else:
        print(f"     이번달 판매 내역 없음")

    print(f"\n  📅 전체 누적")
    print(f"     총 판매 건수: {len(목록)}건")
    print(f"     총 매출: {sum(s['총매출'] for s in 목록):,}원")
    print(f"     총 순이익: {sum(s['순이익'] for s in 목록):,}원")

    print(f"\n  🏪 플랫폼별 매출")
    플랫폼통계 = {}
    for s in 목록:
        p = s['플랫폼']
        if p not in 플랫폼통계:
            플랫폼통계[p] = {"매출": 0, "순이익": 0, "건수": 0}
        플랫폼통계[p]["매출"] += s['총매출']
        플랫폼통계[p]["순이익"] += s['순이익']
        플랫폼통계[p]["건수"] += 1

    for p, v in 플랫폼통계.items():
        print(f"     {p}: {v['건수']}건 | 매출 {v['매출']:,}원 | 순이익 {v['순이익']:,}원")

def 내역보기():
    목록 = 장부불러오기()
    if not 목록:
        print("\n등록된 판매 내역이 없습니다.")
        return

    print(f"\n{'='*55}")
    print(f"  📋 전체 판매 내역 (최근 10건)")
    print(f"{'='*55}")
    for s in 목록[-10:]:
        print(f"\n  [{s['날짜']}] {s['상품명']}")
        print(f"     플랫폼: {s['플랫폼']} | 수량: {s['수량']}개")
        print(f"     매출: {s['총매출']:,}원 | 순이익: {s['순이익']:,}원 ({s['마진율']}%)")

if __name__ == "__main__":
    while True:
        print("\n" + "="*45)
        print("  💰 수익 관리 장부")
        print("="*45)
        print("  1. 판매 내역 등록")
        print("  2. 수익 통계 보기")
        print("  3. 전체 내역 보기")
        print("  4. 종료")
        print("="*45)

        선택 = input("  번호를 입력하세요: ")

        if 선택 == "1":
            판매등록()
        elif 선택 == "2":
            통계보기()
        elif 선택 == "3":
            내역보기()
        elif 선택 == "4":
            print("  종료합니다.")
            break