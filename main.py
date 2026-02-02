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
MACRO_MAP = {"NG=F": "천연", "^TNX": "미10", "DX-Y.NYB": "달러", "^GSPC": "S&P", "CL=F": "WTI"}

report = f"<b>🏛️ 에너지 인프라 통합 리서치 터미널 (Final Mastery)</b>\n"
report += f"기준: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
report += "="*40 + "\n"

# 1. 매크로 데이터 수집 및 클리닝
macro_rets = {}
macro_info = "<b>🌐 [MACRO DASHBOARD]</b>\n"
for sym, name in MACRO_MAP.items():
    t = yf.Ticker(sym)
    h = t.history(period="6mo")
    # 결측치 제거 및 수익률 계산
    macro_rets[sym] = h['Close'].pct_change().fillna(0)
    c, p = h['Close'].iloc[-1], h['Close'].iloc[-2]
    w = h['Close'].iloc[-6]
    macro_info += f"📍 {name:3}: {c:7.2f} | 1D:{get_pct(c,p):+6.2f}% | 1W:{get_pct(c,w):+6.2f}%\n"

report += macro_info + "-"*40 + "\n"

# 2. 종목 심층 분석
report += "<b>📈 [EQUITY RESEARCH: 분석 지표]</b>\n"
for s in STOCKS:
    try:
        t = yf.Ticker(s)
        df = t.history(period="6mo")
        info = t.info if t.info else {}
        c = df['Close'].iloc[-1]
        ret = df['Close'].pct_change().fillna(0)
        
        # RSI 계산
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rsi = 100 - (100 / (1 + (gain.iloc[-1] / (loss.iloc[-1] + 1e-9))))
        
        # 밸류/의견
        target = info.get('targetMeanPrice', c)
        upside = get_pct(target, c)
        opinion = "STRONG_BUY" if upside > 20 else "BUY" if upside > 5 else "HOLD"
        
        # 배당률 보정 (핵심!)
        div = info.get('dividendYield', 0)
        if div > 1: div = div / 100 # 3.84 -> 0.0384 보정
        
        report += f"<b>📊 {s}</b> | 시총: ${info.get('marketCap',0)/1e9:.1f}B | 현재가: ${c:.2f}\n"
        report += f"  ├─ [밸류/목표] EV/EBITDA: {info.get('enterpriseToEbitda','N/A')}배 | Upside: {upside:+.1f}% | 의견: {opinion}\n"
        report += f"  ├─ [펀더멘탈] 부채/EBITDA: {info.get('debtToEquity',0)/100:.1f}배 | ROE: {info.get('returnOnEquity',0)*100:.1f}%\n"
        report += f"  ├─ [기술/배당] RSI: {rsi:.1f} | 배당률: {div*100:.2f}%\n"
        
        # 상관관계 & 베타 (NaN 방지)
        corr_str, beta_str = "  ├─ [상관관계] ", "  ├─ [민감도(β)] "
        for m_sym, m_name in MACRO_MAP.items():
            m_ret = macro_rets.get(m_sym, pd.Series())
            # 공통 날짜 기준으로 정렬하여 연산
            combined = pd.concat([ret, m_ret], axis=1).dropna()
            corr = combined.iloc[:,0].corr(combined.iloc[:,1])
            beta = combined.iloc[:,0].cov(combined.iloc[:,1]) / (combined.iloc[:,1].var() + 1e-9)
            
            corr_str += f"{m_name}:{corr:+.2f} "
            beta_str += f"{m_name}:{beta:+.2f} "
        
        report += corr_str.strip() + "\n" + beta_str.strip() + "\n"
        
        # 뉴스 섹션 강화
        news_data = t.news
        news_title = news_data[0].get('title', 'N/A') if news_data else "N/A"
        report += f"  └─ [최신뉴스] {news_title[:45]}...\n"
        report += "-"*40 + "\n"
        
    except Exception as e:
        report += f"⚠️ {s} 분석 중 예외 발생\n"

send_report(report)
