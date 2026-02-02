import yfinance as yf
import pandas as pd
import numpy as np
import requests
import os
from datetime import datetime

# 설정값
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

def get_change(curr, prev):
    if prev == 0 or prev is None: return 0
    return ((curr - prev) / prev) * 100

def send_report(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    # 메시지 길이에 따른 분할 전송 (텔레그램 글자수 제한 대응)
    for i in range(0, len(text), 4000):
        payload = {"chat_id": CHAT_ID, "text": text[i:i+4000], "parse_mode": "HTML"}
        requests.post(url, data=payload)

# 1. 대상 설정
STOCKS = ["KMI", "WMB", "LNG"]
MACRO = {"NG=F": "천연가스", "^TNX": "10년금리", "DX-Y.NYB": "달러인덱스", "^GSPC": "S&P500", "CL=F": "WTI원유"}

report = f"<b>🏛 [에너지 전략 대시보드 - FINAL]</b>\n"
report += f"기준: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"

# 2. 매크로 대시보드 및 연산 데이터 준비
macro_hist = {}
report += "<b>🌐 매크로 대시보드</b>\n"
for sym, name in MACRO.items():
    try:
        t = yf.Ticker(sym)
        h = t.history(period="6mo")
        macro_hist[sym] = h['Close']
        curr = h['Close'].iloc[-1]
        prev = h['Close'].iloc[-2]
        chg = get_change(curr, prev)
        report += f"• {name}: {curr:.2f} ({chg:+.2f}%)\n"
    except: continue

# 3. 개별 종목 심층 분석
for s in STOCKS:
    try:
        t = yf.Ticker(s)
        # 넉넉하게 6개월치 데이터 (상관관계 및 변화율용)
        df = t.history(period="6mo")
        info = t.info
        
        curr = df['Close'].iloc[-1]
        # 변화율 (1D, 1W, 1M - 거래일 기준 1, 5, 21일)
        d1 = get_change(curr, df['Close'].iloc[-2])
        w1 = get_change(curr, df['Close'].iloc[-6])
        m1 = get_change(curr, df['Close'].iloc[-22])
        
        # 재무 지표 (부채/EBT는 DebtToEquity와 EBITDA를 조합하여 보수적 계산)
        ev_ebitda = info.get('enterpriseToEbitda', 0)
        target = info.get('targetMeanPrice', curr)
        roe = info.get('returnOnEquity', 0) * 100
        debt_to_ebitda = info.get('debtToEquity', 0) / 100 # 대용치
        div_yield = info.get('dividendYield', 0) * 100
        mkt_cap = info.get('marketCap', 0) / 1e9
        
        # 지표 연산 (RSI)
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs.iloc[-1]))
        
        # 상관관계 및 베타 (S&P500 대비)
        returns = df['Close'].pct_change().dropna()
        spy_ret = macro_hist["^GSPC"].pct_change().dropna()
        ng_ret = macro_hist["NG=F"].pct_change().dropna()
        
        corr_spy = returns.corr(spy_ret)
        corr_ng = returns.corr(ng_ret)
        beta = returns.cov(spy_ret) / spy_ret.var()
        
        # 뉴스 추출
        news = t.news[:2]
        news_text = ""
        for n in news:
            news_text += f" - {n['title'][:35]}...\n"

        # 리포트 조립
        report += f"\n<b>📊 {s} (시총: ${mkt_cap:.1f}B)</b>\n"
        report += f"<b>주가:</b> ${curr:.2f} (1D:{d1:+.1f}% | 1W:{w1:+.1f}% | 1M:{m1:+.1f}%)\n"
        report += f"<b>밸류:</b> EV/EBITDA {ev_ebitda:.1f} | 목표대비 {get_change(target, curr):+.1f}%\n"
        report += f"<b>펀더:</b> 부채비율 {debt_to_ebitda:.1f} | ROE {roe:.1f}%\n"
        report += f"<b>지표:</b> RSI {rsi:.1f} | 배당률 {div_yield:.1f}%\n"
        report += f"<b>민감:</b> Beta {beta:.2f} | 가스상관 {corr_ng:.2f} | S&P상관 {corr_spy:.2f}\n"
        report += f"<b>📰 최신 뉴스:</b>\n{news_text}"
        
    except Exception as e:
        report += f"\n⚠️ {s} 데이터 분석 중 오류\n"

# 4. 최종 전송
send_report(report)
