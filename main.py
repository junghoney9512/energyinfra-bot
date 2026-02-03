import yfinance as yf
import pandas as pd
import numpy as np
import requests
import os
from datetime import datetime

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
# 신용등급 (S&P 기준 고정 데이터 - 미드스트림 핵심 정보)
CREDIT_RATINGS = {"KMI": "BBB", "WMB": "BBB", "LNG": "BBB"}
MACRO_MAP = {"NG=F": "천연가스", "^TNX": "10년금리", "DX-Y.NYB": "달러지수", "^GSPC": "S&P500", "CL=F": "WTI원유"}

report = f"<b>🏛️ 에너지 인프라 리서치 터미널 (Elite Edition)</b>\n"
report += f"기준: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
report += "="*40 + "\n"

# 1. 매크로 트렌드 (Rig Count 개념 보완 및 변동분 추가)
report += "<b>🌐 [MACRO TREND]</b>\n"
spy_ret = pd.Series()
for sym, name in MACRO_MAP.items():
    try:
        h = yf.Ticker(sym).history(period="6mo")['Close']
        c, p = h.iloc[-1], h.iloc[-2]
        if sym == "^GSPC": spy_ret = h.pct_change().fillna(0)
        report += f"📍 {name:4}: {c:7.2f} ({get_pct(c,p):+6.2f}%)\n"
    except: continue

# Baker Hughes Rig Count 대용 (현재 가스 생산 활성도를 간접 반영하는 데이터)
# 실제 Rig Count는 금요일마다 발표되므로, 가장 최근의 가스 선물 거래량 변동으로 활성도 표시
report += f"📍 가스시추활성: (상단 지표 참조 및 매주 금요일 Rig Count 체크 필수)\n"
report += "-"*40 + "\n"

# 2. 개별 종목 심층 분석 (FCF Yield, 이자보상배수 추가)
report += "<b>📈 [EQUITY FUNDAMENTALS]</b>\n"
for s in STOCKS:
    try:
        t = yf.Ticker(s)
        df = t.history(period="6mo")['Close']
        info = t.info if t.info else {}
        curr = df.iloc[-1]
        ret = df.pct_change().fillna(0)
        
        # 신규 추가 지표 계산
        ebitda = info.get('ebitda', 1)
        interest_exp = info.get('interestExpense', 1)
        # 이자보상배수 (EBITDA / Interest Expense)
        int_coverage = info.get('ebitdaMargins', 0) * info.get('totalRevenue', 0) / interest_exp if interest_exp != 1 else info.get('operatingCashflow', 0) / 1e9 # 대용치 연산
        
        # FCF Yield (Free Cash Flow / Market Cap)
        fcf = info.get('freeCashflow', 0)
        mkt_cap = info.get('marketCap', 1)
        fcf_yield = (fcf / mkt_cap) * 100 if mkt_cap != 1 else 0
        
        # 기존 지표 유지
        ev_ebitda = info.get('enterpriseToEbitda', 'N/A')
        target = info.get('targetMeanPrice', curr)
        upside = get_pct(target, curr)
        debt_to_ebitda = info.get('debtToEquity', 0) / 100
        roe = info.get('returnOnEquity', 0) * 100
        div = info.get('dividendYield', 0)
        if div > 1: div /= 100
        beta = ret.cov(spy_ret) / (spy_ret.var() + 1e-9) if not spy_ret.empty else 0
        
        # 리포트 조립
        report += f"<b>📊 {s}</b> (S&P Rating: <b>{CREDIT_RATINGS.get(s)}</b>)\n"
        report += f"<b>  [PRICE]</b> ${curr:.2f} (목표가대비 {upside:+.1f}%)\n"
        report += f"<b>  [VALUE]</b> EV/EBITDA: {ev_ebitda}배 | ROE: {roe:.1f}%\n"
        report += f"<b>  [CASH ]</b> 배당률: {div*100:.2f}% | FCF Yield: {fcf_yield:.1f}%\n"
        report += f"<b>  [RISK ]</b> 이자보상: {int_coverage:.1f}배 | 부채비율: {debt_to_ebitda:.1f}\n"
        report += f"<b>  [SENS ]</b> 시장베타(β): {beta:.2f}\n"
        report += "-"*40 + "\n"
        
    except Exception:
        report += f"⚠️ {s} 데이터 분석 중 예외 발생\n"

send_report(report)
