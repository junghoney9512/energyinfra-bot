import yfinance as yf
import requests
import os
from datetime import datetime

# 설정 영역
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

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

report = f"<b>🏛️ 에너지 인프라 리서치 터미널</b>\n"
report += f"기준: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
report += "="*40 + "\n"

# 1. 매크로 섹션
report += "<b>🌐 [MACRO TREND]</b>\n"
for sym, name in MACRO_MAP.items():
    try:
        h = yf.Ticker(sym).history(period="5d")['Close']
        c, p = h.iloc[-1], h.iloc[-2]
        report += f"📍 {name:4}: {c:7.2f} ({get_pct(c,p):+6.2f}%)\n"
    except: continue
report += "-"*40 + "\n"

# 2. 개별 종목 분석
for s in STOCKS:
    try:
        t = yf.Ticker(s)
        info = t.info
        curr = t.history(period="1d")['Close'].iloc[-1]
        
        # [1] 배당률 보정 (0.06 -> 6.0% / 6.0 -> 6.0% 양쪽 모두 대응)
        div = info.get('dividendYield', 0)
        if div is None: div = 0
        if div < 0.2: # 0.06 같은 소수점 형태로 들어온 경우
            div *= 100
        # 만약 0.00%로 찍히면 trailingDividendYield 확인
        if div == 0:
            div = (info.get('trailingAnnualDividendYield', 0)) * 100

        # [2] 이자보상배수 (Interest Coverage) 보정
        # EBIT / Interest Expense
        ebit = info.get('ebitda', 0) * 0.85 # 감가상각 고려한 EBIT 추정
        int_exp = abs(info.get('interestExpense', 0))
        if int_exp > 0:
            int_coverage = ebit / int_exp
        else:
            int_coverage = 0 # 데이터 부재 시 0

        # [3] 부채/EBITDA (Leverage) - 미드스트림 핵심 지표
        ebitda = info.get('ebitda', 1)
        total_debt = info.get('totalDebt', 0)
        leverage = total_debt / ebitda if ebitda > 1 else 0

        # [4] FCF Yield
        fcf = info.get('freeCashflow', 0)
        mkt_cap = info.get('marketCap', 1)
        fcf_yield = (fcf / mkt_cap) * 100 if fcf else 0

        report += f"<b>📊 {s}</b> (S&P Rating: <b>{CREDIT_RATINGS.get(s)}</b>)\n"
        report += f"<b>  [PRICE]</b> ${curr:.2f}\n"
        report += f"<b>  [VALUE]</b> EV/EBITDA: {info.get('enterpriseToEbitda', 'N/A')}배\n"
        report += f"<b>  [CASH ]</b> 배당률: {div:.2f}% | FCF Yield: {fcf_yield:.1f}%\n"
        report += f"<b>  [RISK ]</b> 이자보상: {int_coverage:.1f}배 | 부채/EBITDA: {leverage:.1f}배\n"
        report += "-"*40 + "\n"
        
    except Exception:
        report += f"⚠️ {s} 분석 중\n"

send_report(report)
