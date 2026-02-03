import yfinance as yf
import requests
import os
from datetime import datetime

# ==========================================
FMP_API_KEY = "여기에_전문가님의_키를_넣으세요" 
# ==========================================
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

def get_fmp(url):
    try:
        res = requests.get(url)
        data = res.json()
        # 데이터가 리스트로 오면 첫 번째 항목(최신 데이터)을 반환
        if isinstance(data, list) and len(data) > 0:
            return data[0]
        return {}
    except: return {}

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

report = f"<b>🏛️ 에너지 인프라 리서치 터미널 (Pro Final)</b>\n"
report += f"기준: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
report += "="*40 + "\n"

# 1. 매크로 섹션 (yfinance)
report += "<b>🌐 [MACRO TREND]</b>\n"
for sym, name in MACRO_MAP.items():
    try:
        h = yf.Ticker(sym).history(period="5d")['Close']
        c, p = h.iloc[-1], h.iloc[-2]
        report += f"📍 {name:4}: {c:7.2f} ({get_pct(c,p):+6.2f}%)\n"
    except: continue
report += "-"*40 + "\n"

# 2. 개별 종목 분석 (FMP 최신 필드명 매핑)
for s in STOCKS:
    try:
        quote = get_fmp(f"https://financialmodelingprep.com/api/v3/quote/{s}?apikey={FMP_API_KEY}")
        # 'ratios'와 'key-metrics'에서 최신 연간 데이터를 가져옴
        ratios = get_fmp(f"https://financialmodelingprep.com/api/v3/ratios/{s}?limit=1&apikey={FMP_API_KEY}")
        metrics = get_fmp(f"https://financialmodelingprep.com/api/v3/key-metrics/{s}?limit=1&apikey={FMP_API_KEY}")

        curr = quote.get('price', 0)
        change = quote.get('changesPercentage', 0)
        
        # [수정] FMP 최신 API 필드명으로 정확히 매핑
        int_coverage = ratios.get('interestCoverage', 0)
        fcf_yield = ratios.get('freeCashFlowYield', 0) * 100
        div_yield = ratios.get('dividendYield', 0) * 100
        
        # Metrics 필드명 보정
        ev_ebitda = metrics.get('enterpriseValueOverEBITDA', 0)
        roe = metrics.get('roe', 0) * 100
        # 부채비율 (Debt to Equity 또는 Net Debt to EBITDA)
        debt_to_ebitda = metrics.get('netDebtToEBITDA', 0)

        report += f"<b>📊 {s}</b> (S&P Rating: <b>{CREDIT_RATINGS.get(s)}</b>)\n"
        report += f"<b>  [PRICE]</b> ${curr:.2f} ({change:+.2f}%)\n"
        report += f"<b>  [VALUE]</b> EV/EBITDA: {ev_ebitda:.1f}배 | ROE: {roe:.1f}%\n"
        report += f"<b>  [CASH ]</b> 배당률: {div_yield:.2f}% | FCF Yield: {fcf_yield:.1f}%\n"
        report += f"<b>  [RISK ]</b> 이자보상: {int_coverage:.1f}배 | 부채/EBITDA: {debt_to_ebitda:.1f}\n"
        report += "-"*40 + "\n"
        
    except Exception:
        report += f"⚠️ {s} 데이터 연산 중\n"

send_report(report)
