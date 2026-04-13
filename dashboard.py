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
if 'pkg_outputs'           not in st.session_state: st.session_state['pkg_outputs'] = {}

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
                             headers=headers, json=body, timeout=180)
        if resp.status_code == 200:
            text = resp.json()["content"][0]["text"].strip()
            text = re.sub(r'```[^\n]*\n?', '', text)
            text = text.replace('~~', '~')     # ✅ 취소선 → 물결 하나로 교체
            return text.strip()
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
    url = "https://domeggook.com/ssl/api/"

    def _fetch(kw):
        params = {"ver":"4.1","mode":"getItemList","aid":DOMEGGOOK_API_KEY,
                  "om":"json","kw":kw,"sz":50,"market":"dome"}
        try:
            data      = requests.get(url, params=params, timeout=10).json()
            list_data = data.get('domeggook',{}).get('list',{})
            if not list_data: return []
            items = list_data.get('item')
            if not items: return []
            if isinstance(items, dict): items = [items]
            결과 = []
            for item in items:
                p   = int(item.get('price') or 0)
                f   = int((item.get('deli') or {}).get('fee') or 0)
                qty = int(item.get('unitQty') or 1)
                if (item.get('deli') or {}).get('who') == 'S': f = 0
                if p <= 0: continue
                결과.append({
                    "제목":   item.get('title',''),
                    "가격":   p,
                    "배송비": f,
                    "총가격": p + f,
                    "이미지": item.get('thumb',''),
                    "링크":   item.get('url',''),
                    "출처":   "도매꾹"
                })
            return 결과
        except: return []

    # 1차: 원래 검색어
    결과 = _fetch(검색어)
    # 2차: 결과 없으면 첫 단어로 재시도
    if not 결과 and ' ' in 검색어:
        결과 = _fetch(검색어.split()[0])

    return sorted(결과, key=lambda x: x['총가격'])

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
<img src="{best['이미지']}" style="width:100%;border-radius:8px;margin-bottom:10px;">
<h4 style="color:#ffd700;margin:0 0 6px 0;">단가 {best.get('총가격',best.get('가격')):,}원</h4>
<p style="color:#ccc;font-size:.8rem;margin:0 0 10px 0;height:40px;overflow:hidden;">{best['제목'][:40]}...</p>
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
<span style="color:#03C75A;font-weight:bold;font-size:1.2rem;">단가 {item['총가격']:,}원</span>
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

# ── 멀티플랫폼 가격 체크 (전역 — 재고메뉴 + 자동스케줄러 공용) ──
PLATFORM_ICONS = {
    "도매꾹": "🔵", "11번가": "🔴",
    "네이버": "🟢", "G마켓":  "🟡", "옥션": "🟠",
}

def 가격체크_도매꾹(item_no):
    try:
        r = requests.get("https://domeggook.com/ssl/api/", timeout=10, params={
            "ver":"4.1","aid":DOMEGGOOK_API_KEY,"market":"dome",
            "om":"json","mode":"getItemList","itemNo":item_no}).json()
        list_data = r.get('domeggook',{}).get('list',{})
        if not list_data: return None, "품절"
        it = list_data.get('item')
        if not it: return None, "품절"
        it = it[0] if isinstance(it, list) else it
        return int(it.get('price', 0) or 0), "판매중"
    except: return None, "오류"

def 가격체크_URL(url, 플랫폼):
    ua = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
          "AppleWebKit/537.36 (KHTML, like Gecko) "
          "Chrome/120.0.0.0 Safari/537.36")
    headers = {"User-Agent": ua, "Accept-Language": "ko-KR,ko;q=0.9"}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        text = resp.text
        patterns = [
            r'"price"\s*:\s*"?(\d{3,8})"?',
            r'"salePrice"\s*:\s*(\d{3,8})',
            r'"finalPrice"\s*:\s*(\d{3,8})',
            r'"sellingPrice"\s*:\s*(\d{3,8})',
            r'"discountedPrice"\s*:\s*(\d{3,8})',
            r'data-price="(\d{3,8})"',
            r'"currentPrice"\s*:\s*(\d{3,8})',
        ]
        if 플랫폼 == "11번가":
            patterns = [r'"price"\s*:\s*(\d{3,8})', r'itemprop="price"[^>]*content="(\d{3,8})"'] + patterns
        elif 플랫폼 in ["G마켓","옥션"]:
            patterns = [r'data-price="(\d{3,8})"', r'"itemPrice"\s*:\s*(\d{3,8})'] + patterns
        elif 플랫폼 == "네이버":
            patterns = [r'"wholeSalePrice"\s*:\s*(\d{3,8})', r'"benefitPrice"\s*:\s*(\d{3,8})'] + patterns
        for pat in patterns:
            m = re.search(pat, text)
            if m:
                p = int(m.group(1).replace(',',''))
                if 500 <= p <= 9_999_999:
                    return p, "판매중"
        if any(k in text for k in ['품절','일시품절','soldout','SOLDOUT','판매중지']):
            return None, "품절"
        return None, "확인불가"
    except: return None, "오류"

# ── 자동 점검 함수 (스케줄러 + 수동 점검 공용) ──────────────────
점검기록파일 = "자동점검기록.json"

def 자동_가격체크(source="자동"):
    # 중복 실행 방지
    now     = datetime.now()
    now_key = now.strftime('%Y%m%d%H')
    if os.path.exists(점검기록파일):
        try:
            last = json.load(open(점검기록파일,'r',encoding='utf-8'))
            if source == "자동" and last.get('last_key') == now_key:
                return
        except: pass

    # ── Google Sheets에서 목록 로드 ──────────────────────────────
    def _스케줄러_로드():
        try:
            import gspread
            from google.oauth2.service_account import Credentials
            scopes = ["https://spreadsheets.google.com/feeds",
                      "https://www.googleapis.com/auth/drive"]
            creds = Credentials.from_service_account_info(
                dict(st.secrets["gcp_service_account"]), scopes=scopes)
            gc   = gspread.authorize(creds)
            sh   = gc.open_by_key(st.secrets["SPREADSHEET_ID"])
            ws   = sh.worksheet("재고감시")
            recs = ws.get_all_records()
            for r in recs:
                r['price'] = int(r.get('price', 0) or 0)
            return recs, ws
        except:
            # Google Sheets 미연동 → 로컬 fallback
            재고파일_path = "재고모니터링.json"
            if not os.path.exists(재고파일_path):
                return [], None
            목록 = json.load(open(재고파일_path,'r',encoding='utf-8'))
            return 목록, None

    def _스케줄러_저장(목록, ws):
        try:
            if ws:
                ws.clear()
                ws.append_row(["no","name","platform","url","price","상태"])
                for item in 목록:
                    ws.append_row([item.get('no',''), item.get('name',''),
                                   item.get('platform','도매꾹'), item.get('url',''),
                                   item.get('price',0), item.get('상태','판매중')])
            else:
                재고파일_path = "재고모니터링.json"
                json.dump(목록, open(재고파일_path,'w',encoding='utf-8'), ensure_ascii=False, indent=2)
        except Exception as e:
            send_telegram(f"⚠️ 저장 오류: {str(e)[:100]}")

    try:
        목록, ws = _스케줄러_로드()
        if not 목록: return

        변경_내용 = []
        for i, s in enumerate(목록):
            플랫폼 = s.get('platform','도매꾹')
            if 플랫폼 == "도매꾹":
                now_p, now_st = 가격체크_도매꾹(s.get('no',''))
            else:
                now_p, now_st = 가격체크_URL(s['url'], 플랫폼)
            icon = PLATFORM_ICONS.get(플랫폼,"⚪")
            if now_p and now_p > s['price']:
                diff = now_p - s['price']
                send_telegram(f"🔺 <b>가격인상!</b> {icon}{플랫폼}\n📦 {s['name']}\n{s['price']:,}원 → <b>{now_p:,}원</b> (+{diff:,}원)")
                목록[i].update({'price': now_p, '상태': "판매중"})
                변경_내용.append(f"🔺 {s['name']}: +{diff:,}원")
            elif now_p and now_p < s['price']:
                diff = s['price'] - now_p
                send_telegram(f"🔻 <b>가격인하!</b> {icon}{플랫폼}\n📦 {s['name']}\n{s['price']:,}원 → <b>{now_p:,}원</b> (-{diff:,}원)")
                목록[i].update({'price': now_p, '상태': "판매중"})
                변경_내용.append(f"🔻 {s['name']}: -{diff:,}원")
            elif now_p:
                목록[i]['상태'] = "판매중"
            else:
                if s['상태'] == "판매중":
                    send_telegram(f"🚫 <b>품절/확인불가!</b> {icon}{플랫폼}\n📦 {s['name']}\n상태: {now_st}")
                    변경_내용.append(f"🚫 {s['name']}: {now_st}")
                목록[i]['상태'] = now_st

        _스케줄러_저장(목록, ws)

        now_str    = now.strftime('%Y-%m-%d %H:%M')
        type_label = "⏰ 정기" if source == "자동" else "🔄 수동"
        if 변경_내용:
            send_telegram(f"{type_label} <b>점검 완료</b> ({now_str})\n총 {len(목록)}개 점검\n\n<b>변동 내역:</b>\n" + "\n".join(변경_내용))
        else:
            send_telegram(f"{type_label} <b>점검 완료</b> ({now_str})\n총 {len(목록)}개 — 변동 없음 ✅")

        json.dump({'last_key': now_key, 'last_time': now_str,
                   'count': len(목록), 'changes': len(변경_내용), 'source': source},
                  open(점검기록파일,'w',encoding='utf-8'), ensure_ascii=False)
    except Exception as e:
        send_telegram(f"⚠️ <b>점검 오류</b>\n{str(e)[:200]}")

