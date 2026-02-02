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
MACRO_MAP = {"NG=F": "천연가스", "^TNX": "10년금리", "DX-Y.NYB": "달러지수", "^GSPC": "S&P500", "CL=F": "WTI원유"}

report = f"<b>🏛️ 에너지 인프라 리서치 터미널 (Analyst Edition)</b>\n"
report += f"기준: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
report += "="*40 + "\n"

# 1. 매크로 대시보드 (주요 원자재 및 금리 추이)
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

# 2. 개별 종목 심층 분석 (애널리스트 핵심 지표)
report += "<b>📈 [EQUITY FUNDAMENTALS]</b>\n"
for s in STOCKS:
    try:
        t = yf.Ticker(s)
        df = t.history(period="6mo")['Close']
        info = t.info if t.info else {}
        curr = df.iloc[-1]
        ret = df.pct_change().fillna(0)
        
        # 밸류에이션 및 펀더멘탈
        ev_ebitda = info.get('enterpriseToEbitda', 'N/A')
        target = info.get('targetMeanPrice', curr)
        upside = get_pct(target, curr)
        debt_to_ebitda = info.get('debtToEquity', 0) / 100 # 대용치
        roe = info.get('returnOnEquity', 0) * 100
        
        # 기술 지표 및 배당
        div = info.get('dividendYield', 0)
        if div > 1: div /= 100
        
        # 시장 민감도 (S&P500 대비 베타만 남김)
        beta = ret.cov(spy_ret) / (spy_ret.var() + 1e-9) if not spy_ret.empty else 0
        
        # 리포트 조립 (가독성 최적화)
        report += f"<b>📊 {s}</b> (시총: ${info.get('marketCap',0)/1e9:.1f}B)\n"
        report += f"<b>  [PRICE]</b> ${curr:.2f} (목표가대비 {upside:+.1f}%)\n"
        report += f"<b>  [VALUE]</b> EV/EBITDA: {ev_ebitda}배 | ROE: {roe:.1f}%\n"
        report += f"<b>  [CASH ]</b> 배당률: {div*100:.2f}% | 부채비율: {debt_to_ebitda:.1f}\n"
        report += f"<b>  [RISK ]</b> 시장베타(β): {beta:.2f} (Low Vol)\n"
        report += "-"*40 + "\n"
        
    except Exception:
        report += f"⚠️ {s} 데이터 분석 중 예외 발생\n"

send_report(report)
