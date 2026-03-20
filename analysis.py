import requests
from datetime import datetime
import json
import os

CLIENT_ID = "NmoPGi9LLT1pbGFRCQ45"
CLIENT_SECRET = "Z60X30C0Li"

데이터파일 = "인기상품데이터.json"

def 네이버검색(검색어, 개수=20):
    url = "https://openapi.naver.com/v1/search/shop.json"
    headers = {
        "X-Naver-Client-Id": CLIENT_ID,
        "X-Naver-Client-Secret": CLIENT_SECRET
    }
    params = {"query": 검색어, "sort": "sim", "display": 개수}
    response = requests.get(url, headers=headers, params=params)
    return response.json()

def 인기상품조회(검색어):
    print(f"\n🔍 '{검색어}' 인기상품 분석 중...")
    배송비입력 = input("  기본 배송비를 입력하세요 (무료배송이면 0): ")
    배송비 = int(배송비입력) if 배송비입력.isdigit() else 0
    data = 네이버검색(검색어, 개수=50)
    상품목록 = []
    for item in data.get('items', []):
        가격 = int(item['lprice'])
        if 가격 <= 100:
            continue
        해외키워드 = ['직구', '해외', '구매대행', 'USA', '중국', '헤외', '면세']
        if any(k in item['title'] or k in item['mallName'] for k in 해외키워드):
            continue
        배송비적용 = 0 if '무료' in item.get('title', '') else 배송비
        상품목록.append({
            "제목": item['title'].replace('<b>', '').replace('</b>', ''),
            "가격": 가격,
            "배송비": 배송비적용,
            "총가격": 가격 + 배송비적용,
            "쇼핑몰": item['mallName'],
            "링크": item['link'],
        })
    if not 상품목록:
        print("분석할 상품이 없습니다.")
        return
    가격목록 = [s['가격'] for s in 상품목록]
    총가격목록 = [s['총가격'] for s in 상품목록]
    평균가 = sum(가격목록) // len(가격목록)
    총평균가 = sum(총가격목록) // len(총가격목록)
    지금시각 = datetime.now().strftime("%Y년 %m월 %d일 %H시")
    print(f"\n{'='*45}")
    print(f"  📊 {검색어} 인기상품 분석")
    print(f"  📅 {지금시각} 기준")
    print(f"{'='*45}")
    print(f"  수집 상품 수       : {len(상품목록)}개")
    print(f"  평균가 (배송비제외): {평균가:,}원")
    print(f"  평균가 (배송비포함): {총평균가:,}원")
    print(f"  최저가 (배송비제외): {min(가격목록):,}원")
    print(f"  최저가 (배송비포함): {min(총가격목록):,}원")
    print(f"  적용 배송비        : {배송비:,}원")
    정렬상품 = sorted(상품목록, key=lambda x: x['총가격'])
    print(f"\n  🏆 배송비 포함 최저가 TOP 5")
    print(f"  {'─'*35}")
    for i, s in enumerate(정렬상품[:5], 1):
        배송비표시 = "무료배송" if s['배송비'] == 0 else f"배송비 {s['배송비']:,}원"
        print(f"  {i}. {s['제목'][:28]}")
        print(f"     💰 상품가: {s['가격']:,}원 | {배송비표시}")
        print(f"     💳 총합계: {s['총가격']:,}원 | {s['쇼핑몰']}")
        print(f"     🔗 {s['링크']}")
    저장데이터 = {
        "날짜": datetime.now().strftime("%Y-%m-%d"),
        "월": datetime.now().strftime("%Y-%m"),
        "검색어": 검색어,
        "평균가": 평균가,
        "총평균가": 총평균가,
        "최저가": min(가격목록),
        "상품수": len(상품목록),
    }
    전체데이터 = []
    if os.path.exists(데이터파일):
        with open(데이터파일, 'r', encoding='utf-8') as f:
            전체데이터 = json.load(f)
    전체데이터.append(저장데이터)
    with open(데이터파일, 'w', encoding='utf-8') as f:
        json.dump(전체데이터, f, ensure_ascii=False, indent=2)
    print(f"\n  ✅ 데이터 저장 완료!")

def 월별분석():
    if not os.path.exists(데이터파일):
        print("저장된 데이터가 없습니다.")
        return
    with open(데이터파일, 'r', encoding='utf-8') as f:
        전체데이터 = json.load(f)
    이번달 = datetime.now().strftime("%Y-%m")
    이번달데이터 = [d for d in 전체데이터 if d['월'] == 이번달]
    if not 이번달데이터:
        print("이번 달 데이터가 없습니다.")
        return
    print(f"\n{'='*45}")
    print(f"  📅 {이번달} 월별 검색 분석")
    print(f"{'='*45}")
    검색어별 = {}
    for d in 이번달데이터:
        키 = d['검색어']
        if 키 not in 검색어별:
            검색어별[키] = []
        검색어별[키].append(d.get('총평균가', d['평균가']))
    for 검색어, 가격들 in 검색어별.items():
        평균 = sum(가격들) // len(가격들)
        print(f"  🔍 {검색어:15} 배송포함 평균가: {평균:,}원 | 조회: {len(가격들)}회")

if __name__ == "__main__":
    while True:
        print("\n" + "="*45)
        print("  📊 인기상품 분석 프로그램")
        print("="*45)
        print("  1. 상품 분석하기")
        print("  2. 월별 분석 보기")
        print("  3. 종료")
        print("="*45)
        선택 = input("  번호를 입력하세요: ")
        if 선택 == "1":
            검색어 = input("  검색할 상품명: ")
            인기상품조회(검색어)
        elif 선택 == "2":
            월별분석()
        elif 선택 == "3":
            print("  프로그램을 종료합니다.")
            break
        else:
            print("  1, 2, 3 중에 입력해주세요!")