# ── 백그라운드 스케줄러 (오전 11시 · 오후 2시 자동 실행) ────────
import threading
_SCHEDULER_RUNNING = False

def _start_background_scheduler():
    global _SCHEDULER_RUNNING
    if _SCHEDULER_RUNNING:
        return
    _SCHEDULER_RUNNING = True

    def _run():
        last_ran_hour = -1
        while True:
            try:
                now = datetime.now()
                if now.hour in (11, 14) and now.minute < 3:
                    if last_ran_hour != now.hour:
                        last_ran_hour = now.hour
                        자동_가격체크(source="자동")
                elif now.hour not in (11, 14):
                    last_ran_hour = -1   # 매 시간마다 리셋
            except Exception:
                pass
            time.sleep(60)  # 1분마다 시간 확인

    t = threading.Thread(target=_run, daemon=True, name="price_scheduler")
    t.start()

_start_background_scheduler()  # 앱 시작 시 1회 실행

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
    ai_text = call_claude_api({"max_tokens":4096,"messages":[{"role":"user",
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
    import random
    사용된 = 전체_사용된_키워드()
    제외   = ", ".join(사용된) if 사용된 else "없음"
    월  = datetime.now().month
    요일 = datetime.now().weekday()  # 0=월 ~ 6=일
    주차 = datetime.now().isocalendar()[1]  # 올해 몇 번째 주

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

    # ── 다양성 강제 장치 ───────────────────────────────────────────
    # 카테고리 로테이션: 요일별로 다른 세부 카테고리 집중
    요일별_힌트 = {
        0: "주방·식품 보관 용품 위주",
        1: "욕실·위생·청결 용품 위주",
        2: "수납·정리·인테리어 용품 위주",
        3: "반려동물·육아·어린이 용품 위주",
        4: "스포츠·아웃도어·캠핑 용품 위주",
        5: "뷰티·헬스·다이어트 용품 위주",
        6: "사무·학습·문구 용품 위주",
    }
    오늘_힌트 = 요일별_힌트.get(요일, "생활용품 전반")

    # 주차 기반 랜덤 시드 → 같은 주에는 비슷하게, 다른 주에는 다르게
    random.seed(주차 * 100 + 요일)
    랜덤_각도 = random.choice([
        "MZ세대가 SNS에서 공유하는 트렌디한",
        "30~50대 주부가 재구매하는 실용적인",
        "자취생·1인가구가 많이 찾는 소용량",
        "캠핑·피크닉 시즌에 급상승하는",
        "반려동물 가구가 필수로 구매하는",
        "미니멀 라이프·정리수납 트렌드의",
        "건강·웰빙·면역 관심층이 찾는",
    ])

    다음월 = (월 % 12) + 1
    시즌명, 시즌kw      = 시즌맵.get(월, ("일반",[]))
    다음시즌명, 다음kw  = 시즌맵.get(다음월, ("일반",[]))

    prompt = f"""당신은 한국 스마트스토어/쿠팡 위탁판매 전문 MD입니다.
⚠️ 매우 중요: 아래 제외 키워드와 유사한 상품은 절대 추천 금지. 비슷한 카테고리도 피하세요.

[조건]
- 카테고리: {카테고리}
- 가격대: {타겟가격대}
- 추천 개수: {추천수}개
- 오늘 탐색 각도: {랜덤_각도} 상품 위주로 찾아주세요
- 오늘 세부 카테고리 방향: {오늘_힌트}
- 현재 {주차}주차 / {요일+1}요일 기준 신선한 아이디어 필요

[🚫 절대 제외 — 이미 추천한 키워드 (유사 카테고리 전체 제외)]
{제외 if 제외 != '없음' else '없음 (첫 실행)'}

[🗓️ 시즌 반영]
이번달({월}월): {시즌명} → 힌트: {', '.join(시즌kw)}
다음달({다음월}월): {다음시즌명} → 선제힌트: {', '.join(다음kw[:3])}
이번달 70% + 다음달 선제 30% 비율로 구성

[다양성 원칙]
- 추천 {추천수}개가 서로 다른 세부 카테고리에서 나와야 함
- 같은 카테고리 중복 금지 (예: 칫솔 1개면 다른 구강용품 추가 금지)
- 레드오션(무선이어폰·텀블러·보조배터리 등) 제외

[출력] JSON 배열만. 설명 없음.
[{{"keyword":"키워드","reason":"추천이유(시즌+각도 연관성포함)","price_range":"소싱가~판매가","season":"이번달/다음달선제"}}]"""

    res = call_claude_api({"max_tokens":3000,"messages":[{"role":"user","content":prompt}]})
    if res:
        try:
            결과 = json.loads(res.replace("```json","").replace("```","").strip())
            # 제외 키워드와 정확히 일치하는 것 + 유사한 것 필터
            필터결과 = []
            for it in 결과:
                kw = it['keyword']
                # 정확히 같은 키워드 제외
                if kw in 사용된: continue
                # 이미 추천된 키워드의 첫 단어가 겹치면 제외 (예: "실리콘 얼음틀" → "실리콘" 계열 제외)
                kw_첫단어 = kw.split()[0] if kw.split() else kw
                if any(kw_첫단어 in 기존 for 기존 in 사용된 if len(kw_첫단어) > 1):
                    continue
                필터결과.append(it)
            return 필터결과
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
    "🎯 원클릭 등록 패키지",
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
                    desc = call_claude_api({"max_tokens":4096,"messages":[{"role":"user","content":[
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
                result = call_claude_api({"max_tokens":4096,"messages":[{"role":"user","content":prompt}]})
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

    # ── 매입 정보 ─────────────────────────────────────────────────
    st.markdown("##### 📥 매입 정보")
    c1, c2, c3 = st.columns(3)
    buy_p  = c1.number_input("단품 도매가(매입가)", value=2900, step=100, key="buy_p")
    qty    = c2.number_input("판매 수량 (묶음 단위)", min_value=1, value=1, step=1, key="qty")
    ship_buy = c3.number_input("건당 매입 배송비", value=2500, step=100, key="ship_p")

    # ── 판매 정보 ─────────────────────────────────────────────────
    st.markdown("##### 📤 판매 배송비")
    d1, d2 = st.columns([2, 1])
    with d1:
        ship_sell = st.number_input(
            "판매 시 건당 배송비 (내가 구매자에게 부담하는 배송비)",
            min_value=0, value=0, step=100, key="ship_sell",
            help="무료배송이면 0 / 유료배송이면 실제 택배비 입력 (예: 3000)"
        )
    with d2:
        st.markdown("<br>", unsafe_allow_html=True)
        free_ship = st.checkbox("무료배송", value=True, key="free_ship")
        if free_ship:
            ship_sell = 0

    st.divider()
    target_m = st.slider("🎯 목표 마진율 (%)", min_value=5, max_value=80, value=20, step=1)

    if st.button("🚀 플랫폼별 추천 판매가 계산", type="primary", use_container_width=True):
        # 총 매입 원가 = 도매가 × 수량 + 매입배송비
        total_cost = buy_p * qty + ship_buy
        # 총 비용 = 매입원가 + 판매배송비
        total_out  = total_cost + ship_sell

        st.markdown(f"""
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-bottom:20px;">
          <div style="background:rgba(255,215,0,.08);border:1px solid rgba(255,215,0,.2);
          border-radius:10px;padding:14px;text-align:center;">
            <div style="color:#aaa;font-size:.8rem;">📥 총 매입 원가</div>
            <div style="color:#ffd700;font-size:1.4rem;font-weight:800;">{total_cost:,}원</div>
            <div style="color:#555;font-size:.75rem;">(도매가×{qty}개 + 매입배송비)</div>
          </div>
          <div style="background:rgba(255,100,100,.06);border:1px solid rgba(255,100,100,.2);
          border-radius:10px;padding:14px;text-align:center;">
            <div style="color:#aaa;font-size:.8rem;">📤 판매 배송비</div>
            <div style="color:#ff6b6b;font-size:1.4rem;font-weight:800;">{"무료" if ship_sell==0 else f"{ship_sell:,}원"}</div>
            <div style="color:#555;font-size:.75rem;">{"구매자 부담 없음" if ship_sell==0 else "판매자 부담"}</div>
          </div>
          <div style="background:rgba(3,199,90,.08);border:1px solid rgba(3,199,90,.2);
          border-radius:10px;padding:14px;text-align:center;">
            <div style="color:#aaa;font-size:.8rem;">💸 총 지출 합계</div>
            <div style="color:#03C75A;font-size:1.4rem;font-weight:800;">{total_out:,}원</div>
            <div style="color:#555;font-size:.75rem;">(매입원가 + 판매배송비)</div>
          </div>
        </div>""", unsafe_allow_html=True)

        st.markdown("#### 🏪 플랫폼별 추천 판매가")
        for (name, fee), col in zip(
            [("스마트스토어", 0.00), ("쿠팡(11%)", 0.11), ("11번가(13%)", 0.13)],
            st.columns(3)
        ):
            # 판매가 = (총지출) / (1 - 수수료 - 부가세3.6% - 목표마진율)
            rec    = total_out / (1 - fee - 0.036 - target_m / 100)
            margin = rec * (target_m / 100)
            실마진  = rec - total_out - rec * (fee + 0.036)  # 실제 손에 남는 금액

            with col:
                st.success(f"🛒 {name}")
                st.metric("추천 판매가", f"{int(rec):,}원")
                st.markdown(f"""
                <div style="font-size:.88rem;margin-top:4px;">
                  💵 마진액: <b>{int(margin):,}원</b><br>
                  📊 실수령: <b style="color:#03C75A;">{int(실마진):,}원</b>
                  {"<br><span style='color:#aaa;font-size:.8rem;'>1개당: "+str(int(rec/qty))+",원 / 마진 "+str(int(margin/qty))+",원</span>" if qty > 1 else ""}
                </div>""".replace(",원", "원"), unsafe_allow_html=True)

        # 손익분기점
        st.divider()
        bep = total_out / (1 - 0.036)  # 수수료 없는 스마트스토어 기준
        st.info(f"📉 손익분기점 (스마트스토어 기준): **{int(bep):,}원** 이상 판매해야 손해 없음")

# ==========================================
# 📦 재고/가격 알림
# ==========================================
elif 메뉴 == "📦 재고/가격 알림":
    st.markdown("<h1>📦 멀티 플랫폼 가격·재고 감시</h1>", unsafe_allow_html=True)
    st.caption("도매꾹·11번가·네이버·G마켓·옥션 상품을 한 곳에서 감시 · 오전 11시·오후 2시 자동 점검")

    def mask(cid): return cid[:3]+"****"+cid[-2:] if cid else "미등록"
    st.info(f"🔔 텔레그램 수신 ID: {mask(TELEGRAM_CHAT_ID)}")

    # ── Google Sheets 연동 로드/저장 ─────────────────────────────
    def _get_sheet():
        """Google Sheets 워크시트 반환"""
        try:
            import gspread
            from google.oauth2.service_account import Credentials
            scopes = ["https://spreadsheets.google.com/feeds",
                      "https://www.googleapis.com/auth/drive"]
            creds = Credentials.from_service_account_info(
                dict(st.secrets["gcp_service_account"]), scopes=scopes)
            gc = gspread.authorize(creds)
            sh = gc.open_by_key(st.secrets["SPREADSHEET_ID"])
            # "재고감시" 시트 없으면 자동 생성
            try:
                ws = sh.worksheet("재고감시")
            except:
                ws = sh.add_worksheet(title="재고감시", rows=500, cols=10)
                ws.append_row(["no","name","platform","url","price","상태"])
            return ws
        except Exception as e:
            return None

    def 로드():
        ws = _get_sheet()
        if ws is None:
            # Google Sheets 미설정 → 로컬 파일 fallback
            재고파일 = "재고모니터링.json"
            return json.load(open(재고파일,'r',encoding='utf-8')) if os.path.exists(재고파일) else []
        try:
            records = ws.get_all_records()
            # price를 int로 변환
            for r in records:
                r['price'] = int(r.get('price', 0) or 0)
            return records
        except:
            return []

    def 저장(d):
        ws = _get_sheet()
        if ws is None:
            # Google Sheets 미설정 → 로컬 파일 fallback
            재고파일 = "재고모니터링.json"
            json.dump(d, open(재고파일,'w',encoding='utf-8'), ensure_ascii=False, indent=2)
            return
        try:
            ws.clear()
            ws.append_row(["no","name","platform","url","price","상태"])
            for item in d:
                ws.append_row([
                    item.get('no',''),
                    item.get('name',''),
                    item.get('platform','도매꾹'),
                    item.get('url',''),
                    item.get('price', 0),
                    item.get('상태','판매중'),
                ])
        except Exception as e:
            st.warning(f"Google Sheets 저장 오류: {e} — 로컬 저장으로 대체합니다.")
            재고파일 = "재고모니터링.json"
            json.dump(d, open(재고파일,'w',encoding='utf-8'), ensure_ascii=False, indent=2)

    # Google Sheets 연결 상태 표시
    _ws_test = None
    _연동오류 = ""
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        scopes = ["https://spreadsheets.google.com/feeds",
                  "https://www.googleapis.com/auth/drive"]
        if "gcp_service_account" not in st.secrets:
            _연동오류 = "❌ Secrets에 [gcp_service_account] 섹션이 없습니다."
        elif "SPREADSHEET_ID" not in st.secrets:
            _연동오류 = "❌ Secrets에 SPREADSHEET_ID가 없습니다."
        else:
            creds = Credentials.from_service_account_info(
                dict(st.secrets["gcp_service_account"]), scopes=scopes)
            gc = gspread.authorize(creds)
            _ws_test = gc.open_by_key(st.secrets["SPREADSHEET_ID"])
    except ImportError:
        _연동오류 = "❌ gspread 라이브러리 미설치 — requirements.txt에 gspread, google-auth 추가 후 재배포 필요"
    except Exception as e:
        _연동오류 = f"❌ 연동 오류: {str(e)}"

    if _ws_test is not None:
        st.success("☁️ Google Sheets 연동 중 — 앱이 꺼져도 데이터가 유지됩니다.")
    else:
        st.warning("⚠️ Google Sheets 미연동 — 로컬 저장 모드 (앱 재시작 시 초기화될 수 있습니다)\n\nStreamlit Secrets에 `gcp_service_account`와 `SPREADSHEET_ID`를 등록하세요.")
        if _연동오류:
            st.error(_연동오류)

    # ── 스케줄러 상태 카드 ────────────────────────────────────────
    now_h = datetime.now().hour
    now_m = datetime.now().minute
    next_run = "오전 11:00" if now_h < 11 else "오후 2:00" if now_h < 14 else "내일 오전 11:00"

    last_info = {}
    if os.path.exists(점검기록파일):
        try: last_info = json.load(open(점검기록파일,'r',encoding='utf-8'))
        except: pass

    last_txt   = last_info.get('last_time', '아직 없음')
    last_cnt   = last_info.get('count', 0)
    last_chg   = last_info.get('changes', 0)
    last_src   = last_info.get('source', '-')
    src_icon   = "⏰" if last_src == "자동" else "🔄"

    st.markdown(f"""
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-bottom:20px;">
      <div style="background:rgba(3,199,90,.08);border:1px solid rgba(3,199,90,.25);
      border-radius:12px;padding:16px;text-align:center;">
        <div style="color:#03C75A;font-size:1.4rem;font-weight:800;">⏰ 자동 ON</div>
        <div style="color:#aaa;font-size:.82rem;margin-top:4px;">오전 11:00 · 오후 2:00</div>
      </div>
      <div style="background:rgba(255,215,0,.07);border:1px solid rgba(255,215,0,.2);
      border-radius:12px;padding:16px;text-align:center;">
        <div style="color:#ffd700;font-size:1.1rem;font-weight:700;">다음 점검</div>
        <div style="color:#ffd700;font-size:1.3rem;font-weight:800;">{next_run}</div>
      </div>
      <div style="background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.08);
      border-radius:12px;padding:16px;text-align:center;">
        <div style="color:#aaa;font-size:.82rem;">마지막 점검 {src_icon}</div>
        <div style="color:#e8eaf0;font-size:.9rem;font-weight:700;">{last_txt}</div>
        <div style="color:#aaa;font-size:.78rem;">{last_cnt}개 점검 · 변동 {last_chg}건</div>
      </div>
    </div>""", unsafe_allow_html=True)

    # ── 상품 추가 폼 ──────────────────────────────────────────────
    with st.expander("➕ 감시 상품 추가", expanded=True):
        선택플랫폼 = st.selectbox(
            "플랫폼 선택", list(PLATFORM_ICONS.keys()), key="sel_platform",
            format_func=lambda x: f"{PLATFORM_ICONS[x]} {x}"
        )
        ca, cb = st.columns([3,1])
        if 선택플랫폼 == "도매꾹":
            st.caption("💡 도매꾹 상품번호 또는 URL(domeggook.com/숫자)을 입력하세요.")
            raw_input   = ca.text_input("도매꾹 상품번호 또는 URL", key="add_dome",
                                        placeholder="예: 13187678  또는  https://domeggook.com/13187678")
            m_no        = re.search(r'(\d{5,})', raw_input)
            item_no_val = m_no.group(1) if m_no else raw_input.strip()
        else:
            st.caption(f"💡 {선택플랫폼} 상품 페이지 URL을 붙여넣으세요.")
            item_url_val = ca.text_input(f"{선택플랫폼} 상품 URL", key="add_url",
                                         placeholder="상품 페이지 주소를 붙여넣으세요")
        관리명 = cb.text_input("관리 이름", placeholder="예: 실리콘 얼음틀", key="add_name")

        if st.button("👑 모니터링 명단에 등록", use_container_width=True, key="btn_add_item"):
            목록 = 로드()
            if not 관리명.strip():
                st.warning("관리 이름을 입력해주세요!")
            else:
                with st.spinner("현재 가격 확인 중..."):
                    if 선택플랫폼 == "도매꾹":
                        price_now, status_now = 가격체크_도매꾹(item_no_val)
                        url_stored = f"https://domeggook.com/{item_no_val}"
                        id_stored  = item_no_val
                    else:
                        price_now, status_now = 가격체크_URL(item_url_val.strip(), 선택플랫폼)
                        url_stored = item_url_val.strip()
                        id_stored  = ""

                if price_now:
                    목록.append({"no": id_stored, "name": 관리명.strip(),
                                "platform": 선택플랫폼, "url": url_stored,
                                "price": price_now, "상태": status_now})
                    저장(목록)
                    st.success(f"✅ {PLATFORM_ICONS[선택플랫폼]} {선택플랫폼} 등록 완료! 현재가: **{price_now:,}원**")
                    st.rerun()
                else:
                    st.error(f"❌ 가격 확인 실패 ({status_now}) — URL 또는 상품번호를 확인해주세요.")
                    manual_price = st.number_input("현재 가격 직접 입력 (원)", min_value=0, step=100, key="manual_p")
                    if st.button("직접 입력으로 등록", key="btn_manual") and manual_price > 0:
                        목록.append({"no": id_stored if 선택플랫폼=="도매꾹" else "",
                                    "name": 관리명.strip(), "platform": 선택플랫폼,
                                    "url": url_stored if 선택플랫폼!="도매꾹" else f"https://domeggook.com/{item_no_val}",
                                    "price": manual_price, "상태": "판매중"})
                        저장(목록); st.success("✅ 수동 등록 완료!"); st.rerun()

    st.divider()

    # ── 수동 전수 점검 버튼 ───────────────────────────────────────
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🔄 지금 즉시 수동 점검 + 텔레그램 발송", type="primary", use_container_width=True):
            목록 = 로드()
            if not 목록:
                st.warning("등록된 상품이 없습니다.")
            else:
                with st.spinner(f"총 {len(목록)}개 상품 점검 중..."):
                    자동_가격체크(source="수동")
                st.success("✅ 수동 점검 완료! 텔레그램을 확인하세요.")
                st.rerun()
    with col_btn2:
        if st.button("🧪 지금 당장 테스트 발송", use_container_width=True):
            send_telegram(
                f"🧪 <b>테스트 발송</b>\n"
                f"위탁의왕 자동 점검 정상 작동 중 ✅\n"
                f"⏰ 자동 점검 시간: 오전 11:00 · 오후 2:00\n"
                f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )
            st.success("✅ 텔레그램으로 테스트 메시지를 보냈습니다!")

    st.divider()

    # ── 감시 목록 표시 ────────────────────────────────────────────
    목록 = 로드()
    st.markdown("### 📋 감시 중인 영토")
    if not 목록:
        st.info("아직 등록된 상품이 없습니다. 위에서 추가해주세요.")
    else:
        platform_counts = {}
        for s in 목록:
            p = s.get('platform','도매꾹')
            platform_counts[p] = platform_counts.get(p,0) + 1
        summary = " &nbsp; ".join([
            f"<span style='background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);"
            f"border-radius:20px;padding:4px 12px;font-size:.82rem;'>"
            f"{PLATFORM_ICONS.get(p,'⚪')} {p} {c}개</span>"
            for p,c in platform_counts.items()
        ])
        st.markdown(f"<div style='margin-bottom:16px;'>{summary}</div>", unsafe_allow_html=True)

        for idx, s in enumerate(목록):
            플랫폼 = s.get('platform','도매꾹')
            icon   = PLATFORM_ICONS.get(플랫폼,"⚪")
            if s['상태'] == "판매중":   sc = "color:#03C75A;font-weight:bold;"
            elif s['상태'] == "품절":   sc = "color:#ff4b4b;font-weight:bold;"
            else:                        sc = "color:#ffd700;font-weight:bold;"
            c1,c2,c3,c4,c5 = st.columns([3,1,1,1,1])
            c1.markdown(
                f"{icon} **{s['name']}** "
                f"<span style='color:#555;font-size:.78rem;background:rgba(255,255,255,.05);"
                f"padding:2px 7px;border-radius:10px;'>{플랫폼}</span>",
                unsafe_allow_html=True)
            c2.markdown(f"<strong style='color:#ffd700;'>{s['price']:,}원</strong>", unsafe_allow_html=True)
            c3.markdown(f"<span style='{sc}'>{s['상태']}</span>", unsafe_allow_html=True)
            c4.link_button("🔗", s.get('url','#'), use_container_width=True)
            if c5.button("삭제", key=f"d_{idx}", type="secondary"):
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
        import random as _random
        월   = datetime.now().month
        요일  = datetime.now().weekday()
        주차  = datetime.now().isocalendar()[1]
        요일명 = ["월","화","수","목","금","토","일"][요일]
        요일별_힌트_ui = {
            0:"주방·식품 보관 용품",1:"욕실·위생·청결 용품",2:"수납·정리·인테리어 용품",
            3:"반려동물·육아·어린이 용품",4:"스포츠·아웃도어·캠핑 용품",
            5:"뷰티·헬스·다이어트 용품",6:"사무·학습·문구 용품",
        }
        _random.seed(주차 * 100 + 요일)
        오늘각도 = _random.choice([
            "MZ세대 SNS 트렌디","30~50대 주부 실용형","자취생·1인가구 소용량",
            "캠핑·피크닉 시즌형","반려동물 가구 필수템","미니멀·정리수납형","건강·웰빙·면역형"
        ])
        st.caption(f"AI 트렌드 분석 → 블루오션 스캔 → 소싱 → HTML 자동 생성 | 📅 {월}월 {주차}주차 {요일명}요일")

        # ── 오늘의 탐색 각도 표시 ─────────────────────────────────
        st.markdown(f"""<div style="background:rgba(255,215,0,.07);border:1px solid rgba(255,215,0,.2);
        border-radius:10px;padding:10px 18px;margin-bottom:14px;font-size:.88rem;">
        🎯 <b style="color:#ffd700;">오늘의 탐색 각도</b>
        &nbsp;—&nbsp; <span style="color:#03C75A;">{요일별_힌트_ui.get(요일,'생활용품')} · {오늘각도}</span>
        &nbsp;&nbsp;<span style="color:#555;font-size:.78rem;">({주차}주차 {요일명}요일 기준 자동 변경)</span>
        </div>""", unsafe_allow_html=True)

        cs1,cs2,cs3 = st.columns(3)
        카테고리  = cs1.selectbox("타겟 카테고리", ["자동 탐지 (AI 추천)","생활용품","주방용품","뷰티/헬스","반려동물","스포츠/레저","디지털/가전","패션잡화","유아동"], key="sel_category")
        타겟가격대 = cs2.selectbox("타겟 판매가대", ["전체","1만원 이하","1~3만원","3~5만원","5만원 이상"], key="sel_price_range")
        추천수    = cs3.number_input("추천 상품 수", min_value=3, max_value=10, value=5, key="num_recommend")
        send_tg   = st.checkbox("📲 완료 후 텔레그램 발송", value=True, key="chk_telegram")
        st.divider()

        이력data = 이력_로드()
        총kw수   = sum(len(v) for v in 이력data.values())
        ch1, ch2, ch3, ch4 = st.columns([2,2,1,1])
        ch1.metric("📋 누적 추천 키워드", f"{총kw수}개")
        ch2.metric("📅 추천 실행 일수", f"{len(이력data)}일")
        with ch3:
            if st.button("🗑️ 이력 초기화", key="btn_reset_history", type="secondary",
                         help="초기화하면 AI가 기존에 추천한 내용을 잊고 새로운 키워드를 추천합니다"):
                if os.path.exists(이력파일): os.remove(이력파일)
                st.success("✅ 초기화 완료! 다음 추천부터 완전히 새로운 키워드가 나옵니다.")
                st.rerun()
        with ch4:
            # 오늘 이력만 삭제
            오늘 = datetime.now().strftime('%Y-%m-%d')
            if st.button("↩️ 오늘만 취소", key="btn_reset_today", type="secondary",
                         help="오늘 추천된 키워드만 삭제합니다"):
                data = 이력_로드()
                if 오늘 in data:
                    del data[오늘]
                    import json as _json
                    _json.dump(data, open(이력파일,'w',encoding='utf-8'), ensure_ascii=False, indent=2)
                    st.success("✅ 오늘 이력 삭제 완료!"); st.rerun()

        if 이력data:
            with st.expander(f"📖 추천 이력 보기 ({총kw수}개 누적 — AI가 이걸 보고 중복 방지합니다)"):
                for 날짜, kw_list in sorted(이력data.items(), reverse=True):
                    st.markdown(f"**{날짜}** — {', '.join(kw_list)}")
        else:
            st.info("💡 추천 이력이 없습니다. 처음 실행 시 AI가 가장 트렌디한 키워드를 추천합니다.")

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
                res = call_claude_api({"max_tokens":4096,"messages":[{"role":"user","content":prompt}]})

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
⚠️ 출력 규칙: ###, **, - 등 마크다운만 사용. 코드블록(```)과 취소선(~~) 절대 사용 금지. 숫자 범위는 반드시 '28자~38자', '5,000원~12,000원' 형식으로 쓰세요.

'{rev_kw}' 키워드의 네이버 쇼핑 상위 {len(titles_list)}개 상품명을 분석하여 상위노출 패턴을 해독하세요.

[수집된 상품명]
{titles_text}

### 🔑 핵심 공통 키워드 TOP 10 (등장 빈도 포함)
### 📐 상위노출 상품명 구조 패턴 (도식화)
### 🔢 글자수 분석 (평균·최적 구간·권장사항)
### ⚡ 차별화 기회 — 아무도 안 쓴 키워드
### 🏆 이 분석 기반 최적 상품명 3가지 제안
### 📊 가격대 분석 및 우리의 최적 포지션
### 🎯 롱테일 키워드 추천 10개 (검색량·경쟁도 관점)"""
                    result = call_claude_api({"max_tokens":4096,"messages":[{"role":"user","content":prompt}]})

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

# ==========================================
# 🎯 원클릭 등록 패키지
# ==========================================
elif 메뉴 == "🎯 원클릭 등록 패키지":
    st.markdown("<h1>🎯 원클릭 상품 등록 패키지</h1>", unsafe_allow_html=True)
    st.caption("블루오션 HTML을 첨부하면 → 같은 상품 기준으로 경쟁사 분석·SEO 상품명·상세페이지·썸네일까지 자동 완성")

    # ── HTML 파서 함수 ────────────────────────────────────────────
    def parse_blueocean_html(raw_html):
        """블루오션 STEP3 / 등록패키지 HTML에서 키워드·소싱 정보·AI 내용 추출"""
        result = {"keyword":"", "price":0, "source":"", "link":"#", "image":"", "draft":""}

        # ── 키워드 추출 ───────────────────────────────────────────
        # ✅ h1 우선: 두 HTML 형식 모두 h1에 키워드만 정확히 들어있음
        # 상세페이지:  <h1 class="fu">👑 욕실 김서림 방지필름</h1>
        # 등록패키지:  <h1>👑 피크닉 돗자리 방수 대형</h1>
        m = re.search(r'<h1[^>]*>👑\s*([^<]+)</h1>', raw_html)
        if m:
            result["keyword"] = m.group(1).strip()

        # title fallback (h1 실패 시)
        if not result["keyword"]:
            # 등록패키지 형식: "👑 키워드 — 원클릭 등록 패키지" → 대시 앞
            m = re.search(r'<title>👑\s*([^—\-<]+?)(?:\s*[—\-])', raw_html)
            if m:
                kw_candidate = m.group(1).strip()
                # "위탁의왕"처럼 브랜드명이 나오면 대시 뒤를 사용
                if kw_candidate in ('위탁의왕', 'Ultra', ''):
                    m2 = re.search(r'<title>[^—\-]+[—\-]\s*([^<\-—]+?)(?:\s*[—\-]|</title>)', raw_html)
                    if m2: result["keyword"] = m2.group(1).strip()
                else:
                    result["keyword"] = kw_candidate
            # 상세페이지 형식: "👑 위탁의왕 — 키워드" → 대시 뒤
            if not result["keyword"]:
                m = re.search(r'<title>👑[^—\-]+[—\-]\s*([^<]+)</title>', raw_html)
                if m:
                    result["keyword"] = m.group(1).strip()

        # ── HTML 태그 제거 후 텍스트로 검색 (strong, div 등 무관하게 동작) ──
        plain = re.sub(r'<[^>]+>', ' ', raw_html)
        plain = re.sub(r'\s+', ' ', plain).strip()

        # 패턴 1: "소싱가: N,NNN원 (출처)"  ← 상세페이지 HTML
        m = re.search(r'소싱가\s*:\s*([\d,]+)원\s*\(([^)]{1,20})\)', plain)
        if m:
            result["price"]  = int(m.group(1).replace(',',''))
            result["source"] = m.group(2).strip()

        # 패턴 2: "단가 N,NNN원" + "출처: XXX"  ← 등록패키지 HTML
        if not result["price"]:
            m1 = re.search(r'단가\s*([\d,]+)원', plain)
            m2 = re.search(r'출처:\s*([가-힣A-Za-z0-9]{2,10})', plain)
            if m1 and m2:
                result["price"]  = int(m1.group(1).replace(',',''))
                result["source"] = m2.group(1).strip()

        # 패턴 3: "N,NNN원 (출처)" 범용 fallback
        if not result["price"]:
            m = re.search(r'([\d,]{4,})\s*원\s*\(([가-힣A-Za-z0-9]{2,10})\)', plain)
            if m:
                p = int(m.group(1).replace(',',''))
                if 500 <= p <= 9_999_999:
                    result["price"]  = p
                    result["source"] = m.group(2).strip()

        # ── 소싱처 링크 ───────────────────────────────────────────
        m = re.search(r'href="(https?://[^"]+)"[^>]*class="sb"', raw_html)
        if not m:
            m = re.search(r'class="sb"[^>]*href="(https?://[^"]+)"', raw_html)
        if not m:
            m = re.search(r'href="(https?://[^"]+)"[^>]*>🛒', raw_html)
        if not m:  # 등록패키지 스타일 링크
            m = re.search(r'target="_blank"[^>]*href="(https?://[^"]+)"', raw_html)
        if not m:
            m = re.search(r'href="(https?://(?:domeggook|11st|smartstore|gmarket|auction)[^"]+)"', raw_html)
        if m:
            result["link"] = m.group(1)

        # ── 소싱 이미지 ───────────────────────────────────────────
        m = re.search(r'class="ic[^"]*".*?<img\s+src="(https?://[^"]+)"', raw_html, re.DOTALL)
        if not m:
            m = re.search(r'display:flex.*?<img\s+src="(https?://[^"]+)"', raw_html, re.DOTALL)
        if not m:
            m = re.search(r'<img\s+src="(https?://(?:cdn|img)[^"]+)"', raw_html)
        if not m:
            m = re.search(r'<img\s+src="(https?://[^"]+)"', raw_html)
        if m:
            result["image"] = m.group(1)

        # ── AI 기획안 텍스트 ──────────────────────────────────────
        # .ab div (상세페이지 HTML)
        m = re.search(r'class="ab"[^>]*>(.*?)</div>\s*</div>', raw_html, re.DOTALL)
        if m:
            txt = re.sub(r'<[^>]+>',' ', m.group(1))
            result["draft"] = re.sub(r'\s+',' ', txt).strip()[:2500]
        else:
            # 마지막 .card 내용 (등록패키지 HTML)
            cards = re.findall(r'<div class="card[^"]*">(.*?)</div>\s*</div>', raw_html, re.DOTALL)
            if cards:
                txt = re.sub(r'<[^>]+>',' ', cards[-1])
                result["draft"] = re.sub(r'\s+',' ', txt).strip()[:2500]
            else:
                # 전체 fallback
                txt = re.sub(r'<style[^>]*>.*?</style>','', raw_html, flags=re.DOTALL)
                txt = re.sub(r'<[^>]+>',' ', txt)
                result["draft"] = re.sub(r'\s+',' ', txt).strip()[:2500]

        return result

    # ── 파이프라인 안내 ───────────────────────────────────────────
    st.markdown("""
    <div style="background:rgba(255,215,0,0.06);border:1px solid rgba(255,215,0,0.2);
    border-radius:12px;padding:16px 22px;margin-bottom:16px;">
    <b style="color:#ffd700;">🔄 두 가지 사용 방법</b><br>
    <span style="color:#ccc;font-size:.9rem;">
    <b style="color:#03C75A;">방법 A (권장)</b> — 블루오션 HTML 첨부 →
    자동으로 키워드·소싱 추출 → 동일 상품 기준으로 경쟁사 분석 + 업그레이드<br>
    <b style="color:#ffd700;">방법 B</b> — 키워드 직접 입력 →
    처음부터 소싱 조회 + 상세페이지 생성
    </span></div>""", unsafe_allow_html=True)

    # ── HTML 첨부 (STEP 0) ────────────────────────────────────────
    st.markdown("""<div style="background:rgba(3,199,90,0.07);border:1px solid rgba(3,199,90,0.25);
    border-radius:10px;padding:12px 18px;margin-bottom:10px;">
    <b style="color:#03C75A;">📄 블루오션 STEP3 HTML 첨부 (강력 추천)</b><br>
    <span style="color:#aaa;font-size:.85rem;">
    첨부하면 키워드·소싱가·이미지를 자동 추출 → 같은 상품 기준으로 경쟁사 분석 + 더 깊은 기획안 생성
    </span></div>""", unsafe_allow_html=True)

    uploaded_html = st.file_uploader(
        "📎 블루오션 STEP3 HTML 파일 첨부",
        type=["html"], key="pkg_html",
        help="💎 블루오션 탐지 → AI 자동 일일추천 → STEP3에서 다운로드한 파일"
    )

    # ── HTML 파싱 결과 ────────────────────────────────────────────
    html_data     = {}   # 파싱된 데이터
    prev_draft    = ""
    html_sourcing = None

    if uploaded_html:
        try:
            raw = uploaded_html.read().decode('utf-8')
            html_data = parse_blueocean_html(raw)
            prev_draft = html_data.get("draft","")

            # 추출 결과 표시
            ok_kw  = bool(html_data.get("keyword"))
            ok_src = html_data.get("price",0) > 0

            st.markdown(f"""
            <div style="background:rgba(3,199,90,.08);border:1px solid rgba(3,199,90,.2);
            border-radius:10px;padding:14px 18px;margin-bottom:10px;">
            <b style="color:#03C75A;">✅ HTML 파일 분석 완료!</b><br>
            <span style="color:#ccc;font-size:.88rem;">
            {"✅" if ok_kw else "⚠️"} 키워드: <b style="color:#ffd700;">{html_data.get('keyword','추출 실패')}</b>
            &nbsp;&nbsp;
            {"✅" if ok_src else "⚠️"} 소싱가: <b style="color:#03C75A;">{html_data['price']:,}원</b>
            &nbsp;&nbsp;
            출처: {html_data.get('source','-')}
            </span></div>""", unsafe_allow_html=True)

            if ok_src:
                html_sourcing = {
                    "총가격":   html_data["price"],
                    "출처":     html_data["source"],
                    "링크":     html_data["link"],
                    "이미지":   html_data["image"],
                    "최소수량": 1,
                    "실매입가": html_data["price"],
                }

            with st.expander("📋 추출된 기획안 내용 미리보기"):
                st.text(prev_draft[:600] + ("..." if len(prev_draft)>600 else ""))

        except Exception as e:
            st.warning(f"HTML 파싱 오류: {e} — 키워드를 직접 입력해주세요.")

    # ── 키워드 입력 (HTML 첨부 시 자동 채워짐) ───────────────────
    default_kw = html_data.get("keyword","") if html_data else ""
    pkg_kw = st.text_input(
        "📦 등록할 상품 키워드",
        value=default_kw,
        placeholder="블루오션 HTML 첨부 시 자동 입력 / 직접 입력도 가능",
        key="pkg_kw"
    )

    col_p1, col_p2, col_p3 = st.columns(3)
    pkg_target = col_p1.selectbox("주 타겟", ["전체","육아맘","자취생","직장인","캠퍼","시니어"], key="pkg_target")
    pkg_price  = col_p2.selectbox("가격대",  ["1만원 이하","1~3만원","3~5만원","5만원 이상"], key="pkg_price")
    pkg_tone   = col_p3.selectbox("강조 포인트", ["가성비","프리미엄","친환경/안전","디자인/감성","기능성"], key="pkg_tone")

    st.markdown("##### 💬 경쟁사 리뷰 (선택 — 없으면 AI가 추론합니다)")
    col_r1, col_r2 = st.columns(2)
    pkg_good = col_r1.text_area("👍 호평 리뷰", height=90, key="pkg_good",
        placeholder="경쟁사 4~5점 리뷰 붙여넣기")
    pkg_bad  = col_r2.text_area("👎 악평 리뷰", height=90, key="pkg_bad",
        placeholder="경쟁사 1~3점 리뷰 붙여넣기")

    if st.button("🚀 원클릭 등록 패키지 자동 생성 시작", type="primary",
                 use_container_width=True, key="btn_pkg"):

        # 유효성 검사
        effective_kw = pkg_kw.strip() or html_data.get("keyword","")
        if not effective_kw:
            st.warning("상품 키워드를 입력하거나 HTML 파일을 첨부해주세요!")
            st.stop()

        # ── STEP 1: 경쟁사 상품명 수집 ───────────────────────────
        st.divider()
        st.markdown(f"### 🔍 STEP 1 — 경쟁사 상품명 수집 (`{effective_kw}`)")
        with st.spinner(f"'{effective_kw}' 네이버 상위 20개 상품명 수집 중..."):
            nv          = 네이버검색(effective_kw, 개수=20)
            comp_items  = nv.get("items", [])
            comp_total  = nv.get("total", 0)
            comp_titles = [it['title'].replace('<b>','').replace('</b>','') for it in comp_items]
            comp_prices = [int(it.get('lprice',0)) for it in comp_items]

        if comp_titles:
            st.success(f"✅ 경쟁사 {len(comp_titles)}개 수집 완료 (전체 {comp_total:,}개)")
            with st.expander("📋 수집된 경쟁사 상품명 보기"):
                for i,(t,p) in enumerate(zip(comp_titles, comp_prices), 1):
                    st.markdown(f"**{i}.** {t} — <span style='color:#03C75A;'>{p:,}원</span>",
                                unsafe_allow_html=True)
        else:
            st.warning("경쟁사 상품명 수집 실패 — AI 추론으로 진행합니다.")

        # ── STEP 2: 소싱 정보 (HTML 추출 우선 / 없으면 API 조회) ─
        st.markdown("### 💰 STEP 2 — 소싱 정보 확인")
        소싱 = None

        if html_sourcing:
            # ✅ HTML에서 추출한 소싱 그대로 사용
            소싱 = html_sourcing
            st.success("✅ HTML 파일에서 소싱 정보를 그대로 사용합니다.")
            col_s1, col_s2, col_s3 = st.columns(3)
            col_s1.metric("소싱가 (HTML 추출)", f"{소싱['총가격']:,}원")
            col_s2.metric("출처", 소싱['출처'])
            col_s3.metric("소싱처 링크", "✅ 보존됨")
            if 소싱.get('이미지'):
                st.image(소싱['이미지'], width=180, caption="소싱 이미지 (HTML 추출)")
            st.link_button("🛒 소싱처 바로가기", 소싱['링크'])
        else:
            # HTML 없거나 파싱 실패 → 새로 조회
            with st.spinner(f"'{effective_kw}' 최저가 소싱처 탐색 중..."):
                소싱 = 소싱데이터_조회(effective_kw)
            if 소싱:
                col_s1, col_s2, col_s3 = st.columns(3)
                col_s1.metric("최저 단가", f"{소싱['총가격']:,}원")
                col_s2.metric("출처", 소싱['출처'])
                col_s3.metric("실매입가", f"{소싱.get('실매입가', 소싱['총가격']):,}원")
                if 소싱.get('이미지'):
                    st.image(소싱['이미지'], width=180, caption="소싱 이미지")
                # ✅ HTML 미첨부 시 이미지 경고
                st.warning("⚠️ HTML 미첨부 — 키워드 검색 결과 이미지입니다. 실제 등록할 상품과 다를 수 있으니 아래 썸네일 교체 기능을 꼭 이용해주세요.")
            else:
                st.warning("소싱 데이터 없음 — 텍스트 기반으로 생성됩니다.")

        # ── STEP 3: 슈퍼 AI 통합 분석 ────────────────────────────
        st.markdown("### 🧠 STEP 3 — AI 슈퍼 통합 분석")

        titles_text    = "\n".join([f"{i}. {t}" for i,t in enumerate(comp_titles[:15],1)]) if comp_titles else "수집 실패"
        price_info     = f"{소싱['총가격']:,}원 ({소싱['출처']})" if 소싱 else "미확인"
        review_section = ""
        if pkg_good.strip(): review_section += f"\n[경쟁사 호평 리뷰]\n{pkg_good}\n"
        if pkg_bad.strip():  review_section += f"\n[경쟁사 악평 리뷰]\n{pkg_bad}\n"
        if not review_section:
            review_section = "\n[리뷰 없음 — 키워드와 카테고리 기반으로 고객 심리를 추론하세요]\n"

        if prev_draft:
            draft_section = f"""
[📄 기존 상세페이지 초안 — 이 상품의 이전 기획안입니다. 기반으로 업그레이드하세요]
{prev_draft}

⚠️ 반드시 위 초안과 동일한 상품({effective_kw})에 대해 작성하세요.
- 초안의 좋은 내용은 유지하되 경쟁사 분석·리뷰를 반영해 더 구체적으로 발전시키세요
- 후킹 카피와 셀링포인트는 경쟁사 데이터를 반영해 완전히 새롭게 강화하세요
"""
            mode_instruction = f"'{effective_kw}' 상품의 기존 기획 초안을 기반으로, 경쟁사 데이터까지 반영한 최종 업그레이드 버전을 작성하세요."
        else:
            draft_section    = ""
            mode_instruction = f"'{effective_kw}' 상품에 대해 아래 모든 데이터를 반영하여 완전한 상품 기획안을 작성하세요."

        super_prompt = f"""당신은 네이버 쇼핑 SEO 전문가 + 탑티어 이커머스 카피라이터 + MD의 역할을 동시에 수행합니다.
{mode_instruction}
⚠️ 출력 규칙: ###, **, - 등 마크다운만 사용하세요. 코드블록(```)과 취소선(~~)은 절대 사용 금지. 가격 범위는 반드시 '5,000원~12,000원' 형식으로 쓰세요.

[📦 상품 기본 정보]
- 키워드: {effective_kw}
- 주 타겟: {pkg_target}
- 가격대: {pkg_price}
- 강조 포인트: {pkg_tone}
- 최저 소싱가: {price_info}

[🔍 경쟁사 상위노출 상품명 {len(comp_titles)}개]
{titles_text}

[💬 경쟁사 리뷰 데이터]
{review_section}
{draft_section}

아래 형식으로 출력하세요:

### 🏷️ SEO 최적 상품명 TOP 3
(경쟁사 공통 키워드 계승 + 차별화 요소 추가, 각 100자 이내)

### 🔑 경쟁사 분석 — 상위노출 핵심 패턴
(경쟁사 상품명에서 반복되는 키워드 TOP 5 + 우리가 써야 할 이유)

### 🚨 고객 Pain Point & 우리의 해결책
(리뷰 기반 결핍 3가지 + 우리 상품의 해결책 3가지)

### 💎 핵심 셀링포인트 5가지
(경쟁사가 못하는 것 + 고객이 원하는 것 교차점 — 구체적 근거 포함)

### 📝 상단 후킹 문구 3선
(첫 3초 안에 스크롤을 멈추게 만드는 카피 — Pain Point 직격)

### ✅ 상품 특징 상세 설명 (7가지)
(소재·크기·기능·인증·사용법 등 구체적 스펙 포함)

### 🛒 상세페이지 섹션별 카피 초안
(썸네일~마지막 CTA까지 각 섹션 제목 + 본문 문구)

### 🎯 추천 검색 키워드 15개
(메인 키워드 5개 + 세부 키워드 5개 + 롱테일 5개)

### 💰 가격 전략
(경쟁사 가격대 분석 기반 최적 판매가 + 묶음 전략 + 할인 구조)

### 📦 상세페이지 구성 순서 (8단계)
(고객 구매 심리 흐름에 맞춘 섹션 배치 + 각 섹션 역할 설명)"""

        with st.spinner("AI가 모든 데이터를 통합 분석 중... (30~50초 소요)"):
            result = call_claude_api({"max_tokens": 8192,
                                      "messages": [{"role":"user","content": super_prompt}]})
        if not result:
            st.error("AI 분석 실패. 다시 시도해주세요.")
            st.stop()

        # ── 결과를 session_state에 저장 (다운로드 후 유지) ───────
        today_str   = datetime.now().strftime('%Y년 %m월 %d일')
        safe_kw     = re.sub(r'[^\w가-힣]','_', effective_kw)
        upgrade_badge = '<div class="step" style="background:rgba(3,199,90,.15);border-color:rgba(3,199,90,.4);color:#03C75A;">✅ 블루오션 초안 업그레이드</div>' if prev_draft else ''
        result_html = result
        result_html = re.sub(r'### (.+)',       r'<h3>\1</h3>', result_html)
        result_html = re.sub(r'## (.+)',        r'<h2>\1</h2>', result_html)
        result_html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', result_html)
        result_html = re.sub(r'^\* (.+)',       r'<li>\1</li>', result_html, flags=re.MULTILINE)
        result_html = result_html.replace('\n\n','</p><p>').replace('\n','<br>')

        sourcing_html = ""
        if 소싱:
            img_html = f'<img src="{소싱["이미지"]}" style="width:160px;height:160px;object-fit:cover;border-radius:10px;flex-shrink:0;">' if 소싱.get("이미지") else ""
            sourcing_html = f"""
            <div style="display:flex;gap:20px;align-items:center;background:rgba(3,199,90,.08);
            border:1px solid rgba(3,199,90,.2);border-radius:12px;padding:20px;margin-bottom:24px;">
            {img_html}
            <div>
                <div style="color:#03C75A;font-size:1.4rem;font-weight:800;margin-bottom:6px;">
                    단가 {소싱['총가격']:,}원</div>
                <div style="color:#8892a4;font-size:.9rem;">출처: {소싱['출처']}</div>
                <div style="color:#ffd700;font-size:.9rem;margin-top:4px;">
                    최소 {소싱.get('최소수량',1)}개 · 실매입 {소싱.get('실매입가', 소싱['총가격']):,}원</div>
                <a href="{소싱['링크']}" target="_blank" style="display:inline-block;margin-top:10px;
                padding:8px 18px;border-radius:7px;background:linear-gradient(45deg,#03C75A,#029f47);
                color:#fff;font-weight:700;text-decoration:none;font-size:.88rem;">🛒 소싱처 바로가기</a>
            </div></div>"""

        html_pkg = f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>👑 {effective_kw} — 원클릭 등록 패키지</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@700;900&family=Noto+Sans+KR:wght@300;400;700&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#07080f;color:#e8eaf0;font-family:'Noto Sans KR',sans-serif;line-height:1.8}}
body::before{{content:'';position:fixed;inset:0;z-index:0;
  background:radial-gradient(ellipse 80% 50% at 20% 10%,rgba(255,215,0,.06),transparent 60%),
             radial-gradient(ellipse 60% 40% at 80% 80%,rgba(3,199,90,.04),transparent 60%);
  pointer-events:none}}
@keyframes fu{{from{{opacity:0;transform:translateY(16px)}}to{{opacity:1;transform:translateY(0)}}}}
.fu{{animation:fu .6s ease both}}
header{{position:relative;z-index:1;padding:56px 40px 36px;text-align:center;
  border-bottom:1px solid rgba(255,255,255,.07);
  background:linear-gradient(180deg,rgba(255,215,0,.06),transparent)}}
header h1{{font-family:'Noto Serif KR',serif;font-size:clamp(1.8rem,4vw,3rem);
  font-weight:900;color:#ffd700;text-shadow:0 0 40px rgba(255,215,0,.35);letter-spacing:-1px}}
header .sub{{margin-top:10px;color:#8892a4;font-size:.9rem;letter-spacing:2px}}
.steps{{display:flex;flex-wrap:wrap;gap:8px;justify-content:center;
  padding:22px 30px;border-bottom:1px solid rgba(255,255,255,.07)}}
.step{{padding:6px 16px;border-radius:20px;font-size:.82rem;font-weight:700;
  background:rgba(255,215,0,.1);border:1px solid rgba(255,215,0,.25);color:#ffd700}}
main{{position:relative;z-index:1;max-width:960px;margin:0 auto;padding:40px 24px 80px}}
.card{{background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.07);
  border-radius:16px;padding:28px 32px;margin-bottom:20px;transition:border-color .3s}}
.card:hover{{border-color:rgba(255,215,0,.15)}}
.card-label{{font-size:.72rem;font-weight:700;letter-spacing:3px;text-transform:uppercase;
  color:#ffd700;margin-bottom:14px;opacity:.8}}
.card h2{{font-family:'Noto Serif KR',serif;font-size:1.2rem;color:#e8eaf0;
  margin-bottom:14px;padding-bottom:10px;border-bottom:1px solid rgba(255,255,255,.07)}}
h3{{color:#ffd700;font-size:1rem;margin:18px 0 8px}}
h2{{color:#a8d8ff!important;font-size:1.05rem;margin:20px 0 8px}}
p{{color:#8892a4;font-size:.93rem;margin-bottom:8px}}
li{{color:#8892a4;font-size:.93rem;margin:5px 0 5px 20px;list-style:none;position:relative}}
li::before{{content:'▸';position:absolute;left:-16px;color:#ffd700;font-size:.8rem}}
strong{{color:#e8eaf0}}
.comp-list{{display:flex;flex-direction:column;gap:6px}}
.comp-item{{background:rgba(255,255,255,.02);border:1px solid rgba(255,255,255,.05);
  border-radius:8px;padding:8px 14px;font-size:.85rem;color:#ccc}}
.comp-item span{{color:#03C75A;font-weight:700;margin-left:8px}}
footer{{position:relative;z-index:1;text-align:center;padding:36px;
  border-top:1px solid rgba(255,255,255,.05);color:#8892a4;font-size:.8rem}}
footer strong{{color:#ffd700}}
@media(max-width:600px){{main{{padding:24px 16px 60px}}.card{{padding:20px 18px}}}}
</style></head><body>
<header class="fu">
  <h1>👑 {effective_kw}</h1>
  <p class="sub">원클릭 등록 패키지 · {today_str} · 위탁의왕 Ultra</p>
</header>
<div class="steps">
  <div class="step">📦 소싱 정보</div>
  <div class="step">🔍 경쟁사 분석</div>
  <div class="step">🧠 AI 통합 기획</div>
  <div class="step">🏷️ SEO 상품명</div>
  <div class="step">📝 상세페이지</div>
  <div class="step">🎯 키워드 15개</div>
  <div class="step">💰 가격 전략</div>
  {upgrade_badge}
</div>
<main>
  {sourcing_html}
  <div class="card fu">
    <div class="card-label">경쟁사 분석 · {len(comp_titles)}개 수집</div>
    <h2>🔍 네이버 상위 경쟁사 상품명</h2>
    <div class="comp-list">
      {''.join([f'<div class="comp-item"><b>{i}.</b> {t}<span>{p:,}원</span></div>' for i,(t,p) in enumerate(zip(comp_titles[:10], comp_prices[:10]),1)])}
    </div>
  </div>
  <div class="card fu">
    <div class="card-label">AI Generated · Claude Sonnet · 통합 분석</div>
    <h2>📋 상품 등록 기획안 전문</h2>
    <p>{result_html}</p>
  </div>
</main>
<footer>Generated by <strong>👑 위탁의왕 Ultra</strong> · Powered by Claude AI · {today_str}</footer>
</body></html>"""

        # ── 썸네일 생성 후 bytes로 저장 ──────────────────────────
        thumb_bytes = None
        thumb_img_url = 소싱.get('이미지','') if 소싱 else ''
        if thumb_img_url:
            try:
                r = requests.get(thumb_img_url, timeout=10)
                if r.status_code == 200:
                    pil = Image.open(io.BytesIO(r.content)).convert("RGBA")
                    pil = pil.resize((800,800), Image.LANCZOS)
                    ov  = Image.new("RGBA",(800,800),(0,0,0,0))
                    od  = ImageDraw.Draw(ov)
                    for idx_i in range(220):
                        od.rectangle([0,800-220+idx_i,800,801-220+idx_i],
                                     fill=(0,0,0,int(185*(idx_i/220))))
                    pil  = Image.alpha_composite(pil, ov)
                    draw = ImageDraw.Draw(pil)
                    try:
                        fm = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
                        fs = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
                    except:
                        fm = fs = ImageFont.load_default()
                    label_kw = effective_kw[:16]
                    bb = draw.textbbox((0,0), label_kw, font=fm)
                    draw.text(((800-(bb[2]-bb[0]))//2, 620), label_kw, font=fm, fill=(255,215,0))
                    if 소싱:
                        price_txt = f"소싱가 {소싱['총가격']:,}원"
                        bb2 = draw.textbbox((0,0), price_txt, font=fs)
                        draw.text(((800-(bb2[2]-bb2[0]))//2, 675), price_txt, font=fs, fill=(3,199,90))
                    buf = io.BytesIO()
                    pil.convert("RGB").save(buf, format="JPEG", quality=95)
                    thumb_bytes = buf.getvalue()
            except Exception as e:
                st.warning(f"썸네일 생성 실패: {e}")

        # ── 서버 저장 ─────────────────────────────────────────────
        save_dir = "등록패키지_저장"
        os.makedirs(save_dir, exist_ok=True)
        pkg_path = os.path.join(save_dir, f"등록패키지_{safe_kw}_{datetime.now().strftime('%Y%m%d%H%M')}.html")
        with open(pkg_path, 'w', encoding='utf-8') as f:
            f.write(html_pkg)

        # ✅ 모든 결과를 session_state에 저장 → 다운로드 후에도 유지
        st.session_state['pkg_outputs'] = {
            'result':       result,
            'html_pkg':     html_pkg,
            'thumb_bytes':  thumb_bytes,
            'safe_kw':      safe_kw,
            'effective_kw': effective_kw,
            'pkg_path':     pkg_path,
            'today_str':    today_str,
        }
        st.rerun()   # ← 재실행해서 아래 결과 표시 블록으로 이동

    # ── 결과 표시 (session_state 기반 — 다운로드 후에도 유지) ────
    out = st.session_state.get('pkg_outputs', {})
    if out:
        st.divider()

        # 헤더 + 초기화 버튼
        col_hd, col_clr = st.columns([4, 1])
        with col_hd:
            st.markdown(f"### ✅ `{out['effective_kw']}` 패키지 완성")
        with col_clr:
            if st.button("🗑️ 결과 초기화", key="btn_clear_pkg", type="secondary"):
                st.session_state['pkg_outputs'] = {}
                st.rerun()

        # STEP 4: 기획안
        st.markdown("### 📋 STEP 4 — 완성 기획안")
        st.markdown(out['result'])
        st.divider()
        st.text_area("📋 텍스트 복사하기", value=out['result'], height=200, key="pkg_copy")

        # STEP 5: 썸네일
        st.markdown("### 🖼️ STEP 5 — 썸네일")

        # ── 현재 썸네일 표시 ─────────────────────────────────────
        current_thumb = st.session_state['pkg_outputs'].get('thumb_bytes')
        if current_thumb:
            st.image(current_thumb, width=300, caption="현재 썸네일")
        else:
            st.info("💡 소싱 이미지가 없어 자동 썸네일을 건너뜁니다.")

        # ── 이미지 교체 기능 ──────────────────────────────────────
        st.markdown("""<div style="background:rgba(255,215,0,.06);border:1px solid rgba(255,215,0,.2);
        border-radius:10px;padding:12px 18px;margin:12px 0;">
        <b style="color:#ffd700;">🔄 다른 이미지로 썸네일 교체</b><br>
        <span style="color:#aaa;font-size:.85rem;">
        원하는 사진을 업로드하면 배지·상품명·소싱가 텍스트를 동일하게 합성해서 새 썸네일을 만들어드립니다.
        </span></div>""", unsafe_allow_html=True)

        col_up1, col_up2 = st.columns([2, 1])
        with col_up1:
            new_img_file = st.file_uploader(
                "📷 교체할 이미지 업로드 (JPG/PNG)",
                type=["jpg","jpeg","png"],
                key="pkg_thumb_replace"
            )
        with col_up2:
            st.markdown("<br>", unsafe_allow_html=True)
            # 배지 옵션
            add_badge = st.checkbox("배지 추가", value=True, key="pkg_thumb_badge")
            badge_txt = st.text_input("배지 문구", value="가성비 1위", key="pkg_thumb_badge_txt") if add_badge else ""

        if new_img_file:
            try:
                pil_new = Image.open(io.BytesIO(new_img_file.getvalue())).convert("RGBA")
                pil_new = pil_new.resize((800,800), Image.LANCZOS)

                # 하단 어두운 오버레이
                ov  = Image.new("RGBA",(800,800),(0,0,0,0))
                od  = ImageDraw.Draw(ov)
                for idx_i in range(220):
                    od.rectangle([0,800-220+idx_i,800,801-220+idx_i],
                                 fill=(0,0,0,int(185*(idx_i/220))))
                pil_new = Image.alpha_composite(pil_new, ov)
                draw    = ImageDraw.Draw(pil_new)

                try:
                    fm = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
                    fs = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
                    fb = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
                except:
                    fm = fs = fb = ImageFont.load_default()

                # 배지 (좌상단)
                if add_badge and badge_txt:
                    bw, bh = 200, 48
                    draw.rounded_rectangle([16,16,16+bw,16+bh], radius=10, fill=(255,215,0))
                    bb = draw.textbbox((0,0), badge_txt, font=fb)
                    tw, th = bb[2]-bb[0], bb[3]-bb[1]
                    draw.text((16+(bw-tw)//2, 16+(bh-th)//2), badge_txt, font=fb, fill=(3,30,10))

                # 상품명 + 소싱가
                kw_label = out['effective_kw'][:16]
                bb = draw.textbbox((0,0), kw_label, font=fm)
                draw.text(((800-(bb[2]-bb[0]))//2, 620), kw_label, font=fm, fill=(255,215,0))

                out_소싱 = st.session_state['pkg_outputs']
                price_txt = f"소싱가 {out['result'][:10]}" if out.get('result') else ""
                # 소싱가를 session_state에서 안전하게 가져오기
                if out.get('html_pkg'):
                    pm = re.search(r'단가\s*([\d,]+)원', out['html_pkg'])
                    if pm: price_txt = f"소싱가 {pm.group(1)}원"
                if price_txt:
                    bb2 = draw.textbbox((0,0), price_txt, font=fs)
                    draw.text(((800-(bb2[2]-bb2[0]))//2, 675), price_txt, font=fs, fill=(3,199,90))

                new_thumb_rgb = pil_new.convert("RGB")
                new_buf = io.BytesIO()
                new_thumb_rgb.save(new_buf, format="JPEG", quality=95)
                new_thumb_bytes = new_buf.getvalue()

                # 미리보기 + 저장 버튼
                col_pv1, col_pv2 = st.columns([1,1])
                with col_pv1:
                    st.image(new_thumb_bytes, width=280, caption="새 썸네일 미리보기")
                with col_pv2:
                    st.markdown("<br><br>", unsafe_allow_html=True)
                    if st.button("✅ 이 썸네일로 교체 저장", type="primary",
                                 use_container_width=True, key="btn_replace_thumb"):
                        st.session_state['pkg_outputs']['thumb_bytes'] = new_thumb_bytes
                        st.success("✅ 썸네일이 교체됐습니다! 아래에서 다운로드하세요.")
                        st.rerun()

                    st.download_button(
                        "⬇️ 새 썸네일 바로 다운로드",
                        data=new_thumb_bytes,
                        file_name=f"썸네일_교체_{out['safe_kw']}.jpg",
                        mime="image/jpeg",
                        use_container_width=True,
                        key="dl_new_thumb"
                    )
            except Exception as e:
                st.error(f"이미지 처리 오류: {e}")

        # STEP 6: 다운로드 (session_state에서 읽어서 재실행 후에도 버튼 유지)
        st.markdown("### 📥 STEP 6 — 완성 패키지 다운로드")
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            st.download_button(
                "📥 완성 패키지 HTML 다운로드",
                data=out['html_pkg'],
                file_name=f"등록패키지_{out['safe_kw']}_{out['today_str'][:10].replace('년 ','').replace('월 ','').replace('일','')}.html",
                mime="text/html",
                use_container_width=True,
                type="primary",
                key="dl_pkg_html"
            )
        if out.get('thumb_bytes'):
            with col_d2:
                st.download_button(
                    "🖼️ 썸네일 다운로드 (800×800)",
                    data=out['thumb_bytes'],
                    file_name=f"썸네일_{out['safe_kw']}.jpg",
                    mime="image/jpeg",
                    use_container_width=True,
                    key="dl_pkg_thumb"
                )

        st.success(f"✅ 서버 저장 완료: `{out['pkg_path']}`")
        st.markdown("""
        <div style="background:rgba(3,199,90,.08);border:1px solid rgba(3,199,90,.2);
        border-radius:10px;padding:14px 18px;margin-top:16px;">
        <b style="color:#03C75A;">💡 다음 단계 활용 가이드</b><br>
        <span style="color:#ccc;font-size:.9rem;">
        1. HTML 파일을 열어 <b>SEO 상품명 TOP 3</b> 중 하나를 스마트스토어 상품명으로 사용<br>
        2. <b>추천 검색 키워드 15개</b>를 스마트스토어 검색태그에 입력<br>
        3. <b>상세페이지 구성 순서 8단계</b>대로 이미지 제작<br>
        4. 다운로드한 <b>썸네일</b>을 대표이미지로 바로 업로드
        </span></div>""", unsafe_allow_html=True)
