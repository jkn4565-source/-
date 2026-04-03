import streamlit as st
import requests
import pandas as pd
import json
import xml.etree.ElementTree as ET
import base64
import os
import re
import glob
import zipfile
import io as _io
import time
import textwrap
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import io
from streamlit_paste_button import paste_image_button

# ==========================================
# 🔐 1. 안전한 API 키 로드
# ==========================================
try:
    NAVER_CLIENT_ID     = st.secrets["NAVER_CLIENT_ID"]
    NAVER_CLIENT_SECRET = st.secrets["NAVER_CLIENT_SECRET"]
    DOMEGGOOK_API_KEY   = st.secrets["DOMEGGOOK_API_KEY"]
    ELEVENST_API_KEY    = st.secrets["ELEVENST_API_KEY"]
    CLAUDE_API_KEY      = st.secrets["CLAUDE_API_KEY"]
    TELEGRAM_BOT_TOKEN  = st.secrets["TELEGRAM_BOT_TOKEN"]
    TELEGRAM_CHAT_ID    = st.secrets["TELEGRAM_CHAT_ID"]
    RAPID_API_KEY       = st.secrets.get("RAPID_API_KEY", "")
except KeyError as e:
    st.error(f"시크릿 키 설정 오류: {e}")
    st.stop()

