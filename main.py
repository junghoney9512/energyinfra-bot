import yfinance as yf
import requests
import os
from datetime import datetime

# ==========================================
FMP_API_KEY = "H3dnniJWrc9tQpN0I7Hk8Zk2EP8B8kSf" 
# ==========================================
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

def get_fmp(url):
    try:
        res = requests.get(url)
        return res.json()
    except: return None

def send_report(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    requests.post(url, data=payload)

def get_pct(curr, prev):
    if not prev or prev == 0: return 0
    return ((curr - prev) / prev) * 100

STOCKS = ["KMI", "WMB", "LNG"]
CREDIT_RATINGS = {"KMI": "BBB", "WMB": "BBB", "LNG": "BBB"}
MACRO_MAP = {"NG=F": "천연가스", "^TNX": "10년금리", "DX-Y.NYB": "달러지수", "^GSPC": "S&P500", "CL=F": "WTI원유"}

report = f"<b>🏛️ 에너지 인프라 리서치 터미널 (Pro Edition)</b>\n"
report += f"기준: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
report += "="*40 + "\n"

# 1. 매크로 섹션 (경제적 호출을 위해 yfinance 유지)
report += "<b>🌐 [MACRO TREND]</b>\n"
for sym, name in MACRO_MAP.items():
    try:
        h = yf.Ticker(sym).history(period="5d")['Close']
        c, p = h.iloc[-1], h.iloc[-2]
        report += f"📍 {name:4}: {c:7.2f} ({get_pct(c,p):+6.2f}%)\n"
    except: continue
report += "-"*40 + "\n"

# 2. 개별 종목 정밀 분석 (FMP API 활용)
for s in STOCKS:
    try:
        # 데이터 호출
        quote = get_fmp(f"https://financialmodelingprep.com/api/v3/quote/{s}?apikey={FMP_API_KEY}")[0]
        ratios = get_fmp(f"https://financialmodelingprep.com/api/v3/ratios-ttm/{s}?apikey={FMP_API_KEY}")[0]
        metrics = get_fmp(f"https://financialmodelingprep.com/api/v3/key-metrics-ttm/{s}?apikey={FMP_API_KEY}")[0]

        curr = quote.get('price', 0)
        change = quote.get('changesPercentage', 0)
        
        # FMP의 정밀 계산값 추출
        int_coverage = ratios.get('interestCoverageTTM', 0)
        fcf_yield = ratios.get('freeCashFlowYieldTTM', 0) * 100
        div_yield = ratios.get('dividendYieldTTM', 0) * 100
        ev_ebitda = metrics.get('enterpriseValueOverEBITDATTM', 0)
        roe = metrics.get('roeTTM', 0) * 100
        debt_ebitda = metrics.get('netDebtToEBITDATTM', 0)

        report += f"<b>📊 {s}</b> (S&P Rating: <b>{CREDIT_RATINGS.get(s)}</b>)\n"
        report += f"<b>  [PRICE]</b> ${curr:.2f} ({change:+.2f}%)\n"
        report += f"<b>  [VALUE]</b> EV/EBITDA: {ev_ebitda:.1f}배 | ROE: {roe:.1f}%\n"
        report += f"<b>  [CASH ]</b> 배당률: {div_yield:.2f}% | FCF Yield: {fcf_yield:.1f}%\n"
        report += f"<b>  [RISK ]</b> 이자보상: {int_coverage:.1f}배 | 부채/EBITDA: {debt_ebitda:.1f}\n"
        report += "-"*40 + "\n"
        
    except Exception:
        report += f"⚠️ {s} 데이터 호출 실패 (키 확인 필요)\n"

send_report(report)
