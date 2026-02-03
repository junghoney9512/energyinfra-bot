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
        return data[0] if isinstance(data, list) and len(data) > 0 else {}
    except: return {}

def send_report(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    requests.post(url, data=payload)

STOCKS = ["KMI", "WMB", "LNG"]
CREDIT_RATINGS = {"KMI": "BBB", "WMB": "BBB", "LNG": "BBB"}

report = f"<b>🏛️ 에너지 인프라 리서치 터미널 (Direct Calc)</b>\n"
report += f"기준: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
report += "="*40 + "\n"

for s in STOCKS:
    try:
        # 1. 원시 데이터 호출 (가장 누락이 없는 기본 엔드포인트)
        quote = get_fmp(f"https://financialmodelingprep.com/api/v3/quote/{s}?apikey={FMP_API_KEY}")
        income = get_fmp(f"https://financialmodelingprep.com/api/v3/income-statement/{s}?limit=1&apikey={FMP_API_KEY}")
        balance = get_fmp(f"https://financialmodelingprep.com/api/v3/balance-sheet-statement/{s}?limit=1&apikey={FMP_API_KEY}")
        cashflow = get_fmp(f"https://financialmodelingprep.com/api/v3/cash-flow-statement/{s}?limit=1&apikey={FMP_API_KEY}")

        # 2. 직접 연산 로직 (Raw Data -> Metrics)
        ebit = income.get('operatingIncome', 0)
        interest_exp = abs(income.get('interestExpense', 1)) # 분모 0 방지
        int_coverage = ebit / interest_exp if interest_exp != 0 else 0
        
        fcf = cashflow.get('freeCashFlow', 0)
        mkt_cap = quote.get('marketCap', 1)
        fcf_yield = (fcf / mkt_cap) * 100

        total_debt = balance.get('totalDebt', 0)
        ebitda = income.get('ebitda', 1)
        debt_to_ebitda = total_debt / ebitda if ebitda != 0 else 0

        curr = quote.get('price', 0)
        change = quote.get('changesPercentage', 0)

        report += f"<b>📊 {s}</b> (S&P Rating: <b>{CREDIT_RATINGS.get(s)}</b>)\n"
        report += f"<b>  [PRICE]</b> ${curr:.2f} ({change:+.2f}%)\n"
        report += f"<b>  [VALUE]</b> EBIT: ${ebit/1e9:.1f}B | Mkt Cap: ${mkt_cap/1e9:.1f}B\n"
        report += f"<b>  [CASH ]</b> FCF Yield: {fcf_yield:.1f}%\n"
        report += f"<b>  [RISK ]</b> 이자보상: {int_coverage:.1f}배 | 부채/EBITDA: {debt_to_ebitda:.1f}\n"
        report += "-"*40 + "\n"
        
    except Exception:
        report += f"⚠️ {s} 데이터 계산 중\n"

send_report(report)
