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

# 2. 개별 종목 분석 (SENS 파트 삭제 및 최적화)
for s in STOCKS:
    try:
        t = yf.Ticker(s)
        info = t.info
        curr = t.history(period="1d")['Close'].iloc[-1]
        fin = t.financials
        cf = t.cashflow
        
        # 이자보상배수 및 FCF Yield (백업 로직 포함)
        int_coverage = "N/A"
        fcf_yield_val = "N/A"
        try:
            ebit_idx = [i for i in fin.index if 'EBIT' in i.upper() and 'MARGIN' not in i.upper()][0]
            int_idx = [i for i in fin.index if 'INTEREST EXPENSE' in i.upper()][0]
            int_coverage = f"{fin.loc[ebit_idx].iloc[0] / abs(fin.loc[int_idx].iloc[0]):.1f}"
        except:
            ebitda = info.get('ebitda')
            if ebitda and info.get('totalDebt'):
                int_coverage = f"{ebitda / (info.get('totalDebt') * 0.05):.1f}*"

        try:
            fcf_idx = [i for i in cf.index if 'FREE CASH FLOW' in i.upper()][0]
            fcf_yield_val = f"{(cf.loc[fcf_idx].iloc[0] / info.get('marketCap')) * 100:.1f}"
        except:
            if info.get('freeCashflow') and info.get('marketCap'):
                fcf_yield_val = f"{(info.get('freeCashflow') / info.get('marketCap')) * 100:.1f}*"

        # 주요 지표 정리
        ev_ebitda = info.get('enterpriseToEbitda', 'N/A')
        upside = get_pct(info.get('targetMeanPrice', curr), curr)
        div = info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0
        if div > 50: div /= 100

        report += f"<b>📊 {s}</b> (S&P Rating: <b>{CREDIT_RATINGS.get(s)}</b>)\n"
        report += f"<b>  [PRICE]</b> ${curr:.2f} (목표가대비 {upside:+.1f}%)\n"
        report += f"<b>  [VALUE]</b> EV/EBITDA: {ev_ebitda}배 | ROE: {info.get('returnOnEquity',0)*100:.1f}%\n"
        report += f"<b>  [CASH ]</b> 배당률: {div:.2f}% | FCF Yield: {fcf_yield_val}%\n"
        report += f"<b>  [RISK ]</b> 이자보상: {int_coverage}배 | 부채/EBITDA: {info.get('debtToEquity', 0)/100:.1f}\n"
        report += "-"*40 + "\n"
        
    except Exception:
        report += f"⚠️ {s} 데이터 분석 생략\n"

send_report(report)
