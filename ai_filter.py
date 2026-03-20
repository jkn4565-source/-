import anthropic
import requests

NAVER_CLIENT_ID = "NmoPGi9LLT1pbGFRCQ45"
NAVER_CLIENT_SECRET = "Z60X30C0Li"
CLAUDE_API_KEY = "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키"

client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

def 네이버검색(상품명):
    url = "https://openapi.naver.com/v1/search/shop.json"
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
    }
    params = {"query": 상품명, "sort": "sim", "display": 20}
    response = requests.get(url, headers=headers, params=params)
    return response.json()

def Claude분석(상품명, 상품목록, 평균가, 최저가):
    상품정보 = ""
    for i, item in enumerate(상품목록[:5], 1):
        상품정보 += f"{i}. {item['title'][:30]} | {int(item['lprice']):,}원 | {item['mallName']}\n"

    프롬프트 = f"""
당신은 위탁배송 전문가입니다. 아래 상품 정보를 분석해주세요.

[검색 상품명]: {상품명}
[시장 평균가]: {평균가:,}원
[최저가]: {최저가:,}원

[상위 5개 상품]
{상품정보}

다음 항목을 분석해주세요:
1. 미끼상품 여부 (최저가가 평균가의 50% 미만이면 의심)
2. 위탁판매 추천 여부
3. 적정 판매가 추천
4. 주의사항

간결하게 핵심만 답변해주세요.
"""
    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": 프롬프트}]
    )
    return message.content[0].text

def 미끼상품분석(상품명):
    print(f"\n🔍 '{상품명}' 분석 중...")
    data = 네이버검색(상품명)
    상품목록 = []
    for item in data.get('items', []):
        가격 = int(item['lprice'])
        if 가격 <= 100:
            continue
        해외키워드 = ['직구', '해외', '구매대행', 'USA', '중국', '헤외', '면세']
        if any(k in item['title'] or k in item['mallName'] for k in 해외키워드):
            continue
        상품목록.append(item)

    if not 상품목록:
        print("분석할 상품이 없습니다.")
        return

    가격목록 = [int(i['lprice']) for i in 상품목록]
    평균가 = sum(가격목록) // len(가격목록)
    최저가 = min(가격목록)

    print(f"\n{'='*45}")
    print(f"  📊 {상품명} 기본 분석")
    print(f"{'='*45}")
    print(f"  수집 상품 수: {len(상품목록)}개")
    print(f"  최저가: {최저가:,}원")
    print(f"  평균가: {평균가:,}원")
    미끼의심 = 최저가 < 평균가 * 0.5
    print(f"  미끼상품 의심: {'⚠️ 예' if 미끼의심 else '✅ 아님'}")
    print(f"\n{'='*45}")
    print(f"  🤖 Claude AI 정밀 분석 중...")
    print(f"{'='*45}")
    AI분석결과 = Claude분석(상품명, 상품목록, 평균가, 최저가)
    print(AI분석결과)

if __name__ == "__main__":
    while True:
        print("\n" + "="*45)
        print("  🤖 Claude AI 미끼상품 분석기")
        print("="*45)
        상품명 = input("  분석할 상품명 입력 (종료: q): ")
        if 상품명.lower() == 'q':
            break
        미끼상품분석(상품명)