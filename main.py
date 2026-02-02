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
    # 고정폭 느낌을 주기 위해 HTML의 <code> 태그를 활용합니다.
    payload = {"chat_id": CHAT_ID, "text": f"<code>{text}</code>", "parse_mode": "HTML"}
    requests.post(url, data=payload)

def get_pct(curr, prev):
    if not prev or prev == 0: return 0
    return ((curr - prev) / prev) * 100

STOCKS = ["KMI", "WMB", "LNG"]
# 텍스트 밀림 방지를 위해 매크로 이름을 2글자로 통일
MACRO_MAP = {"NG=F": "가스", "^TNX": "금리", "DX-Y.NYB": "달러", "^GSPC": "S&P", "CL=F": "원유"}

now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
report = f"🏛️ ENERGY INFRA TERMINAL\n"
report += f"DATE: {now_str}\n"
report += "="*30 + "\n"

# 1. 매크로 데이터 (수익률 연산 보정)
macro_rets = {}
report += "[🌐 MACRO DASHBOARD]\n"
for sym, name in MACRO_MAP.items():
    try:
        t = yf.Ticker(sym)
        h = t.history(period="6mo")['Close']
        if sym == "^TNX":
            macro_rets[sym] = h.diff().fillna(0) # 금리는 단순 변화량
        else:
            macro_rets[sym] = h.pct_change().fillna(0)
            
        c, p = h.iloc[-1], h.iloc[-2]
        report += f"{name:4}: {c:7.2f} ({get_pct(c,p):+6.2f}%)\n"
    except: report += f"{name:4}: Data Error\n"

report += "-"*30 + "\n"

# 2. 종목 분석
report += "[📈 EQUITY RESEARCH]\n"
for s in STOCKS:
    try:
        t = yf.Ticker(s)
        df = t.history(period="6mo")['Close']
        info = t.info if t.info else {}
        
        c = df.iloc[-1]
        ret = df.pct_change().fillna(0)
        
        # 기본 지표
        upside = get_pct(info.get('targetMeanPrice', c), c)
        delta = df.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rsi = 100 - (100 / (1 + (gain.iloc[-1] / (loss.iloc[-1] + 1e-9))))
        
        div = info.get('dividendYield', 0)
        if div > 1: div /= 100 # 배당 오차 수정

        report += f"● {s:3} | Price: ${c:.2f}\n"
        report += f"├ Value: EV {info.get('enterpriseToEbitda','N/A')}배 | UP {upside:+.1f}%\n"
        report += f"├ Funda: Debt {info.get('debtToEquity',0)/100:.1f} | ROE {info.get('returnOnEquity',0)*100:.1f}%\n"
        report += f"├ Tech : RSI {rsi:.1f} | Div {div*100:.1f}%\n"
        
        # 상관관계 & 베타 (한 줄 정렬을 위해 짧게 표기)
        corr_line = "├ Corr : "
        beta_line = "└ Beta : "
        for m_sym, m_name in MACRO_MAP.items():
            m_ret = macro_rets.get(m_sym, pd.Series(0, index=ret.index))
            combined = pd.concat([ret, m_ret], axis=1).dropna()
            
            corr = combined.iloc[:,0].corr(combined.iloc[:,1])
            beta = combined.iloc[:,0].cov(combined.iloc[:,1]) / (combined.iloc[:,1].var() + 1e-9)
            
            # NaN은 0으로 강제 변환
            corr = 0 if np.isnan(corr) else corr
            beta = 0 if np.isnan(beta) else beta
            
            # 가독성을 위해 기호 제외하고 수치만 간결하게
            corr_line += f"{corr:+.1f} "
            beta_line += f"{beta:+.1f} "
        
        report += corr_line.strip() + "\n"
        report += beta_line.strip() + "\n"
        report += "."*30 + "\n"
        
    except Exception:
        report += f"⚠️ {s} Analysis Error\n"

send_report(report)
