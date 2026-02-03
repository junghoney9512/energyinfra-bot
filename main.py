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

report = f"<b>🏛️ 에너지 인프라 리서치 터미널 (Elite Edition)</b>\n"
report += f"기준: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
report += "="*40 + "\n"

# 1. 매크로 섹션 (유지)
report += "<b>🌐 [MACRO TREND]</b>\n"
for sym, name in MACRO_MAP.items():
    try:
        h = yf.Ticker(sym).history(period="5d")['Close']
        c, p = h.iloc[-1], h.iloc[-2]
        report += f"📍 {name:4}: {c:7.2f} ({get_pct(c,p):+6.2f}%)\n"
    except: continue
report += "-"*40 + "\n"

# 2. 개별 종목 정밀 분석
for s in STOCKS:
    try:
        t = yf.Ticker(s)
        # 펀더멘탈 데이터 추출 로직 보강
        info = t.info
        curr = t.history(period="1d")['Close'].iloc[-1]
        
        # 재무제표 항목 찾기 (유연한 매칭)
        fin = t.financials
        cf = t.cashflow
        
        # 이자보상배수 정밀 계산
        int_coverage = "N/A"
        try:
            # EBIT와 이자비용 항목을 리스트에서 검색
            ebit_idx = [i for i in fin.index if 'EBIT' in i.upper() and 'MARGIN' not in i.upper()][0]
            int_idx = [i for i in fin.index if 'INTEREST EXPENSE' in i.upper()][0]
            
            ebit_val = fin.loc[ebit_idx].iloc[0]
            int_val = abs(fin.loc[int_idx].iloc[0])
            
            if int_val != 0:
                int_coverage = f"{ebit_val / int_val:.1f}"
        except: pass

        # FCF Yield 정밀 계산
        fcf_yield_val = "N/A"
        try:
            fcf_idx = [i for i in cf.index if 'FREE CASH FLOW' in i.upper()][0]
            fcf_val = cf.loc[fcf_idx].iloc[0]
            mkt_cap = info.get('marketCap')
            if mkt_cap:
                fcf_yield_val = f"{(fcf_val / mkt_cap) * 100:.1f}"
        except: pass

        # 기존 밸류에이션 데이터
        ev_ebitda = info.get('enterpriseToEbitda', 'N/A')
        upside = get_pct(info.get('targetMeanPrice', curr), curr)
        roe = info.get('returnOnEquity', 0) * 100
        div = info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0
        if div > 50: div /= 100 # 단위 오류 방지

        report += f"<b>📊 {s}</b> (S&P Rating: <b>{CREDIT_RATINGS.get(s)}</b>)\n"
        report += f"<b>  [PRICE]</b> ${curr:.2f} (목표가대비 {upside:+.1f}%)\n"
        report += f"<b>  [VALUE]</b> EV/EBITDA: {ev_ebitda}배 | ROE: {roe:.1f}%\n"
        report += f"<b>  [CASH ]</b> 배당률: {div:.2f}% | FCF Yield: {fcf_yield_val}%\n"
        report += f"<b>  [RISK ]</b> 이자보상: {int_coverage}배 | 부채/EBITDA: {info.get('debtToEquity', 0)/100:.1f}\n"
        report += "-"*40 + "\n"
        
    except Exception:
        report += f"⚠️ {s} 데이터 분석 오류\n"

send_report(report)
