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

# 종목 및 매크로 설정
STOCKS = ["KMI", "WMB", "LNG"]
MACRO_MAP = {"NG=F": "천연", "^TNX": "미10년물", "DX-Y.NYB": "달러", "^GSPC": "S&P", "CL=F": "WTI"}

report = f"<b>🏛️ 에너지 인프라 통합 리서치 터미널 (Final Mastery)</b>\n"
report += f"기준: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
report += "="*40 + "\n"

# 1. 매크로 데이터 수집 (금리 연산 정밀 보정)
macro_rets = {}
macro_info = "<b>🌐 [MACRO DASHBOARD]</b>\n"
for sym, name in MACRO_MAP.items():
    try:
        t = yf.Ticker(sym)
        h = t.history(period="6mo")['Close']
        
        # 금리(^TNX)는 절대값 변화량이 아닌 수익률 자체의 변화로 연산
        macro_rets[sym] = h.pct_change().replace([np.inf, -np.inf], np.nan).fillna(0)
            
        c, p, w = h.iloc[-1], h.iloc[-2], h.iloc[-6]
        macro_info += f"📍 {name}: {c:7.2f} | 1D:{get_pct(c,p):+6.2f}% | 1W:{get_pct(c,w):+6.2f}%\n"
    except:
        macro_info += f"📍 {name}: 데이터 지연\n"

report += macro_info + "-"*40 + "\n"

# 2. 종목 심층 분석
report += "<b>📈 [EQUITY RESEARCH: 분석 지표]</b>\n"
for s in STOCKS:
    try:
        t = yf.Ticker(s)
        df = t.history(period="6mo")['Close']
        info = t.info if t.info else {}
        
        c = df.iloc[-1]
        ret = df.pct_change().fillna(0)
        
        # 밸류/의견/RSI
        target = info.get('targetMeanPrice', c)
        upside = get_pct(target, c)
        opinion = "STRONG_BUY" if upside > 20 else "BUY" if upside > 5 else "HOLD"
        
        delta = df.diff()
        gain = delta.clip(lower=0).rolling(window=14).mean()
        loss = (-delta.clip(upper=0)).rolling(window=14).mean()
        rsi = 100 - (100 / (1 + (gain.iloc[-1] / (loss.iloc[-1] + 1e-9))))
        
        # 배당률 보정
        div = info.get('dividendYield', 0)
        if div > 1: div /= 100
        
        report += f"<b>📊 {s}</b> | 시총: ${info.get('marketCap',0)/1e9:.1f}B | 현재가: ${c:.2f}\n"
        report += f"  ├─ [밸류/목표] EV/EBITDA: {info.get('enterpriseToEbitda','N/A')}배 | Upside: {upside:+.1f}% | 의견: {opinion}\n"
        report += f"  ├─ [펀더멘탈] 부채/EBITDA: {info.get('debtToEquity',0)/100:.1f}배 | ROE: {info.get('returnOnEquity',0)*100:.1f}%\n"
        report += f"  ├─ [기술/배당] RSI: {rsi:.1f} | 배당률: {div*100:.2f}%\n"
        
        # 상관관계 & 베타 (금리 nan 문제 해결을 위해 인덱스 동기화)
        corr_line, beta_line = "  ├─ [상관관계] ", "  ├─ [민감도(β)] "
        for m_sym, m_name in MACRO_MAP.items():
            m_ret = macro_rets.get(m_sym, pd.Series(0, index=ret.index))
            
            # 두 데이터의 날짜 인덱스를 맞춰서 NaN 발생 억제
            common_idx = ret.index.intersection(m_ret.index)
            s_ret_c = ret.loc[common_idx]
            m_ret_c = m_ret.loc[common_idx]
            
            corr = s_ret_c.corr(m_ret_c)
            beta = s_ret_c.cov(m_ret_c) / (m_ret_c.var() + 1e-9)
            
            # 최종 수치 클리닝
            corr_val = 0.00 if np.isnan(corr) else corr
            beta_val = 0.00 if np.isnan(beta) else beta
            
            corr_line += f"{m_name}:{corr_val:+.2f} "
            beta_line += f"{m_name}:{beta_val:+.2f} "
        
        report += corr_line.strip() + "\n" + beta_line.strip() + "\n"
        report += "-"*40 + "\n"
        
    except Exception:
        report += f"⚠️ {s} 분석 중 예외 발생\n"

send_report(report)
