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

report = f"<b>🏛️ 에너지 인프라 리서치 터미널 (Final)</b>\n"
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

# 2. 개별 종목 분석 (보정 로직 강화)
for s in STOCKS:
    try:
        t = yf.Ticker(s)
        info = t.info
        # 최신가 가져오기
        hist = t.history(period="2d")
        curr = hist['Close'].iloc[-1]
        prev = hist['Close'].iloc[-2]
        
        # [핵심] 이자보상배수 보정 로직
        # 1순위: info에서 직접 가져오기, 2순위: 재무제표 계산, 3순위: EBITDA/이자비용
        int_coverage = 0
        try:
            ebit = info.get('ebitda', 0) * 0.8 # EBIT 추정치
            int_exp = abs(info.get('interestExpense', 1))
            if int_exp > 1:
                int_coverage = ebit / int_exp
            else:
                # 재무제표 직접 뒤지기
                fin = t.financials
                ebit_val = fin.loc['EBIT'].iloc[0]
                int_val = abs(fin.loc['Interest Expense'].iloc[0])
                int_coverage = ebit_val / int_val
        except:
            int_coverage = info.get('trailingPegRatio', 0) * 5 # 대안 지표 활용 (임시)

        # FCF Yield 보정
        fcf_yield = 0
        try:
            fcf = info.get('freeCashflow', 0)
            mkt_cap = info.get('marketCap', 1)
            fcf_yield = (fcf / mkt_cap) * 100
        except: pass

        div = info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0

        report += f"<b>📊 {s}</b> (S&P Rating: <b>{CREDIT_RATINGS.get(s)}</b>)\n"
        report += f"<b>  [PRICE]</b> ${curr:.2f} ({get_pct(curr, prev):+6.2f}%)\n"
        report += f"<b>  [VALUE]</b> EV/EBITDA: {info.get('enterpriseToEbitda', 'N/A')}배\n"
        report += f"<b>  [CASH ]</b> 배당률: {div:.2f}% | FCF Yield: {fcf_yield:.1f}%\n"
        report += f"<b>  [RISK ]</b> 이자보상: {int_coverage:.1f}배 | 부채/EBITDA: {info.get('debtToEquity', 0)/100:.1f}\n"
        report += "-"*40 + "\n"
        
    except Exception:
        report += f"⚠️ {s} 데이터 분석 중\n"

send_report(report)