# ==========================================
# 🎨 2. 디자인 CSS
# ==========================================
st.set_page_config(page_title="위탁의왕 Ultra", page_icon="👑", layout="wide")
st.markdown("""
<style>
@keyframes gradientBG {
    0%{background-position:0% 50%} 50%{background-position:100% 50%} 100%{background-position:0% 50%}
}
.stApp {
    background: linear-gradient(-45deg,#0a0f1e,#1a2a4a,#0d1b33,#050a14);
    background-size:400% 400%; animation:gradientBG 15s ease infinite; color:#e0e6ed;
}
[data-testid="stSidebar"] {
    background-color:rgba(3,45,25,0.9)!important;
    backdrop-filter:blur(10px); border-right:1px solid rgba(255,215,0,0.2);
}
[data-testid="stSidebar"] * {color:#f0f0f0!important; font-weight:500;}
.stButton>button {
    width:100%; border-radius:8px; font-weight:bold;
    background:linear-gradient(45deg,#03C75A,#029f47);
    color:white; border:none; transition:all 0.3s;
    box-shadow:0 4px 15px rgba(3,199,90,0.3);
}
.stButton>button:hover {
    background:linear-gradient(45deg,#ffd700,#ffb900);
    color:#032d19; transform:translateY(-2px);
    box-shadow:0 6px 20px rgba(255,215,0,0.4);
}
h1{color:#ffd700!important; text-shadow:0 2px 4px rgba(0,0,0,0.5); font-weight:800; letter-spacing:-1px;}
h2,h3{color:#f0f0f0!important;}
.stMetric label{color:#aaa!important;}
.stMetric [data-testid="stMetricValue"]{color:#ffd700!important; font-weight:800;}
.result-card {
    border:1px solid rgba(255,255,255,0.05); padding:20px; border-radius:12px;
    background-color:rgba(255,255,255,0.02); margin-bottom:15px; transition:border 0.3s; position:relative;
}
.result-card:hover{border:1px solid rgba(255,215,0,0.3);}
.stTextInput input,.stNumberInput input,.stSelectbox div,.stTextArea textarea {
    background-color:rgba(0,0,0,0.2)!important; color:white!important;
    border:1px solid rgba(255,255,255,0.1)!important; border-radius:8px!important;
}
hr{border:0; border-top:1px solid rgba(255,215,0,0.1);}
.keyword-badge {
    display:inline-block; padding:5px 12px; margin-right:10px; border-radius:20px;
    background-color:rgba(255,215,0,0.1); border:1px solid rgba(255,215,0,0.3);
    color:#ffd700; font-size:0.9rem; font-family:monospace;
}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🔐 3. 세션 상태
# ==========================================
if 'helper_generated_text' not in st.session_state: st.session_state['helper_generated_text'] = ""
if 'keyword_input'         not in st.session_state: st.session_state['keyword_input'] = ""
if 'keywords_list'         not in st.session_state: st.session_state['keywords_list'] = []
if 'run_search'            not in st.session_state: st.session_state['run_search'] = False

# ==========================================
# 🛠️ 4. 핵심 함수 모음
# ==========================================

def call_claude_api(body):
    try:
        headers = {
            "x-api-key": CLAUDE_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        body["model"] = "claude-sonnet-4-6"
        resp = requests.post("https://api.anthropic.com/v1/messages",
                             headers=headers, json=body, timeout=80)
        if resp.status_code == 200:
            return resp.json()["content"][0]["text"].strip()
        return None
    except:
        return None

def 네이버검색(상품명, 개수=50):
    url = "https://openapi.naver.com/v1/search/shop.json"
    headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
    params  = {"query": 상품명, "sort": "sim", "display": 개수}
    try:    return requests.get(url, headers=headers, params=params).json()
    except: return {"items": []}

def 필터링(items, 배송비=0):
    결과 = []
    해외 = ['직구','해외','구매대행','USA','중국','항공','통관']
    for item in items:
        가격 = int(item['lprice'])
        if 가격 <= 100 or any(k in item['title'] for k in 해외): continue
        결과.append({
            "제목": item['title'].replace('<b>','').replace('</b>',''),
            "가격": 가격, "배송비": 배송비, "총가격": 가격+배송비,
            "이미지": item.get('image',''), "링크": item.get('link',''), "출처": "네이버"
        })
    return 결과

def 도매꾹검색(검색어, 개수=20):
    url    = "https://domeggook.com/ssl/api/"
    params = {"ver":"4.1","mode":"getItemList","aid":DOMEGGOOK_API_KEY,
              "market":"dome","om":"json","kw":검색어,"sz":개수}
    try:
        data  = requests.get(url, params=params).json()
        items = data['domeggook']['list']['item']
        if isinstance(items, dict): items = [items]
        결과 = []
        for item in items:
            p = int(item.get('price', 0))
            f = int(item.get('deli',{}).get('fee', 0) or 0)
            if item.get('deli',{}).get('who','') == 'S': f = 0
            결과.append({
                "제목": item.get('title',''), "가격": p, "배송비": f, "총가격": p+f,
                "이미지": item.get('thumb',''), "링크": item.get('url',''), "출처": "도매꾹"
            })
        return sorted(결과, key=lambda x: x['총가격'])
    except: return []

def 검색_11번가(검색어, 개수=20):
    url    = "http://openapi.11st.co.kr/openapi/OpenApiService.tmall"
    params = {"key": ELEVENST_API_KEY, "apiCode": "ProductSearch",
              "keyword": 검색어, "pageSize": 개수}
    try:
        resp = requests.get(url, params=params)
        root = ET.fromstring(resp.content.decode('euc-kr', errors='ignore'))
        결과 = []
        for item in root.findall('.//Product'):
            f = int(item.findtext('DeliveryFee','0').replace(',','').strip() or 0)
            p = int(item.findtext('SalePrice','0').replace(',','').strip() or 0)
            if f >= 6000: continue
            결과.append({
                "제목": item.findtext('ProductName','').replace('<b>','').replace('</b>',''),
                "가격": p, "배송비": f, "총가격": p+f,
                "이미지": item.findtext('ProductImage100',''),
                "링크": item.findtext('DetailPageUrl',''), "출처": "11번가"
            })
        return sorted(결과, key=lambda x: x['총가격'])
    except: return []

def 검색_글로벌_알리(검색어, 개수=20):
    endpoints = [
        "https://aliexpress-datahub.p.rapidapi.com/item_search_2",
        "https://aliexpress-datahub.p.rapidapi.com/item_search_3"
    ]
    headers = {"x-rapidapi-key": RAPID_API_KEY.strip(),
               "x-rapidapi-host": "aliexpress-datahub.p.rapidapi.com"}
    response = None
    for url in endpoints:
        try:
            response = requests.get(url, headers=headers,
                                    params={"q": 검색어,"page":"1"}, timeout=5)
            if response.status_code == 200: break
        except: continue
    if not response or response.status_code != 200: return []
    try:
        data       = response.json()
        items_data = []
        if 'result' in data:
            if 'resultList' in data['result']: items_data = data['result']['resultList']
            elif isinstance(data['result'], list): items_data = data['result']
        결과 = []
        for item in items_data:
            ii  = item.get('item',{})
            usd = float(ii.get('sku',{}).get('def',{}).get('promotionPrice',
                        ii.get('sku',{}).get('def',{}).get('price',0)))
            krw = int(usd * 1500)
            img = ii.get('image','')
            lnk = ii.get('itemUrl','')
            if img and not img.startswith('http'): img = "https:" + img
            if lnk and not lnk.startswith('http'): lnk = "https:" + lnk
            결과.append({
                "제목": ii.get('title',''), "가격": krw, "총가격": krw,
                "판매량": int(ii.get('sales',0)),
                "평점": ii.get('evaluateRate','N/A'),
                "이미지": img, "링크": lnk, "출처": "AliExpress"
            })
        return sorted(결과, key=lambda x: x['가격'])
    except: return []

def 출력_통합_결과_레이아웃(검색어):
    with st.spinner(f"'{검색어}' 국내 및 글로벌 최저가 동시 분석 중..."):
        n_list = 필터링(네이버검색(검색어).get('items',[]))
        d_list = 도매꾹검색(검색어)
        e_list = 검색_11번가(검색어)
        en_kw  = 검색어
        if RAPID_API_KEY:
            res_kw = call_claude_api({"max_tokens":50,"messages":[{"role":"user","content":
                f"'{검색어}'를 알리익스프레스 검색용 영어 단어로 번역해줘. 설명 없이 영어 단어만 출력해."}]})
            en_kw  = res_kw if res_kw else 검색어
            a_list = 검색_글로벌_알리(en_kw)
        else: a_list = []

        c1,c2,c3,c4 = st.columns(4)
        for (name, data), col in zip(
            [("🟢 네이버",n_list),("🔵 도매꾹",d_list),("🔴 11번가",e_list),("✈️ 글로벌(알리)",a_list)],
            [c1,c2,c3,c4]):
            with col:
                st.markdown(f"### {name}")
                if data:
                    best = data[0]
                    si   = f"<div style='position:absolute;top:10px;left:10px;background:#ff4500;color:white;padding:3px 8px;border-radius:5px;font-weight:bold;font-size:.8rem;'>판매량 {best['판매량']}+</div>" if '판매량' in best else ""
                    st.markdown(f"""<div class="result-card">{si}
<img src="{best['이미지']}" style="width:100%;border-radius:8px;margin-bottom:15px;">
<h4 style="color:#ffd700;margin:0;">{best.get('총가격',best.get('가격')):,}원</h4>
<p style="color:#ccc;font-size:.8rem;margin:5px 0 15px 0;height:40px;overflow:hidden;">{best['제목'][:40]}...</p>
</div>""", unsafe_allow_html=True)
                    st.link_button("👑 왕의 소싱처로 이동", best['링크'], type="primary")
                else:
                    if name == "✈️ 글로벌(알리)":
                        st.warning("서버 혼잡 (플랜B 가동)")
                        st.link_button("🚀 알리 다이렉트 결과",
                            f"https://ko.aliexpress.com/w/wholesale-{en_kw.replace(' ','-')}.html",
                            use_container_width=True)
                    else: st.error("결과 없음")

        combined = sorted(n_list[:10]+d_list[:10]+e_list[:10]+a_list[:10],
                          key=lambda x: x['총가격'])
        if combined:
            st.divider()
            st.markdown("## 🏆 전체 통합 최저가 TOP 10")
            for i, item in enumerate(combined[:10], 1):
                col_img, col_txt, col_btn = st.columns([1,5,2])
                with col_img: st.image(item['이미지'], width=100)
                with col_txt:
                    badge = "✈️ 직구" if item['출처']=="AliExpress" else "🇰🇷 국내"
                    st.markdown(f"""<div style="margin-bottom:15px;">
<strong style="color:#ffd700;font-size:1.1rem;">{i}. [{badge}|{item['출처']}]</strong>
<span style="color:#fff;">{item['제목']}</span><br>
<span style="color:#03C75A;font-weight:bold;font-size:1.2rem;">{item['총가격']:,}원</span>
</div>""", unsafe_allow_html=True)
                with col_btn: st.link_button("구매하러 가기", item['링크'])

def send_telegram(text):
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                      params={"chat_id":TELEGRAM_CHAT_ID,"text":text,"parse_mode":"HTML"})
    except: pass

이력파일 = "추천이력.json"
def 이력_로드():
    if os.path.exists(이력파일): return json.load(open(이력파일,'r',encoding='utf-8'))
    return {}
def 이력_저장(날짜, 키워드목록):
    data = 이력_로드()
    data[날짜] = list(set(data.get(날짜,[]) + 키워드목록))
    json.dump(data, open(이력파일,'w',encoding='utf-8'), ensure_ascii=False, indent=2)
def 전체_사용된_키워드():
    data = 이력_로드()
    모든키워드 = []
    for v in data.values(): 모든키워드.extend(v)
    return set(모든키워드)

def 소싱데이터_조회(keyword):
    n = 필터링(네이버검색(keyword, 개수=10).get('items',[]))
    d = 도매꾹검색(keyword, 개수=5)
    combined = sorted(n[:5]+d[:5], key=lambda x: x['총가격'])
    return combined[0] if combined else None

# ── HTML 상세페이지 빌더 ──────────────────────────────────────────
def generate_html_detail_page(keyword, sourcing, reason, ocean_grade, ai_content):
    price_str  = f"{sourcing['총가격']:,}원" if sourcing else "미확인"
    origin_str = sourcing['출처']            if sourcing else "-"
    link_str   = sourcing.get('링크','#')    if sourcing else '#'
    img_str    = sourcing.get('이미지','')   if sourcing else ''
    today      = datetime.now().strftime('%Y년 %m월 %d일')
    oc         = "#00ff88" if "블루" in ocean_grade else "#ffd700" if "중간" in ocean_grade else "#ff4b4b"
    body       = ai_content
    body = re.sub(r'### (.+)',      r'<h3>\1</h3>', body)
    body = re.sub(r'## (.+)',       r'<h2>\1</h2>', body)
    body = re.sub(r'\*\*(.+?)\*\*',r'<strong>\1</strong>', body)
    body = re.sub(r'^\* (.+)',      r'<li>\1</li>', body, flags=re.MULTILINE)
    body = body.replace('\n\n','</p><p>').replace('\n','<br>')
    img_tag = f'<img src="{img_str}" alt="{keyword}">' if img_str else '<div class="img-placeholder">📦</div>'
    return f"""<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>👑 위탁의왕 — {keyword}</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@700;900&family=Noto+Sans+KR:wght@300;400;700&display=swap" rel="stylesheet">
<style>
:root{{--g:{oc};--bg:#07080f;--tx:#e8eaf0;--dm:#8892a4;--cd:rgba(255,255,255,.04);--bd:rgba(255,255,255,.07)}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:var(--bg);color:var(--tx);font-family:'Noto Sans KR',sans-serif;line-height:1.8}}
@keyframes fu{{from{{opacity:0;transform:translateY(20px)}}to{{opacity:1;transform:translateY(0)}}}}
.fu{{animation:fu .6s ease both}}
header{{padding:60px 40px 40px;text-align:center;border-bottom:1px solid var(--bd);background:linear-gradient(180deg,rgba(255,215,0,.05),transparent)}}
header h1{{font-family:'Noto Serif KR',serif;font-size:clamp(2rem,5vw,3.5rem);font-weight:900;color:{oc};text-shadow:0 0 40px {oc}44}}
header .sub{{margin-top:12px;color:var(--dm);font-size:.95rem;letter-spacing:2px}}
.meta{{display:flex;flex-wrap:wrap;gap:12px;justify-content:center;padding:28px 40px;border-bottom:1px solid var(--bd)}}
.badge{{padding:10px 20px;border-radius:100px;font-size:.88rem;font-weight:700;border:1px solid var(--bd);background:var(--cd)}}
.b-o{{border-color:{oc}55;color:{oc};background:{oc}11}}
.b-p{{border-color:#00b4d855;color:#00b4d8;background:#00b4d811}}
.b-s{{border-color:rgba(255,215,0,.3);color:#ffd700;background:rgba(255,215,0,.1)}}
.b-d{{color:var(--dm)}}
main{{max-width:960px;margin:0 auto;padding:50px 24px 80px}}
.ic{{display:flex;gap:30px;align-items:flex-start;background:var(--cd);border:1px solid var(--bd);border-radius:20px;padding:28px;margin-bottom:40px}}
.ic img{{width:180px;height:180px;object-fit:cover;border-radius:12px;flex-shrink:0}}
.img-placeholder{{width:180px;height:180px;border-radius:12px;background:linear-gradient(135deg,#1a2a3a,#0d1b2a);display:flex;align-items:center;justify-content:center;font-size:3rem;flex-shrink:0}}
.ic-info h2{{font-family:'Noto Serif KR',serif;font-size:1.5rem;font-weight:700;color:#ffd700;margin-bottom:10px}}
.ic-info p{{color:var(--dm);font-size:.9rem;line-height:1.7}}
.sb{{display:inline-block;margin-top:16px;padding:10px 24px;border-radius:8px;background:linear-gradient(45deg,#03C75A,#029f47);color:#fff;font-weight:700;text-decoration:none}}
.rs{{background:linear-gradient(135deg,rgba(0,180,216,.08),rgba(0,255,136,.05));border:1px solid rgba(0,180,216,.2);border-radius:12px;padding:20px 24px;margin-bottom:24px;color:#a8eeff}}
.rs span{{font-weight:700;color:#00b4d8}}
.sec{{background:var(--cd);border:1px solid var(--bd);border-radius:16px;padding:32px 36px;margin-bottom:24px}}
.sec h2{{font-family:'Noto Serif KR',serif;font-size:1.3rem;font-weight:700;color:var(--tx);margin-bottom:16px;border-bottom:1px solid var(--bd);padding-bottom:12px}}
.ab h3{{color:#ffd700;font-size:1rem;margin:16px 0 6px}}
.ab p{{color:var(--dm);font-size:.95rem;margin-bottom:8px}}
.ab li{{color:var(--dm);font-size:.95rem;margin:5px 0 5px 20px;list-style:none;position:relative}}
.ab li::before{{content:'▸';position:absolute;left:-16px;color:#ffd700;font-size:.8rem}}
.ab strong{{color:var(--tx)}}
footer{{text-align:center;padding:40px;border-top:1px solid var(--bd);color:var(--dm);font-size:.82rem}}
footer strong{{color:#ffd700}}
@media(max-width:600px){{.ic{{flex-direction:column}}.ic img{{width:100%;height:200px}}}}
</style></head><body>
<header class="fu"><h1>👑 {keyword}</h1><p class="sub">위탁의왕 AI 상세페이지 기획안 · {today}</p></header>
<div class="meta fu">
  <div class="badge b-o">📊 {ocean_grade}</div>
  <div class="badge b-p">💰 {price_str}</div>
  <div class="badge b-s">🏪 {origin_str}</div>
  <div class="badge b-d">📅 {today}</div>
</div>
<main>
  <div class="ic fu">{img_tag}
    <div class="ic-info"><h2>소싱 상품 정보</h2>
    <p><strong>키워드:</strong> {keyword}</p>
    <p><strong>소싱가:</strong> {price_str} ({origin_str})</p>
    <p><strong>경쟁 강도:</strong> {ocean_grade}</p>
    <a href="{link_str}" target="_blank" class="sb">🛒 소싱처 바로가기</a></div>
  </div>
  <div class="rs fu"><span>💡 AI 추천 이유 —</span> {reason}</div>
  <div class="sec fu"><h2>📄 상세페이지 기획안 전문</h2><div class="ab"><p>{body}</p></div></div>
</main>
<footer>Generated by <strong>👑 위탁의왕 Ultra</strong> · Powered by Claude AI · {today}</footer>
</body></html>"""

def ai_상세페이지_생성_및_저장(keyword, sourcing, reason, ocean_grade, idx):
    price_info = f"소싱가 {sourcing['총가격']:,}원 ({sourcing['출처']})" if sourcing else "소싱가 미확인"
    img_url    = sourcing.get('이미지','') if sourcing else ''
    img_content = []
    if img_url:
        try:
            r = requests.get(img_url, timeout=10)
            if r.status_code == 200:
                ct = r.headers.get('Content-Type','image/jpeg')
                mt = ('image/png' if 'png' in ct else 'image/gif' if 'gif' in ct else
                      'image/webp' if 'webp' in ct else 'image/jpeg')
                img_content = [{"type":"image","source":{"type":"base64","media_type":mt,
                                "data":base64.b64encode(r.content).decode('utf-8')}}]
        except: pass
    prompt = f"""당신은 매출을 10배 올려주는 이커머스 카피라이터입니다.
{'첨부 이미지를 분석하고' if img_content else '아래 정보를 바탕으로'} 스마트스토어 상세페이지 기획안을 작성하세요.
[상품 정보] 키워드: {keyword} / {price_info} / 추천 이유: {reason}
### 🏷️ 상품 타이틀 후보 3가지
### 💡 핵심 셀링포인트 3가지
### 📝 상단 후킹 문구
### ✅ 상품 특징 5가지
### 🎯 추천 검색 키워드 10개
### 💰 가격 전략"""
    ai_text = call_claude_api({"max_tokens":2000,"messages":[{"role":"user",
              "content":img_content+[{"type":"text","text":prompt}]}]})
    if not ai_text: return None, None, None
    html_str  = generate_html_detail_page(keyword, sourcing, reason, ocean_grade, ai_text)
    safe_name = re.sub(r'[^\w가-힣]','_', keyword)
    filename  = f"상세페이지_{datetime.now().strftime('%Y%m%d')}_{idx+1:02d}_{safe_name}.html"
    save_dir  = "상세페이지_저장"
    os.makedirs(save_dir, exist_ok=True)
    filepath  = os.path.join(save_dir, filename)
    with open(filepath,'w',encoding='utf-8') as f: f.write(html_str)
    return ai_text, html_str, filepath

# ── 시즌 캘린더 포함 트렌드 키워드 생성 ─────────────────────────
def ai_트렌드_키워드_생성(카테고리, 타겟가격대, 추천수):
    사용된 = 전체_사용된_키워드()
    제외   = ", ".join(사용된) if 사용된 else "없음"
    월 = datetime.now().month
    시즌맵 = {
        1: ("겨울 한파·설 연휴",   ["핫팩","방한용품","새해선물","귀마개","온열제품"]),
        2: ("졸업·입학 시즌",      ["졸업선물","입학선물","책가방","문구세트","화이트데이준비"]),
        3: ("봄·입학·황사",        ["황사마스크","봄나들이","미세먼지","입학준비","꽃샘추위"]),
        4: ("봄 피크닉·캠핑 시작", ["피크닉용품","돗자리","캠핑입문","봄원피스","자외선차단"]),
        5: ("가정의 달·야외활동",  ["어버이날선물","어린이날선물","가족나들이","캠핑","스포츠"]),
        6: ("초여름·장마 준비",    ["장마용품","제습제","우산","여름준비","에어컨용품"]),
        7: ("여름 피크·휴가",      ["물놀이","수영용품","여행용품","모기퇴치","냉감용품"]),
        8: ("무더위·개학 준비",    ["개학준비","냉방용품","여름정리","등교용품","쿨토시"]),
        9: ("가을·추석 시즌",      ["추석선물","가을패션","단풍여행","운동회","독서용품"]),
        10:("가을 나들이·할로윈",  ["할로윈소품","가을캠핑","무드등","코스튬","패딩준비"]),
        11:("수능·초겨울·블프",    ["수험생용품","수능선물","방한준비","블랙프라이데이","크리스마스준비"]),
        12:("연말·크리스마스",     ["크리스마스선물","연말파티","새해달력","겨울용품","연하장"]),
    }
    다음월 = (월 % 12) + 1
    시즌명, 시즌kw      = 시즌맵.get(월, ("일반",[]))
    다음시즌명, 다음kw  = 시즌맵.get(다음월, ("일반",[]))
    prompt = f"""당신은 한국 스마트스토어/쿠팡 위탁판매 전문 MD입니다.
[조건] 카테고리:{카테고리} / 가격대:{타겟가격대} / 추천:{추천수}개
블루오션 위주, 레드오션 제외, 중복금지:[{제외}]
[🗓️ 시즌 — 반드시 반영]
이번달({월}월): {시즌명} → 힌트: {', '.join(시즌kw)}
다음달({다음월}월): {다음시즌명} → 선제힌트: {', '.join(다음kw[:3])}
이번달 70% + 다음달 선제 30% 비율로 추천하세요.
[출력] JSON 배열만. 설명 없음.
[{{"keyword":"키워드","reason":"추천이유(시즌연관성포함)","price_range":"소싱가~판매가","season":"이번달/다음달선제"}}]"""
    res = call_claude_api({"max_tokens":1500,"messages":[{"role":"user","content":prompt}]})
    if res:
        try:
            결과 = json.loads(res.replace("```json","").replace("```","").strip())
            return [it for it in 결과 if it['keyword'] not in 사용된]
        except: st.error("AI 응답 파싱 실패.")
    return []

def 경쟁강도_필터(키워드목록):
    결과 = []
    bar = st.progress(0, text="네이버 경쟁강도 분석 중...")
    for i, item in enumerate(키워드목록):
        total = 네이버검색(item['keyword'], 개수=10).get('total', 999999)
        item['total_count'] = total
        if total < 15000:   item['ocean'], item['score'] = "🟢 블루오션", "상"
        elif total < 50000: item['ocean'], item['score'] = "🟡 중간",     "중"
        else:               item['ocean'], item['score'] = "🔴 레드오션", "하"
        결과.append(item)
        bar.progress((i+1)/len(키워드목록), text=f"분석 중: {item['keyword']} ({total:,}개)")
    bar.empty()
    return sorted(결과, key=lambda x: x['total_count'])

# ==========================================
# 🖥️ 5. 사이드바 메뉴
# ==========================================
st.sidebar.markdown("# 👑 위탁의왕 Ultra")
st.sidebar.markdown("---")
메뉴 = st.sidebar.radio("메뉴 선택", [
    "🏠 홈",
    "📸 이미지로 검색",
    "🔎 통합 최저가 검색",
    "🇨🇳 글로벌 사입/직구 검색",
    "🏪 상품 등록 도우미",
    "🕵️‍♂️ 경쟁사 리뷰 분석기",
    "💰 마진 계산기",
    "📦 재고/가격 알림",
    "💎 블루오션 탐지 + 🤖 자동추천",
    "🏷️ 상품명 최적화",
    "🖼️ 썸네일 메이커",
    "🔬 경쟁사 상품명 역분석",
], index=0)

# ==========================================
# 🏠 홈
# ==========================================
if 메뉴 == "🏠 홈":
    st.markdown("<h1>👑 위탁의왕 자동화 대시보드 v7.0 Ultra</h1>", unsafe_allow_html=True)
    st.caption(f"📅 오늘 날짜: {datetime.now().strftime('%Y-%m-%d')} | 대표님, 오늘도 위탁 시장의 왕이 되어보시죠!")
    st.divider()
    c1,c2,c3 = st.columns(3)
    with c1: st.metric("업무 모드", "매출 폭발 모드 🚀")
    with c2: st.metric("AI 마케터", "Sonnet Ultra")
    with c3: st.metric("버전", "v7.0 Full Pack")
    st.divider()
    st.markdown("""
    <div style="background:rgba(255,215,0,0.05);padding:30px;border-radius:15px;border:1px solid rgba(255,215,0,0.1);">
    <h3 style="color:#ffd700;margin-top:0;">👋 위탁의 왕, 대표님 환영합니다!</h3>
    <p style="color:#e0e6ed;line-height:1.8;">
    단순히 상품을 올리고 기다리던 시대는 끝났습니다.<br>
    데이터를 기반으로 최저가를 <b>사냥(Sourcing)</b>하고, AI를 활용해 <b>유혹(Copywriting)</b>해야 합니다.<br><br>
    <b>v7.0 신기능:</b> 🏷️ 상품명 최적화 · 🖼️ 썸네일 메이커 · 🔬 경쟁사 역분석 · 📅 시즌 캘린더 자동 연동
    </p></div>""", unsafe_allow_html=True)

# ==========================================
# 📸 이미지로 검색
# ==========================================
elif 메뉴 == "📸 이미지로 검색":
    st.markdown("<h1>📸 AI 이미지 최저가 검색 (Lens Mode)</h1>", unsafe_allow_html=True)
    st.info("💡 상품을 캡처(Win+Shift+S)한 뒤 아래 버튼을 누르거나, 파일을 직접 업로드해주세요.")
    if st.button("🔄 화면이 멈추거나 막혔을 때 누르세요 (초기화)", type="secondary"):
        st.session_state.update({'keywords_list':[],'keyword_input':'','run_search':False})
        st.rerun()
    with st.container():
        paste_result = paste_image_button(label="📋 캡처한 이미지 바로 붙여넣기 (PC용)",
            background_color="#03C75A", hover_background_color="#029f47", text_color="#ffffff")
        img_bytes = None
        if paste_result.image_data is not None:
            try:
                pil = paste_result.image_data
                if pil.mode != 'RGB': pil = pil.convert('RGB')
                pil.thumbnail((1500,1500))
                buf = io.BytesIO(); pil.save(buf, format="JPEG"); img_bytes = buf.getvalue()
            except Exception as e: st.error(f"이미지 처리 오류: {e}")
        st.write("---")
        with st.expander("📂 내 앨범/폴더에서 사진 선택하기 (스마트폰용)", expanded=True):
            up = st.file_uploader("사진 선택", type=['jpg','jpeg','png'])
            if up:
                try:
                    pil = Image.open(io.BytesIO(up.getvalue()))
                    if pil.mode != 'RGB': pil = pil.convert('RGB')
                    pil.thumbnail((1500,1500))
                    buf = io.BytesIO(); pil.save(buf,format="JPEG"); img_bytes = buf.getvalue()
                except Exception as e: st.error(f"파일 업로드 오류: {e}")
        if img_bytes:
            b64 = base64.b64encode(img_bytes).decode("utf-8")
            st.divider()
            cu1, cu2 = st.columns([1,2])
            with cu1: st.image(img_bytes, width=300, caption="성공적으로 불러왔습니다!")
            with cu2:
                st.markdown("### 1단계: AI 정밀 분석")
                if st.button("🔍 AI 황금 키워드 9개 추출", key="btn_ai_kw"):
                    with st.spinner("이미지 정밀 분석 중..."):
                        res = call_claude_api({"model":"claude-sonnet-4-6","max_tokens":300,
                            "messages":[{"role":"user","content":[
                                {"type":"image","source":{"type":"base64","media_type":"image/jpeg","data":b64}},
                                {"type":"text","text":"당신은 한국의 10년차 탑티어 상품 소싱 MD입니다.\n1. 브랜드/모델명을 알면 앞쪽에 적으세요.\n2. 모르면 네이버/도매꾹 검색용 구체적 명사로 적으세요.\n3. 총 9개 명사형 키워드만 콤마(,)로 구분해서 출력하세요. (설명 없음)"}
                            ]}]})
                        if res:
                            st.session_state['keywords_list'] = [k.strip() for k in res.split(',')]
                            st.rerun()
                        else: st.error("⚠️ AI 서버 혼잡. 초기화 버튼을 누르고 다시 시도해주세요.")
    if st.session_state.get('keywords_list'):
        st.divider()
        st.markdown("### 2단계: 사냥할 키워드 선택")
        cols = st.columns(3)
        for i, kw in enumerate(st.session_state['keywords_list']):
            if cols[i%3].button(f"💎 {kw}", key=f"kw_{i}", use_container_width=True):
                st.session_state.update({'keyword_input':kw,'run_search':True})
                st.rerun()
    if st.session_state.get('keyword_input'):
        st.divider()
        search_kw = st.text_input("🔎 검색어 수정", value=st.session_state['keyword_input'], key="input_search_kw")
        if st.button("🛒 실시간 통합 최저가 사냥 시작", type="primary", key="btn_main_search") or st.session_state.get('run_search'):
            st.session_state['run_search'] = False
            if search_kw: 출력_통합_결과_레이아웃(search_kw)

# ==========================================
# 🔎 통합 최저가 검색
# ==========================================
elif 메뉴 == "🔎 통합 최저가 검색":
    st.markdown("<h1>🔎 통합 최저가 검색 (텍스트)</h1>", unsafe_allow_html=True)
    text_kw = st.text_input("사냥할 상품명을 입력하세요", placeholder="예: 무선 가습기", key="input_text_kw")
    if st.button("🚀 왕의 명령: 실시간 통합 비교 시작", type="primary", use_container_width=True):
        if text_kw: 출력_통합_결과_레이아웃(text_kw)

# ==========================================
# 🇨🇳 글로벌 사입/직구 검색
# ==========================================
elif 메뉴 == "🇨🇳 글로벌 사입/직구 검색":
    st.markdown("<h1>🇨🇳 글로벌 신뢰도 1티어 최저가 사냥</h1>", unsafe_allow_html=True)
    st.markdown("""<div style="background:rgba(255,215,0,0.1);padding:15px;border-radius:10px;border:1px solid #ffd700;margin-bottom:20px;">
    <h4 style="margin-top:0;color:#ffd700;">💡 신상품 사입 중국어 치트키</h4>
    <span class="keyword-badge">ins风</span> 인스타 감성 &nbsp;
    <span class="keyword-badge">新款</span> 최신 신상품 &nbsp;
    <span class="keyword-badge">创意</span> 아이디어 상품
    </div>""", unsafe_allow_html=True)
    탭1, 탭2 = st.tabs(["🔤 텍스트 사냥", "📸 3대장 순정 렌즈 사냥"])
    with 탭1:
        c1, c2 = st.columns([3,1])
        gkw = c1.text_input("사냥할 상품명 (한글)", placeholder="예: 무소음 얼음틀", key="txt_g_input")
        if c2.button("🌐 글로벌 탐색", type="primary", use_container_width=True):
            if gkw:
                with st.spinner("AI 번역 중..."):
                    en_kw = call_claude_api({"max_tokens":50,"messages":[{"role":"user","content":f"'{gkw}'를 알리익스프레스 검색용 영문으로 번역해줘. 설명 없이 영어만 출력해."}]})
                    cn_kw = call_claude_api({"max_tokens":50,"messages":[{"role":"user","content":f"'{gkw}'를 1688 검색용 중국어 간체로 번역해줘. 설명 없이 중국어만 출력해."}]})
                st.success(f"번역완료! ✈️ {en_kw} / 🇨🇳 {cn_kw}")
                ali = 검색_글로벌_알리(en_kw)
                if ali:
                    cols = st.columns(3)
                    for i, item in enumerate(ali[:9]):
                        with cols[i%3]:
                            st.markdown(f"""<div class="result-card">
<img src="{item['이미지']}" style="width:100%;border-radius:8px;margin-bottom:10px;">
<h3 style="color:#03C75A;margin:0;">{item['가격']:,}원</h3>
<p style="color:#ccc;font-size:.8rem;height:40px;overflow:hidden;">{item['제목'][:50]}...</p>
</div>""", unsafe_allow_html=True)
                            st.link_button("✈️ 바로가기", item['링크'], use_container_width=True)
                else:
                    lc1,lc2,lc3 = st.columns(3)
                    lc1.link_button("🚀 1688", f"https://s.1688.com/selloffer/offer_search.htm?keywords={cn_kw}", use_container_width=True)
                    lc2.link_button("🚀 타오바오", f"https://s.taobao.com/search?q={cn_kw}", use_container_width=True)
                    lc3.link_button("🚀 알리", f"https://ko.aliexpress.com/w/wholesale-{en_kw.replace(' ','-')}.html", use_container_width=True)
    with 탭2:
        st.markdown("""<div style="background:rgba(3,199,90,0.1);padding:15px;border-radius:10px;border:1px solid #03C75A;margin-bottom:15px;">
        <p style="margin:0;color:#03C75A;"><b>👑 3대장 순정 렌즈 브릿지 안내</b><br>사이트를 미리 켜두신 후 이미지를 카메라 아이콘(📷)에 첨부하세요!</p></div>""", unsafe_allow_html=True)
        bc1,bc2,bc3 = st.columns(3)
        bc1.link_button("🇨🇳 타오바오 켜기", "https://s.taobao.com", use_container_width=True)
        bc2.link_button("🇨🇳 1688 켜기", "https://s.1688.com", use_container_width=True)
        bc3.link_button("✈️ 알리 켜기", "https://ko.aliexpress.com", use_container_width=True)
        st.divider()
        pr_g = paste_image_button(label="📋 사냥할 이미지 붙여넣기", background_color="#ff4500",
            hover_background_color="#e52e04", text_color="#ffffff", key="paste_bridge")
        g_img = None
        if pr_g.image_data is not None:
            pil = pr_g.image_data.convert('RGB'); pil.thumbnail((1200,1200))
            buf = io.BytesIO(); pil.save(buf,format="JPEG"); g_img = buf.getvalue()
        with st.expander("📱 앨범에서 사진 선택 (모바일용)", expanded=True):
            ug = st.file_uploader("사진 첨부", type=['jpg','jpeg','png'], key="up_g_bridge")
            if ug:
                pil = Image.open(io.BytesIO(ug.getvalue()))
                if pil.mode != 'RGB': pil = pil.convert('RGB')
                pil.thumbnail((1200,1200))
                buf = io.BytesIO(); pil.save(buf,format="JPEG"); g_img = buf.getvalue()
        if g_img:
            gc1, gc2 = st.columns([1,2])
            with gc1:
                st.image(g_img, width=280)
                st.download_button("💾 이미지 다운로드", data=g_img,
                    file_name="search_item.jpg", mime="image/jpeg", use_container_width=True)
            with gc2:
                if st.button("🤖 AI 현지어 키워드 추출", type="primary", use_container_width=True):
                    with st.spinner("스캔 중..."):
                        res = call_claude_api({"model":"claude-sonnet-4-6","max_tokens":100,
                            "messages":[{"role":"user","content":[
                                {"type":"image","source":{"type":"base64","media_type":"image/jpeg",
                                "data":base64.b64encode(g_img).decode("utf-8")}},
                                {"type":"text","text":"이 이미지 속 상품을 글로벌 도매 시장에서 찾기 위한 중국어 간체 키워드와 영어 키워드를 뽑아줘.\n출력형식:\n중국어: [키워드]\n영어: [키워드]"}
                            ]}]})
                    if res:
                        st.success("✅ 키워드 추출 완료!")
                        st.code(res)
                        cn_ai, en_ai = "상품", "item"
                        for line in res.split('\n'):
                            if '중국어:' in line: cn_ai = line.split('중국어:')[1].strip()
                            if '영어:'   in line: en_ai  = line.split('영어:')[1].strip()
                        lc1,lc2,lc3 = st.columns(3)
                        lc1.link_button("🚀 1688", f"https://s.1688.com/selloffer/offer_search.htm?keywords={cn_ai}", use_container_width=True)
                        lc2.link_button("🚀 타오바오", f"https://s.taobao.com/search?q={cn_ai}", use_container_width=True)
                        lc3.link_button("🚀 알리", f"https://ko.aliexpress.com/w/wholesale-{en_ai.replace(' ','-')}.html", use_container_width=True)

# ==========================================
# 🏪 상품 등록 도우미
# ==========================================
elif 메뉴 == "🏪 상품 등록 도우미":
    st.markdown("<h1>🏪 AI 상세페이지 기획기 (Royal Copywriter)</h1>", unsafe_allow_html=True)
    j_file = st.file_uploader("상품 사진 업로드", type=['jpg','jpeg','png'], key="j_up")
    if j_file:
        img_bytes = j_file.getvalue()
        cj1, cj2 = st.columns([1,2])
        with cj1: st.image(img_bytes, width=400)
        with cj2:
            p_info = st.text_input("상품명 또는 핵심 강조 포인트 (선택사항)", placeholder="예: 무소음, 파스텔 핑크")
            c1, c2 = st.columns(2)
            target = c1.selectbox("타겟 고객", ["전체","깐깐한 육아맘","가성비 따지는 자취생","트렌디한 2030 직장인","건강을 챙기는 5060"])
            tone   = c2.selectbox("글의 톤앤매너", ["감성을 자극하는 따뜻한 톤","전문가 느낌의 신뢰감 있는 톤","유머러스하고 친근한 톤","결핍을 찌르는 강력한 톤"])
            if st.button("✨ 황금 상세페이지 생성", type="primary", use_container_width=True, key="btn_desc_gen"):
                with st.spinner("왕실 카피라이터 작성 중..."):
                    b64 = base64.b64encode(img_bytes).decode("utf-8")
                    desc = call_claude_api({"max_tokens":2000,"messages":[{"role":"user","content":[
                        {"type":"image","source":{"type":"base64","media_type":j_file.type,"data":b64}},
                        {"type":"text","text":f"당신은 매출을 10배 올려주는 이커머스 카피라이터입니다.\n타겟:{target} / 톤:{tone} / 포인트:{p_info if p_info else '이미지 분석 기반'}"}
                    ]}]})
                    if desc:
                        st.session_state['helper_generated_text'] = desc
                        st.rerun()
    if st.session_state['helper_generated_text']:
        st.divider()
        st.markdown("### 📊 황금 상세페이지 기획안")
        st.markdown(st.session_state['helper_generated_text'])
        st.divider()
        st.text_area("📋 복사하기", value=st.session_state['helper_generated_text'], height=300, key="txt_area_desc")

# ==========================================
# 🕵️ 경쟁사 리뷰 분석기 (Full Spectrum)
# ==========================================
elif 메뉴 == "🕵️‍♂️ 경쟁사 리뷰 분석기":
    st.markdown("<h1>🕵️‍♂️ AI 경쟁사 리뷰 분석기 (Full Spectrum)</h1>", unsafe_allow_html=True)
    st.caption("경쟁사의 칭찬은 우리가 반드시 갖춰야 할 기준이고, 불만은 우리가 치고 들어갈 틈새입니다.")
    with st.container():
        st.markdown("### 1단계: 경쟁사 리뷰 가져오기")
        col_tip1, col_tip2 = st.columns(2)
        with col_tip1: st.info("⭐ **호평(4~5점)** — 고객이 왜 샀는지, 어떤 점이 만족스러웠는지")
        with col_tip2: st.warning("💢 **악평(1~3점)** — 어떤 점에서 실망했는지, 반품/환불 이유")
        good_reviews = st.text_area("👍 호평 리뷰 붙여넣기 (4~5점)", height=140, key="good_reviews",
            placeholder="예시:\n정말 편하고 디자인이 예뻐요. 선물용으로도 딱 좋아요!\n배송 빠르고 포장도 꼼꼼했어요. 재구매 의사 있어요.")
        bad_reviews = st.text_area("👎 악평 리뷰 붙여넣기 (1~3점)", height=140, key="bad_reviews",
            placeholder="예시:\n생각보다 내구성이 약해서 금방 망가졌어요.\n사진이랑 실제 색상이 너무 달라요.")
        분석모드 = st.radio("분석 모드", [
            "⚡ 풀스펙트럼 (호평+악평 동시)","👍 호평만 (장점 부각 전략)","👎 악평만 (Pain Point 전략)"
        ], horizontal=True, key="analysis_mode")

        if st.button("🔍 AI 전략 분석 시작", type="primary", use_container_width=True):
            has_good = good_reviews.strip() != ""
            has_bad  = bad_reviews.strip() != ""
            if "호평만" in 분석모드 and not has_good:
                st.warning("호평 리뷰를 입력해주세요!"); st.stop()
            elif "악평만" in 분석모드 and not has_bad:
                st.warning("악평 리뷰를 입력해주세요!"); st.stop()
            elif "풀스펙트럼" in 분석모드 and not has_good and not has_bad:
                st.warning("리뷰를 하나 이상 입력해주세요!"); st.stop()

            if "호평만" in 분석모드:
                prompt = f"""당신은 매출을 10배 올려주는 이커머스 카피라이터입니다.
[경쟁사 호평 리뷰]\n{good_reviews}
### ⭐ 고객이 진짜 원하는 것 TOP 3
### 🏆 우리가 반드시 갖춰야 할 필수 요소
### 💎 장점을 극대화하는 어필 포인트 5가지
### 🎯 구매 욕구를 자극하는 후킹 카피 3선
### 📣 SNS 리뷰 유도 문구 2가지"""
            elif "악평만" in 분석모드:
                prompt = f"""당신은 매출을 10배 올려주는 이커머스 카피라이터입니다.
[경쟁사 악평 리뷰]\n{bad_reviews}
### 🚨 고객 분노 핵심 결핍 TOP 3
### 💡 우리의 완벽한 해결책
### 🎣 결핍을 찌르는 후킹 카피 3선
### ⚠️ 절대 반복하면 안 될 실수 목록"""
            else:
                prompt = f"""당신은 매출을 10배 올려주는 이커머스 카피라이터입니다.
[경쟁사 호평]\n{good_reviews if has_good else '(입력없음)'}
[경쟁사 악평]\n{bad_reviews if has_bad else '(입력없음)'}
## ✅ PART 1 — 장점 전략
### ⭐ 고객이 진짜 원하는 것 TOP 3
### 💎 장점 극대화 어필 포인트 3가지
---
## 🔥 PART 2 — 약점 전략
### 🚨 고객 분노 핵심 결핍 TOP 3
### 💡 우리의 완벽한 해결책
---
## 👑 PART 3 — 통합 전략
### 🎯 최종 상세페이지 컨셉 한 줄 요약
### 🎣 장점+약점 동시 공략 후킹 카피 3선
### 📦 상세페이지 구성 순서 추천"""

            with st.spinner("경쟁사 완전 해부 중..."):
                result = call_claude_api({"max_tokens":2000,"messages":[{"role":"user","content":prompt}]})
            if result:
                st.divider()
                color = "#03C75A" if "호평만" in 분석모드 else "#ff4b4b" if "악평만" in 분석모드 else "#ffd700"
                label = "장점 부각 전략" if "호평만" in 분석모드 else "Pain Point 전략" if "악평만" in 분석모드 else "풀스펙트럼 전략"
                st.markdown(f"""<div style="padding:12px 20px;background:linear-gradient(90deg,{color}22,transparent);
border-left:3px solid {color};border-radius:8px;margin-bottom:20px;">
<h3 style="color:{color};margin:0;">📊 {label} 리포트</h3></div>""", unsafe_allow_html=True)
                st.markdown(result)
                st.divider()
                st.text_area("📋 복사하기", value=result, height=200, key="result_copy")

# ==========================================
# 💰 마진 계산기
# ==========================================
elif 메뉴 == "💰 마진 계산기":
    st.markdown("<h1>💰 스마트 묶음 마진 계산기</h1>", unsafe_allow_html=True)
    c1,c2,c3 = st.columns(3)
    buy_p  = c1.number_input("단품 도매가(매입가)", value=2900, step=100, key="buy_p")
    qty    = c2.number_input("판매 수량 (묶음 단위)", min_value=1, value=10, step=1, key="qty")
    ship_p = c3.number_input("건당 매입 배송비", value=2500, step=100, key="ship_p")
    st.divider()
    target_m = st.slider("🎯 목표 마진율 (%)", min_value=5, max_value=80, value=5, step=1)
    if st.button("🚀 플랫폼별 추천 판매가 계산", type="primary", use_container_width=True):
        total_cost = buy_p * qty + ship_p
        st.markdown(f"""<div style="padding:15px;background:rgba(255,215,0,0.1);border-radius:8px;margin-bottom:20px;">
<h4 style="color:#ffd700;margin:0;">📦 총 매입 원가: {total_cost:,}원</h4></div>""", unsafe_allow_html=True)
        for (name, fee), col in zip([("스마트스토어",0.00),("쿠팡(11%)",0.11),("11번가(13%)",0.13)], st.columns(3)):
            rec = total_cost / (1 - fee - 0.036 - target_m/100)
            margin = rec * (target_m/100)
            with col:
                st.success(f"🛒 {name}")
                st.metric("추천 판매가", f"{int(rec):,}원")
                st.write(f"💵 마진액: **{int(margin):,}원**")
                if qty > 1:
                    st.caption(f"1개당: {int(rec/qty):,}원 / 마진 {int(margin/qty):,}원")

# ==========================================
# 📦 재고/가격 알림
# ==========================================
elif 메뉴 == "📦 재고/가격 알림":
    st.markdown("<h1>📦 공급처 가격 및 재고 감시</h1>", unsafe_allow_html=True)
    def mask(cid): return cid[:3]+"****"+cid[-2:] if cid else "미등록"
    st.info(f"🔔 텔레그램 수신 ID: {mask(TELEGRAM_CHAT_ID)}")
    재고파일 = "재고모니터링.json"
    def 로드(): return json.load(open(재고파일,'r',encoding='utf-8')) if os.path.exists(재고파일) else []
    def 저장(d): json.dump(d, open(재고파일,'w',encoding='utf-8'), ensure_ascii=False, indent=2)
    목록 = 로드()
    with st.expander("➕ 감시 상품 추가", expanded=True):
        c1, c2 = st.columns([2,1])
        n_no   = c1.text_input("도매꾹 상품번호", key="n_no")
        n_name = c2.text_input("관리 이름", key="n_name")
        if st.button("👑 모니터링 명단에 등록", use_container_width=True):
            r = requests.get("https://domeggook.com/ssl/api/", params={"ver":"4.1","aid":DOMEGGOOK_API_KEY,
                "market":"dome","om":"json","mode":"getItemList","itemNo":n_no}).json()
            if 'domeggook' in r and 'list' in r['domeggook'] and 'item' in r['domeggook']['list']:
                it = r['domeggook']['list']['item']
                it = it[0] if isinstance(it,list) else it
                if it:
                    목록.append({"no":n_no,"name":n_name,"price":int(it['price']),"상태":"판매중"})
                    저장(목록); st.success("등록되었습니다."); st.rerun()
    st.divider()
    if st.button("🔄 전수 점검 및 텔레그램 발송", type="primary", use_container_width=True):
        with st.spinner("전수 확인 중..."):
            for i, s in enumerate(목록):
                r = requests.get("https://domeggook.com/ssl/api/", params={"ver":"4.1","aid":DOMEGGOOK_API_KEY,
                    "market":"dome","om":"json","mode":"getItemList","itemNo":s['no']}).json()
                if 'domeggook' in r and 'list' in r['domeggook'] and 'item' in r['domeggook']['list']:
                    it = r['domeggook']['list']['item']
                    it = it[0] if isinstance(it,list) else it
                    if it:
                        now_p = int(it['price'])
                        if now_p > s['price']:
                            send_telegram(f"🔺 <b>가격인상!</b>\n{s['name']}\n{s['price']:,}원→<b>{now_p:,}원</b>")
                        목록[i]['price'] = now_p; 목록[i]['상태'] = "판매중"
                else:
                    if s['상태'] == "판매중":
                        send_telegram(f"🚫 <b>품절!</b>\n{s['name']} 품절발생")
                        목록[i]['상태'] = "품절"
            저장(목록); st.success("전수 점검 완료!"); st.rerun()
    st.divider()
    st.markdown("### 📋 감시 중인 영토")
    for idx, s in enumerate(목록):
        c1,c2,c3,c4 = st.columns([3,1,1,1])
        c1.markdown(f"**{s['name']}** <span style='color:#777;font-size:.8rem;'>({s['no']})</span>", unsafe_allow_html=True)
        c2.markdown(f"<strong style='color:#ffd700;'>{s['price']:,}원</strong>", unsafe_allow_html=True)
        sc = "color:#03C75A;font-weight:bold;" if s['상태']=="판매중" else "color:#ff4b4b;font-weight:bold;"
        c3.markdown(f"<span style='{sc}'>{s['상태']}</span>", unsafe_allow_html=True)
        if c4.button("삭제", key=f"d_{idx}", type="secondary"):
            목록.pop(idx); 저장(목록); st.rerun()

# ==========================================
# 💎 블루오션 탐지 + 자동추천
# ==========================================
elif 메뉴 == "💎 블루오션 탐지 + 🤖 자동추천":
    st.markdown("<h1>💎 블루오션 탐지 + 🤖 AI 자동 일일추천</h1>", unsafe_allow_html=True)
    탭1, 탭2 = st.tabs(["🔍 단일 키워드 분석", "🚀 AI 자동 일일추천"])

    with 탭1:
        st.caption("키워드 입력 → 네이버 경쟁강도 즉시 분석")
        cb1, cb2 = st.columns([3,1])
        bkw     = cb1.text_input("분석할 키워드 입력", key="input_blue_kw")
        btn_ana = cb2.button("실시간 시장 분석", type="primary", key="btn_blue_ana")
        if btn_ana and bkw:
            with st.spinner("분석 중..."):
                total = 네이버검색(bkw).get('total', 0)
            st.metric("네이버 등록 상품수", f"{total:,}개")
            st.divider()
            if total < 2000:   st.success("🏆 확실한 블루오션! 지금 바로 소싱하세요."); st.balloons()
            elif total < 10000: st.info("🟢 경쟁해볼 만한 시장입니다.")
            else:               st.error("🔴 레드오션입니다. 다른 키워드를 추천합니다.")

    with 탭2:
        월 = datetime.now().month
        st.caption(f"AI 트렌드 분석 → 블루오션 스캔 → 최저가 소싱 → HTML 상세페이지 자동 생성·저장 | 📅 현재 {월}월 시즌 자동 반영")

        cs1,cs2,cs3 = st.columns(3)
        카테고리  = cs1.selectbox("타겟 카테고리", ["자동 탐지 (AI 추천)","생활용품","주방용품","뷰티/헬스","반려동물","스포츠/레저","디지털/가전","패션잡화","유아동"], key="sel_category")
        타겟가격대 = cs2.selectbox("타겟 판매가대", ["전체","1만원 이하","1~3만원","3~5만원","5만원 이상"], key="sel_price_range")
        추천수    = cs3.number_input("추천 상품 수", min_value=3, max_value=10, value=5, key="num_recommend")
        send_tg   = st.checkbox("📲 완료 후 텔레그램 발송", value=True, key="chk_telegram")
        st.divider()

        이력data = 이력_로드()
        총kw수   = sum(len(v) for v in 이력data.values())
        ch1,ch2,ch3 = st.columns([2,2,1])
        ch1.metric("📋 누적 추천 키워드", f"{총kw수}개")
        ch2.metric("📅 추천 실행 일수", f"{len(이력data)}일")
        with ch3:
            if st.button("🗑️ 이력 초기화", key="btn_reset_history", type="secondary"):
                if os.path.exists(이력파일): os.remove(이력파일)
                st.success("초기화 완료!"); st.rerun()

        if 이력data:
            with st.expander("📖 날짜별 추천 이력"):
                for 날짜, kw_list in sorted(이력data.items(), reverse=True):
                    st.markdown(f"**{날짜}** — {', '.join(kw_list)}")

        saved_files = sorted(glob.glob("상세페이지_저장/*.html"), reverse=True)
        if saved_files:
            with st.expander(f"📂 저장된 HTML 상세페이지 ({len(saved_files)}개)"):
                for fp in saved_files:
                    fname = os.path.basename(fp)
                    cf1, cf2 = st.columns([4,1])
                    cf1.markdown(f"📄 `{fname}`")
                    with open(fp,'r',encoding='utf-8') as fh:
                        cf2.download_button("⬇️", data=fh.read(), file_name=fname, mime="text/html", key=f"dl_saved_{fname}")
        st.divider()

        if st.button("🚀 AI 자동 분석 시작 — 오늘의 황금 상품 사냥", type="primary", use_container_width=True, key="btn_auto_daily"):
            결과_목록 = []
            st.markdown("### 🧠 STEP 1 — AI 트렌드 + 시즌 분석")
            with st.spinner("Claude AI가 블루오션 키워드 분석 중..."):
                키워드목록 = ai_트렌드_키워드_생성(카테고리, 타겟가격대, 추천수)
            if not 키워드목록: st.error("키워드 생성 실패."); st.stop()
            st.success(f"✅ {len(키워드목록)}개 키워드 생성 완료!")
            이력_저장(datetime.now().strftime('%Y-%m-%d'), [it['keyword'] for it in 키워드목록])

            st.markdown("### 📊 STEP 2 — 네이버 경쟁강도 분석")
            키워드목록 = 경쟁강도_필터(키워드목록)

            st.markdown("### 💎 STEP 3 — 소싱 & HTML 상세페이지 자동 생성")
            tg_msg = f"👑 <b>오늘의 위탁왕 자동추천</b> ({datetime.now().strftime('%Y-%m-%d')})\n\n"

            for idx, item in enumerate(키워드목록):
                kw_item     = item['keyword']
                icon        = '🟢' if item['score']=='상' else '🟡' if item['score']=='중' else '🔴'
                ocean_label = item['ocean']
                season_tag  = item.get('season','')

                with st.expander(f"{icon} #{idx+1} [{ocean_label}] **{kw_item}** {season_tag} — 경쟁{item['total_count']:,}개", expanded=(idx==0)):
                    ca, cb = st.columns([2,1])
                    with ca:
                        st.markdown(f"**추천 이유:** {item['reason']}")
                        st.markdown(f"**예상 가격대:** {item['price_range']}")
                        st.markdown(f"**경쟁 강도:** {ocean_label}")
                        if season_tag: st.markdown(f"**시즌:** {season_tag}")
                    with cb:
                        with st.spinner("소싱 확인 중..."):
                            소싱 = 소싱데이터_조회(kw_item)
                        if 소싱:
                            st.metric("최저 소싱가", f"{소싱['총가격']:,}원")
                            st.caption(f"출처: {소싱['출처']}")
                            if 소싱.get('이미지'): st.image(소싱['이미지'], width=120)
                            st.link_button("소싱처 →", 소싱['링크'])
                        else: st.warning("소싱 데이터 없음")

                    st.divider()
                    with st.spinner(f"'{kw_item}' HTML 생성 중..."):
                        ai_text, html_str, filepath = ai_상세페이지_생성_및_저장(kw_item, 소싱, item['reason'], ocean_label, idx)

                    if ai_text:
                        st.markdown("#### 📄 AI 자동 생성 상세페이지")
                        st.markdown(ai_text)
                        if html_str and filepath:
                            fname = os.path.basename(filepath)
                            st.download_button(f"⬇️ HTML 다운로드 ({fname})", data=html_str,
                                file_name=fname, mime="text/html", key=f"dl_now_{idx}",
                                use_container_width=True, type="primary")
                            st.success(f"✅ 저장완료: 상세페이지_저장/{fname}")
                        st.text_area("📋 복사하기", value=ai_text, height=150, key=f"copy_{idx}")
                        소싱가_txt = f"{소싱['총가격']:,}원 ({소싱['출처']})" if 소싱 else "미확인"
                        결과_목록.append({"keyword":kw_item,"ocean":ocean_label,"count":item['total_count'],
                            "소싱가":소싱['총가격'] if 소싱 else 0,"출처":소싱['출처'] if 소싱 else "-",
                            "html_file":os.path.basename(filepath) if filepath else "-"})
                        tg_msg += f"{idx+1}. <b>{kw_item}</b> {ocean_label} | 소싱가:{소싱가_txt}\n\n"

            if send_tg and 결과_목록:
                tg_msg += f"총 <b>{len(결과_목록)}개</b> 완료 ✅ | HTML {len(결과_목록)}개 저장됨"
                send_telegram(tg_msg); st.success("📲 텔레그램 발송 완료!")

            if 결과_목록:
                st.divider()
                st.markdown("### 🏆 오늘의 추천 상품 최종 요약")
                st.dataframe(pd.DataFrame([{"순위":i+1,"키워드":r['keyword'],"경쟁강도":r['ocean'],
                    "경쟁수":f"{r['count']:,}개","소싱가":f"{r['소싱가']:,}원" if r['소싱가'] else "미확인",
                    "출처":r['출처'],"파일":r['html_file']} for i,r in enumerate(결과_목록)]),
                    use_container_width=True, hide_index=True)
                zip_buf = _io.BytesIO()
                with zipfile.ZipFile(zip_buf,'w') as zf:
                    for r in 결과_목록:
                        fp = os.path.join("상세페이지_저장", r['html_file'])
                        if os.path.exists(fp):
                            with open(fp,'r',encoding='utf-8') as fh: zf.writestr(r['html_file'], fh.read())
                zip_buf.seek(0)
                st.download_button("📦 전체 ZIP 다운로드", data=zip_buf.getvalue(),
                    file_name=f"위탁왕_{datetime.now().strftime('%Y%m%d')}.zip",
                    mime="application/zip", use_container_width=True)

# ==========================================
# 🏷️ 상품명 최적화
# ==========================================
elif 메뉴 == "🏷️ 상품명 최적화":
    st.markdown("<h1>🏷️ 스마트스토어 상품명 자동 완성기</h1>", unsafe_allow_html=True)
    st.caption("네이버 쇼핑 알고리즘에 최적화된 상품명을 SEO 점수와 함께 자동 생성합니다.")
    st.markdown("""<div style="background:rgba(255,215,0,0.06);border:1px solid rgba(255,215,0,0.15);
    border-radius:12px;padding:16px 20px;margin-bottom:20px;">
    <b style="color:#ffd700;">📐 네이버 쇼핑 최적 공식</b><br>
    <span style="color:#ccc;font-size:.9rem;">[브랜드] + [핵심키워드] + [세부속성] + [타겟/용도] + [감성형용사]<br>
    예: <b style="color:#03C75A;">무소음 얼음틀 실리콘 대용량 뚜껑있는 가정용 아이스큐브</b></span></div>""",
    unsafe_allow_html=True)

    cn1, cn2 = st.columns([3,1])
    nm_kw  = cn1.text_input("상품 키워드 또는 특징 입력", placeholder="예: 실리콘 얼음틀, 무선 가습기")
    nm_cat = cn2.selectbox("카테고리", ["자동감지","생활용품","주방","뷰티","스포츠","디지털","패션","유아동"], key="nm_cat")
    cn3,cn4,cn5 = st.columns(3)
    nm_target = cn3.selectbox("주 타겟", ["전체","육아맘","자취생","직장인","캠퍼","시니어"], key="nm_target")
    nm_price  = cn4.selectbox("가격대", ["1만원 이하","1~3만원","3~5만원","5만원 이상"], key="nm_price")
    nm_tone   = cn5.selectbox("강조 포인트", ["가성비","프리미엄","친환경/안전","디자인/감성","기능성"], key="nm_tone")

    if st.button("✨ 최적 상품명 5종 + SEO 분석 생성", type="primary", use_container_width=True):
        if not nm_kw.strip():
            st.warning("상품 키워드를 입력해 주세요!")
        else:
            with st.spinner("네이버 알고리즘 맞춤 상품명 생성 중..."):
                prompt = f"""당신은 네이버 쇼핑 SEO 전문가입니다.
상품: {nm_kw} / 카테고리: {nm_cat} / 타겟: {nm_target} / 가격대: {nm_price} / 강조: {nm_tone}
네이버 쇼핑 상위노출 최적화 상품명 5개를 생성하세요.
규칙: 100자 이내, 핵심 키워드 앞쪽 배치, 세부속성 포함, 자연스러운 나열
[출력] JSON만. 설명 없음.
{{"titles":[
  {{"rank":1,"title":"상품명","keywords":["키워드1","키워드2"],"seo_score":85,"reason":"효과적인 이유 한 줄"}},
  {{"rank":2,"title":"상품명","keywords":[...],"seo_score":82,"reason":"..."}},
  {{"rank":3,"title":"상품명","keywords":[...],"seo_score":79,"reason":"..."}},
  {{"rank":4,"title":"상품명","keywords":[...],"seo_score":76,"reason":"..."}},
  {{"rank":5,"title":"상품명","keywords":[...],"seo_score":73,"reason":"..."}}
],
"avoid":["피해야할표현1","피해야할표현2","피해야할표현3"],
"tip":"상위노출 핵심 팁 한 줄"}}"""
                res = call_claude_api({"max_tokens":2000,"messages":[{"role":"user","content":prompt}]})

            if res:
                try:
                    data   = json.loads(res.replace("```json","").replace("```","").strip())
                    titles = data.get("titles",[])
                    avoid  = data.get("avoid",[])
                    tip    = data.get("tip","")
                    st.divider()
                    st.markdown("### 🏆 추천 상품명 TOP 5")
                    for item in titles:
                        score  = item.get("seo_score",0)
                        bc     = "#03C75A" if score>=80 else "#ffd700" if score>=70 else "#ff4b4b"
                        medal  = ["🥇","🥈","🥉","4️⃣","5️⃣"][item["rank"]-1]
                        badges = "".join([f'<span style="background:rgba(255,215,0,.1);border:1px solid rgba(255,215,0,.3);color:#ffd700;padding:2px 8px;border-radius:12px;font-size:.78rem;margin-right:5px;">{k}</span>' for k in item.get("keywords",[])])
                        bar_w  = min(score * 2, 200)
                        st.markdown(f"""<div style="background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.07);
border-radius:12px;padding:18px 22px;margin-bottom:12px;">
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
  <span style="font-size:1.1rem;font-weight:700;color:#e8eaf0;">{medal} {item['title']}</span>
  <span style="color:{bc};font-weight:800;">SEO {score}</span>
</div>
<div style="background:rgba(255,255,255,.06);border-radius:4px;height:6px;margin-bottom:10px;">
  <div style="width:{bar_w}px;max-width:100%;background:{bc};height:6px;border-radius:4px;"></div>
</div>
<div style="margin-bottom:8px;">{badges}</div>
<span style="color:#8892a4;font-size:.85rem;">💡 {item.get('reason','')}</span>
</div>""", unsafe_allow_html=True)
                        st.code(item["title"], language=None)
                    if avoid:
                        st.divider()
                        st.markdown("### ⚠️ 이런 표현은 피하세요")
                        html_avoid = " ".join([f'<span style="background:rgba(255,75,75,.1);border:1px solid rgba(255,75,75,.3);color:#ff8080;padding:4px 12px;border-radius:20px;font-size:.85rem;margin-right:6px;">{a}</span>' for a in avoid])
                        st.markdown(html_avoid, unsafe_allow_html=True)
                    if tip:
                        st.divider()
                        st.markdown(f"""<div style="background:rgba(3,199,90,.08);border-left:3px solid #03C75A;border-radius:8px;padding:14px 18px;">
<b style="color:#03C75A;">👑 상위노출 핵심 팁</b><br><span style="color:#ccc;font-size:.92rem;">{tip}</span></div>""", unsafe_allow_html=True)
                except:
                    st.markdown(res)
            else:
                st.error("AI 서버 오류. 다시 시도해주세요.")

# ==========================================
# 🖼️ 썸네일 메이커
# ==========================================
elif 메뉴 == "🖼️ 썸네일 메이커":
    st.markdown("<h1>🖼️ AI 썸네일 메이커 (포토샵 없이 완성)</h1>", unsafe_allow_html=True)
    st.caption("상품 이미지에 배지·텍스트를 자동 합성해 스마트스토어·쿠팡에 바로 업로드 가능한 800×800 썸네일을 만들어드립니다.")

    up_thumb = st.file_uploader("📷 상품 이미지 업로드", type=["jpg","jpeg","png"], key="up_thumb")

    if up_thumb:
        pil_orig = Image.open(io.BytesIO(up_thumb.getvalue())).convert("RGBA")
        pil_orig = pil_orig.resize((800,800), Image.LANCZOS)
        st.divider()
        ct1, ct2 = st.columns([1,1])

        with ct1:
            st.markdown("### ⚙️ 배지 설정")
            badge_type = st.selectbox("배지 종류", [
                "없음","🔥 오늘만 특가","🚀 무료배송","⭐ 베스트셀러",
                "🆕 신상품","💎 한정수량","✅ 안전인증","직접 입력"
            ], key="badge_type")
            custom_badge = st.text_input("배지 텍스트 직접 입력", placeholder="예: 1+1 증정", key="custom_badge") if badge_type == "직접 입력" else (badge_type.split(" ",1)[-1] if badge_type != "없음" else "")
            badge_pos   = st.selectbox("배지 위치", ["좌상단","우상단","좌하단","우하단"], key="badge_pos")
            badge_color = st.selectbox("배지 색상", ["레드(긴급)","골드(프리미엄)","그린(신뢰)","블루(신상)"], key="badge_color")
            st.markdown("### 📝 텍스트 오버레이")
            main_text    = st.text_input("메인 텍스트 (하단 크게)", placeholder="예: 가성비 1위", key="main_text")
            sub_text     = st.text_input("서브 텍스트 (메인 아래)", placeholder="예: 무료배송·당일출고", key="sub_text")
            dark_overlay = st.checkbox("하단 어두운 배경 추가 (텍스트 가독성 향상)", value=True, key="dark_overlay")

        with ct2:
            st.markdown("### 👁️ 미리보기")
            img  = pil_orig.copy()
            draw = ImageDraw.Draw(img)
            SIZE = 800

            color_map = {
                "레드(긴급)":     ((220,38,38),  (255,255,255)),
                "골드(프리미엄)": ((180,140,0),  (255,255,255)),
                "그린(신뢰)":     ((3,180,90),   (255,255,255)),
                "블루(신상)":     ((37,99,235),  (255,255,255)),
            }
            bg_col, txt_col = color_map.get(badge_color, ((220,38,38),(255,255,255)))

            if badge_type != "없음" and custom_badge:
                b_w, b_h = 220, 52
                pad = 20
                pos_map = {"좌상단":(pad,pad),"우상단":(SIZE-b_w-pad,pad),
                           "좌하단":(pad,SIZE-b_h-pad),"우하단":(SIZE-b_w-pad,SIZE-b_h-pad)}
                bx, by = pos_map[badge_pos]
                draw.rounded_rectangle([bx,by,bx+b_w,by+b_h], radius=10, fill=bg_col)
                try: fb = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
                except: fb = ImageFont.load_default()
                bb = draw.textbbox((0,0), custom_badge, font=fb)
                tw, th = bb[2]-bb[0], bb[3]-bb[1]
                draw.text((bx+(b_w-tw)//2, by+(b_h-th)//2), custom_badge, font=fb, fill=txt_col)

            if dark_overlay and (main_text or sub_text):
                ov = Image.new("RGBA",(SIZE,SIZE),(0,0,0,0))
                od = ImageDraw.Draw(ov)
                for i in range(220):
                    od.rectangle([0,SIZE-220+i,SIZE,SIZE-219+i], fill=(0,0,0,int(185*(i/220))))
                img = Image.alpha_composite(img, ov)
                draw = ImageDraw.Draw(img)

            try:
                f_main = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
                f_sub  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 27)
            except:
                f_main = f_sub = ImageFont.load_default()

            if main_text:
                bb = draw.textbbox((0,0), main_text, font=f_main)
                draw.text(((SIZE-(bb[2]-bb[0]))//2, SIZE-165), main_text, font=f_main, fill=(255,215,0))
            if sub_text:
                bb = draw.textbbox((0,0), sub_text, font=f_sub)
                draw.text(((SIZE-(bb[2]-bb[0]))//2, SIZE-105), sub_text, font=f_sub, fill=(210,210,210))

            img_rgb = img.convert("RGB")
            st.image(img_rgb, use_container_width=True, caption="합성 미리보기")

        st.divider()
        buf = io.BytesIO()
        img_rgb.save(buf, format="JPEG", quality=95)
        buf.seek(0)
        st.download_button("⬇️ 완성 썸네일 다운로드 (JPEG 800×800)",
            data=buf.getvalue(),
            file_name=f"썸네일_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg",
            mime="image/jpeg", use_container_width=True, type="primary")
        st.info("💡 800×800 정사각형 — 스마트스토어·쿠팡 대표이미지 권장 규격입니다.")

# ==========================================
# 🔬 경쟁사 상품명 역분석
# ==========================================
elif 메뉴 == "🔬 경쟁사 상품명 역분석":
    st.markdown("<h1>🔬 경쟁사 상품명 역분석 (상위노출 패턴 해독기)</h1>", unsafe_allow_html=True)
    st.caption("네이버 쇼핑 1~20위 상품명을 AI가 분석해 상위노출을 만드는 키워드 패턴을 해독합니다.")

    cr1, cr2 = st.columns([3,1])
    rev_kw    = cr1.text_input("분석할 키워드 입력", placeholder="예: 실리콘 얼음틀", key="rev_kw")
    rev_count = cr2.number_input("분석 상품수", min_value=5, max_value=20, value=10, key="rev_count")

    if st.button("🔬 상위노출 패턴 분석 시작", type="primary", use_container_width=True):
        if not rev_kw.strip():
            st.warning("키워드를 입력해 주세요!")
        else:
            with st.spinner(f"네이버 상위 {rev_count}개 상품명 수집 중..."):
                naver_res = 네이버검색(rev_kw, 개수=rev_count)
                items     = naver_res.get("items",[])
                total     = naver_res.get("total",0)

            if not items:
                st.error("검색 결과가 없습니다.")
            else:
                titles_list = [it['title'].replace('<b>','').replace('</b>','') for it in items]
                st.success(f"✅ 상위 {len(titles_list)}개 수집 완료 (전체 {total:,}개 중)")

                with st.expander("📋 수집된 상품명 원본 보기"):
                    for i, (t, it) in enumerate(zip(titles_list, items), 1):
                        st.markdown(f"**{i}.** {t} — <span style='color:#03C75A;'>{int(it.get('lprice',0)):,}원</span>", unsafe_allow_html=True)

                with st.spinner("AI가 상위노출 패턴 해독 중..."):
                    titles_text = "\n".join([f"{i}. {t}" for i,t in enumerate(titles_list,1)])
                    prompt = f"""당신은 네이버 쇼핑 SEO 전문가입니다.
'{rev_kw}' 키워드의 네이버 쇼핑 상위 {len(titles_list)}개 상품명을 분석하여 상위노출 패턴을 해독하세요.

[수집된 상품명]
{titles_text}

### 🔑 핵심 공통 키워드 TOP 10 (등장 빈도 포함)
### 📐 상위노출 상품명 구조 패턴 (도식화)
### ⚡ 차별화 기회 — 아무도 안 쓴 키워드
### 🏆 이 분석 기반 최적 상품명 3가지 제안
### 📊 가격대 분석 및 우리의 최적 포지션"""
                    result = call_claude_api({"max_tokens":2000,"messages":[{"role":"user","content":prompt}]})

                if result:
                    st.divider()
                    st.markdown("""<div style="padding:12px 20px;background:linear-gradient(90deg,rgba(255,215,0,.1),transparent);
border-left:3px solid #ffd700;border-radius:8px;margin-bottom:20px;">
<h3 style="color:#ffd700;margin:0;">👑 상위노출 패턴 분석 리포트</h3></div>""", unsafe_allow_html=True)
                    st.markdown(result)
                    st.divider()
                    st.text_area("📋 복사하기", value=result, height=200, key="rev_copy")

                    body_html = re.sub(r'### (.+)',r'<h3>\1</h3>', result)
                    body_html = re.sub(r'\*\*(.+?)\*\*',r'<strong>\1</strong>', body_html)
                    body_html = body_html.replace('\n\n','</p><p>').replace('\n','<br>')
                    today_str = datetime.now().strftime('%Y년 %m월 %d일')
                    html_report = f"""<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8">
<title>🔬 {rev_kw} 역분석</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;700&display=swap" rel="stylesheet">
<style>*{{margin:0;padding:0;box-sizing:border-box}}body{{background:#07080f;color:#e8eaf0;font-family:'Noto Sans KR',sans-serif;padding:40px 24px}}
.wrap{{max-width:860px;margin:0 auto}}h1{{color:#ffd700;font-size:2rem;margin-bottom:6px}}
.sub{{color:#8892a4;font-size:.9rem;margin-bottom:28px}}
.card{{background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.07);border-radius:16px;padding:28px 32px}}
h3{{color:#ffd700;font-size:1rem;margin:18px 0 8px}}p{{color:#8892a4;font-size:.93rem;margin-bottom:8px}}
strong{{color:#e8eaf0}}footer{{margin-top:36px;text-align:center;color:#8892a4;font-size:.8rem}}footer strong{{color:#ffd700}}</style></head>
<body><div class="wrap"><h1>🔬 {rev_kw} 상위노출 패턴 분석</h1>
<div class="sub">{today_str} · 상위 {len(titles_list)}개 분석 · 위탁의왕 Ultra</div>
<div class="card"><p>{body_html}</p></div>
<footer>Generated by <strong>👑 위탁의왕 Ultra</strong> · Powered by Claude AI</footer></div></body></html>"""
                    st.download_button("📥 분석 리포트 HTML 다운로드", data=html_report,
                        file_name=f"역분석_{rev_kw}_{datetime.now().strftime('%Y%m%d')}.html",
                        mime="text/html", use_container_width=True)
