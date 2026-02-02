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
    if prev == 0 or prev is None: return 0
    return ((curr - prev) / prev) * 100

STOCKS = ["KMI", "WMB", "LNG"]
MACRO_SYMS = {"NG=F": "천연가스", "^TNX": "10년금리", "DX-Y.NYB": "달러인덱스", "^GSPC": "S&P500", "CL=F": "WTI원유"}

# 1. 매크로 데이터 수집
macro_info = ""
macro_returns = {}
for sym, name in MACRO_SYMS.items():
    try:
        t = yf.Ticker(sym)
        h = t.history(period="6mo")
        curr, prev = h['Close'].iloc[-1], h['Close'].iloc[-2]
        macro_returns[sym] = h['Close'].pct_change().dropna()
        macro_info += f"• {name}: {curr:.2f} ({get_pct(curr, prev):+.2f}%)\n"
    except: macro_info += f"• {name}: 데이터 지연\n"

report = f"<b>🏛 [에너지 전략 대시보드 - FINAL]</b>\n{datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
report += f"<b>🌐 매크로 상황</b>\n{macro_info}"

# 2. 종목 분석
for s in STOCKS:
    try:
        t = yf.Ticker(s)
        df = t.history(period="6mo")
        info = t.info # 재무 데이터 호출
        
        curr = df['Close'].iloc[-1]
        d1 = get_pct(curr, df['Close'].iloc[-2])
        w1 = get_pct(curr, df['Close'].iloc[-6])
        m1 = get_pct(curr, df['Close'].iloc[-22])
        
        # 재무 지표 안전하게 추출
        ev_ebitda = info.get('enterpriseToEbitda', 'N/A')
        roe = info.get('returnOnEquity', 0) * 100
        debt_ebitda = info.get('debtToEquity', 0) / 100
        div = info.get('dividendYield', 0) * 100
        target = info.get('targetMeanPrice', curr)
        
        # 기술 지표 계산
        returns = df['Close'].pct_change().dropna()
        rsi = (df['Close'].diff().gt(0).rolling(14).sum().iloc[-1] / 14) * 100
        
        # 상관관계/베타
        spy_ret = macro_returns.get("^GSPC", pd.Series())
        ng_ret = macro_returns.get("NG=F", pd.Series())
        beta = returns.cov(spy_ret) / spy_ret.var() if not spy_ret.empty else 0
        corr_ng = returns.corr(ng_ret) if not ng_ret.empty else 0

        report += f"\n<b>📊 {s} (${info.get('marketCap', 0)/1e9:.1f}B)</b>\n"
        report += f"<b>주가:</b> ${curr:.2f} (1D:{d1:+.1f}% | 1W:{w1:+.1f}% | 1M:{m1:+.1f}%)\n"
        report += f"<b>밸류:</b> EV/EBITDA {ev_ebitda} | 목표대비 {get_pct(target, curr):+.1f}%\n"
        report += f"<b>펀더:</b> 부채비율 {debt_ebitda:.1f} | ROE {roe:.1f}%\n"
        report += f"<b>지표:</b> RSI {rsi:.1f} | 배당률 {div:.1f}%\n"
        report += f"<b>민감:</b> Beta {beta:.2f} | 가스상관 {corr_ng:.2f}\n"
        
        # 뉴스
        news = t.news[:2]
        if news:
            report += "<b>📰 뉴스:</b>\n"
            for n in news: report += f" - {n.get('title')[:35]}..\n"
            
    except Exception as e:
        report += f"\n⚠️ {s}: 데이터 연산 오류\n"

send_report(report)
