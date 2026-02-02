import yfinance as yf
import pandas as pd
import numpy as np
import requests
import os
from datetime import datetime

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

def get_safe(dict_obj, key, default=0):
    val = dict_obj.get(key)
    return val if val is not None else default

def send_report(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    for i in range(0, len(text), 4000):
        payload = {"chat_id": CHAT_ID, "text": text[i:i+4000], "parse_mode": "HTML"}
        requests.post(url, data=payload)

STOCKS = ["KMI", "WMB", "LNG"]
MACRO = {"NG=F": "천연가스", "^TNX": "10년금리", "DX-Y.NYB": "달러인덱스", "^GSPC": "S&P500", "CL=F": "WTI원유"}

report = f"<b>🏛 [에너지 전략 대시보드 - FINAL]</b>\n"
report += f"기준: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"

# 1. 매크로 데이터 수집
macro_hist = {}
report += "<b>🌐 매크로 대시보드</b>\n"
for sym, name in MACRO.items():
    try:
        t = yf.Ticker(sym)
        h = t.history(period="6mo")
        macro_hist[sym] = h['Close']
        curr, prev = h['Close'].iloc[-1], h['Close'].iloc[-2]
        chg = ((curr - prev) / prev) * 100
        report += f"• {name}: {curr:.2f} ({chg:+.2f}%)\n"
    except: report += f"• {name}: 데이터 지연\n"

# 2. 종목별 심층 분석
for s in STOCKS:
    try:
        t = yf.Ticker(s)
        df = t.history(period="6mo")
        # 재무 데이터 호출 (에러 방지를 위해 get 사용)
        info = t.info if t.info else {}
        
        curr = df['Close'].iloc[-1]
        d1 = ((curr - df['Close'].iloc[-2]) / df['Close'].iloc[-2]) * 100
        w1 = ((curr - df['Close'].iloc[-6]) / df['Close'].iloc[-6]) * 100
        m1 = ((curr - df['Close'].iloc[-22]) / df['Close'].iloc[-22]) * 100
        
        # 지표 연산
        target = get_safe(info, 'targetMeanPrice', curr)
        rsi_val = (df['Close'].diff().gt(0).rolling(14).sum().iloc[-1] / 14) * 100
        
        # 상관관계/베타
        returns = df['Close'].pct_change().dropna()
        spy_ret = macro_hist.get("^GSPC", pd.Series()).pct_change().dropna()
        ng_ret = macro_hist.get("NG=F", pd.Series()).pct_change().dropna()
        
        beta = returns.cov(spy_ret) / spy_ret.var() if not spy_ret.empty else 0
        corr_ng = returns.corr(ng_ret) if not ng_ret.empty else 0

        # 리포트 구성
        report += f"\n<b>📊 {s} (${get_safe(info, 'marketCap', 0)/1e9:.1f}B)</b>\n"
        report += f"<b>주가:</b> ${curr:.2f} (1D:{d1:+.1f}% | 1W:{w1:+.1f}% | 1M:{m1:+.1f}%)\n"
        report += f"<b>밸류:</b> EV/EBITDA {get_safe(info, 'enterpriseToEbitda', 0):.1;f} | 목표대비 {((target-curr)/curr*100):+.1f}%\n"
        report += f"<b>펀더:</b> 부채비율 {get_safe(info, 'debtToEquity', 0)/100:.1f} | ROE {get_safe(info, 'returnOnEquity', 0)*100:.1f}%\n"
        report += f"<b>지표:</b> RSI {rsi_val:.1f} | 배당률 {get_safe(info, 'dividendYield', 0)*100:.1f}%\n"
        report += f"<b>민감:</b> Beta {beta:.2;f} | 가스상관 {corr_ng:.2f}\n"
        
        # 뉴스 안전하게 가져오기
        try:
            news = t.news[:2]
            if news:
                report += "<b>📰 뉴스:</b>\n"
                for n in news: report += f" - {n.get('title', '제목 없음')[:35]}..\n"
        except: pass
        
    except Exception:
        report += f"\n⚠️ {s}: 기본 시세 데이터 오류\n"

send_report(report)
