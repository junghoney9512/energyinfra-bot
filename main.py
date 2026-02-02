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

# 1. 설정
STOCKS = ["KMI", "WMB", "LNG"]
MACRO_MAP = {"NG=F": "천연", "^TNX": "미10", "DX-Y.NYB": "달러", "^GSPC": "S&P", "CL=F": "WTI"}

report = f"🏛️ <b>에너지 인프라 통합 리서치 터미널 (Final Mastery)</b>\n"
report += f"기준: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
report += "="*40 + "\n"

# 2. 매크로 데이터 연산
macro_rets = {}
macro_info = "<b>🌐 [MACRO DASHBOARD]</b>\n"
for sym, name in MACRO_MAP.items():
    t = yf.Ticker(sym)
    h = t.history(period="6mo")
    macro_rets[sym] = h['Close'].pct_change().dropna()
    c, p = h['Close'].iloc[-1], h['Close'].iloc[-2]
    w, m = h['Close'].iloc[-6], h['Close'].iloc[-22]
    macro_info += f"📍 {name:3}: {c:7.2f} | 1D:{get_pct(c,p):+6.2f}% | 1W:{get_pct(c,w):+6.2f}%\n"

report += macro_info + "-"*40 + "\n"

# 3. 종목 분석
report += "<b>📈 [EQUITY RESEARCH: 펀더멘탈/상관성/베타]</b>\n"
for s in STOCKS:
    try:
        t = yf.Ticker(s)
        df = t.history(period="6mo")
        info = t.info
        c = df['Close'].iloc[-1]
        ret = df['Close'].pct_change().dropna()
        
        # 지표 계산
        rsi = (df['Close'].diff().gt(0).rolling(14).sum().iloc[-1] / 14) * 100
        rsi_tag = "⚠️ 과매수" if rsi > 70 else "❄️ 과매도" if rsi < 30 else "HOLD"
        upside = get_pct(info.get('targetMeanPrice', c), c)
        opinion = "STRONG_BUY" if upside > 20 else "BUY" if upside > 5 else "HOLD"
        
        report += f"<b>📊 {s}</b> | 시총: ${info.get('marketCap',0)/1e9:.2f}B | 현재가: ${c:.2f}\n"
        report += f"  ├─ [밸류/목표] EV/EBITDA: {info.get('enterpriseToEbitda','N/A')}배 | Upside: {upside:+.2f}% | 의견: {opinion}\n"
        report += f"  ├─ [펀더멘탈] 부채/EBITDA: {info.get('debtToEquity',0)/100:.2f}배 | ROE: {info.get('returnOnEquity',0)*100:.1f}%\n"
        report += f"  ├─ [기술/배당] RSI: {rsi:.1f} ({rsi_tag}) | 배당률: {info.get('dividendYield',0)*100:.2f}%\n"
        
        # 상관관계 & 베타 연산
        corr_str, beta_str = "  ├─ [상관관계] ", "  ├─ [민감도(β)] "
        for m_sym, m_name in MACRO_MAP.items():
            m_ret = macro_rets[m_sym]
            corr = ret.corr(m_ret)
            beta = ret.cov(m_ret) / m_ret.var()
            corr_str += f"{m_name}:{corr:+.2f} "
            beta_str += f"{m_name}:{beta:+.2f} "
        
        report += corr_str + "\n" + beta_str + "\n"
        
        # 뉴스
        news = t.news[0].get('title', 'N/A') if t.news else "N/A"
        report += f"  └─ [최신뉴스] {news[:50]}...\n"
        report += "-"*40 + "\n"
        
    except Exception as e:
        report += f"⚠️ {s} 데이터 연산 오류\n"

send_report(report)
