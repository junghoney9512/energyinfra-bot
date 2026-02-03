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

STOCKS = ["KMI", "WMB", "LNG"]
CREDIT_RATINGS = {"KMI": "BBB", "WMB": "BBB", "LNG": "BBB"}

report = f"<b>🏛️ 에너지 인프라 리서치 정밀 리포트</b>\n"
report += f"기준: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
report += "="*40 + "\n"

for s in STOCKS:
    try:
        t = yf.Ticker(s)
        info = t.info
        curr = t.history(period="1d")['Close'].iloc[-1]
        
        # 1. 이자보상배수 (정밀 계산: EBIT / Interest Expense)
        # Operating Cash Flow에서 이자비용을 역산하거나 EBIT 데이터를 우선순위로 타격
        ebit = info.get('ebitda', 0) - info.get('amortization', 0) # EBITDA에서 감가상각 제외 시도
        if ebit <= 0: ebit = info.get('operatingCashflow', 0) * 0.7 # 보수적 추정
        
        int_exp = abs(info.get('interestExpense', 0))
        int_coverage = f"{ebit / int_exp:.2f}" if int_exp > 0 else "N/A"

        # 2. FCF Yield (Free Cash Flow / Market Cap)
        fcf = info.get('freeCashflow', 0)
        mkt_cap = info.get('marketCap', 1)
        fcf_yield = f"{(fcf / mkt_cap) * 100:.2f}" if fcf > 0 else "N/A"

        # 3. 부채/EBITDA (Net Debt / EBITDA 타겟팅)
        net_debt = info.get('totalDebt', 0) - info.get('totalCash', 0)
        ebitda = info.get('ebitda', 1)
        leverage = f"{net_debt / ebitda:.2f}" if ebitda > 1 else "N/A"

        # 4. 배당률 (정확한 % 표기)
        div = info.get('dividendYield', 0)
        if div and div < 0.2: div *= 100
        elif not div: div = (info.get('trailingAnnualDividendYield', 0)) * 100

        report += f"<b>📊 {s}</b> (S&P: <b>{CREDIT_RATINGS.get(s)}</b>)\n"
        report += f"<b>  [PRICE]</b> ${curr:.2f}\n"
        report += f"<b>  [CASH ]</b> 배당: {div:.2f}% | FCF Yield: {fcf_yield}%\n"
        report += f"<b>  [RISK ]</b> 이자보상: {int_coverage}배 | NetDebt/EBITDA: {leverage}배\n"
        report += "-"*40 + "\n"
        
    except Exception:
        report += f"⚠️ {s} 데이터 정밀 분석 실패\n"

send_report(report)
