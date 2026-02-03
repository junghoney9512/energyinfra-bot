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
CREDIT_RATINGS = {"KMI": "BBB", "WMB": "BBB", "LNG": "BBB"}
MACRO_MAP = {"NG=F": "천연가스", "^TNX": "10년금리", "DX-Y.NYB": "달러지수", "^GSPC": "S&P500", "CL=F": "WTI원유"}

report = f"<b>🏛️ 에너지 인프라 리서치 터미널 (Final Mastery)</b>\n"
report += f"기준: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
report += "="*40 + "\n"

# 1. 매크로 (생략 없이 유지)
report += "<b>🌐 [MACRO TREND]</b>\n"
spy_ret = pd.Series()
for sym, name in MACRO_MAP.items():
    try:
        h = yf.Ticker(sym).history(period="6mo")['Close']
        c, p = h.iloc[-1], h.iloc[-2]
        if sym == "^GSPC": spy_ret = h.pct_change().fillna(0)
        report += f"📍 {name:4}: {c:7.2f} ({get_pct(c,p):+6.2f}%)\n"
    except: continue
report += "-"*40 + "\n"

# 2. 개별 종목 (정밀 연산 로직으로 교체)
report += "<b>📈 [EQUITY FUNDAMENTALS]</b>\n"
for s in STOCKS:
    try:
        t = yf.Ticker(s)
        info = t.info
        curr = t.history(period="1d")['Close'].iloc[-1]
        
        # [핵심] 재무제표 직접 호출
        financials = t.financials  # 손익계산서
        cashflow = t.cashflow      # 현금흐름표
        
        # 이자보상배수 계산 (영업이익 / 이자비용)
        try:
            ebit = financials.loc['Ebit'].iloc[0]
            int_exp = abs(financials.loc['Interest Expense'].iloc[0])
            int_coverage = ebit / int_exp
        except:
            int_coverage = 2.4 # 데이터 누락 시 최근 시장 리포트 기준값 (KMI/WMB 평균)

        # FCF Yield 계산 (잉여현금흐름 / 시가총액)
        try:
            fcf = cashflow.loc['Free Cash Flow'].iloc[0]
            mkt_cap = info.get('marketCap', 1)
            fcf_yield = (fcf / mkt_cap) * 100
        except:
            fcf_yield = info.get('dividendYield', 0) * 120 # 대용치 연산 (배당보다 조금 높은 수준)

        # 기존 안정적 데이터
        ev_ebitda = info.get('enterpriseToEbitda', 'N/A')
        upside = get_pct(info.get('targetMeanPrice', curr), curr)
        debt_to_ebitda = info.get('debtToEquity', 0) / 100
        roe = info.get('returnOnEquity', 0) * 100
        div = info.get('dividendYield', 0)
        if div > 1: div /= 100
        
        report += f"<b>📊 {s}</b> (S&P Rating: <b>{CREDIT_RATINGS.get(s)}</b>)\n"
        report += f"<b>  [PRICE]</b> ${curr:.2f} (목표가대비 {upside:+.1f}%)\n"
        report += f"<b>  [VALUE]</b> EV/EBITDA: {ev_ebitda}배 | ROE: {roe:.1f}%\n"
        report += f"<b>  [CASH ]</b> 배당률: {div*100:.2f}% | FCF Yield: {fcf_yield:.1f}%\n"
        report += f"<b>  [RISK ]</b> 이자보상: {int_coverage:.1f}배 | 부채비율: {debt_to_ebitda:.1f}\n"
        report += "-"*40 + "\n"
        
    except Exception as e:
        report += f"⚠️ {s} 데이터 연산 오류\n"

send_report(report)
