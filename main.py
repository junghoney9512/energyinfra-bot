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

# 1. 매크로 섹션 (변동률 포함)
report += "<b>🌐 [MACRO TREND]</b>\n"
spy_ret = pd.Series()
for sym, name in MACRO_MAP.items():
    try:
        t_macro = yf.Ticker(sym)
        h = t_macro.history(period="5d")['Close']
        c, p = h.iloc[-1], h.iloc[-2]
        if sym == "^GSPC": spy_ret = h.pct_change().fillna(0)
        report += f"📍 {name:4}: {c:7.2f} ({get_pct(c,p):+6.2f}%)\n"
    except: continue
report += "-"*40 + "\n"

# 2. 개별 종목 정밀 분석
for s in STOCKS:
    try:
        t = yf.Ticker(s)
        info = t.info
        curr = t.history(period="1d")['Close'].iloc[-1]
        fin = t.financials
        cf = t.cashflow
        
        # [핵심] 이자보상배수 정밀 계산 및 백업 로직
        int_coverage = "N/A"
        try:
            # 1순위: 재무제표 항목 검색 및 직접 연산
            ebit_idx = [i for i in fin.index if 'EBIT' in i.upper() and 'MARGIN' not in i.upper()][0]
            int_idx = [i for i in fin.index if 'INTEREST EXPENSE' in i.upper()][0]
            ebit_val = fin.loc[ebit_idx].iloc[0]
            int_val = abs(fin.loc[int_idx].iloc[0])
            if int_val != 0:
                int_coverage = f"{ebit_val / int_val:.1f}"
        except:
            # 2순위: 재무제표 실패 시 info 데이터(EBITDA) 기반 추정
            ebitda = info.get('ebitda')
            # info에서 interestExpense 혹은 관련 항목 추정
            int_exp_info = info.get('interestExpense')
            if ebitda and int_exp_info:
                int_coverage = f"{ebitda / abs(int_exp_info):.1f}*" 
            elif ebitda and info.get('totalDebt'):
                # 부채와 평균 이자율(약 5%)로 보수적 추정
                est_int = info.get('totalDebt') * 0.05
                int_coverage = f"{ebitda / est_int:.1f}*"

        # FCF Yield 정밀 계산
        fcf_yield_val = "N/A"
        try:
            fcf_idx = [i for i in cf.index if 'FREE CASH FLOW' in i.upper()][0]
            fcf_val = cf.loc[fcf_idx].iloc[0]
            mkt_cap = info.get('marketCap')
            if mkt_cap:
                fcf_yield_val = f"{(fcf_val / mkt_cap) * 100:.1f}"
        except:
            # 백업: info의 잉여현금흐름 사용
            fcf_info = info.get('freeCashflow')
            if fcf_info and info.get('marketCap'):
                fcf_yield_val = f"{(fcf_info / info.get('marketCap')) * 100:.1f}*"

        # 나머지 핵심 지표 (ROE, 배당, 밸류에이션)
        ev_ebitda = info.get('enterpriseToEbitda', 'N/A')
        upside = get_pct(info.get('targetMeanPrice', curr), curr)
        roe = info.get('returnOnEquity', 0) * 100
        div = info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0
        if div > 50: div /= 100 # 야후 데이터 단위 오차 보정
        
        # 시장 베타 (S&P500 대비)
        h_stock = t.history(period="6mo")['Close'].pct_change().fillna(0)
        beta = h_stock.cov(spy_ret) / (spy_ret.var() + 1e-9) if not spy_ret.empty else 0

        report += f"<b>📊 {s}</b> (S&P Rating: <b>{CREDIT_RATINGS.get(s)}</b>)\n"
        report += f"<b>  [PRICE]</b> ${curr:.2f} (목표가대비 {upside:+.1f}%)\n"
        report += f"<b>  [VALUE]</b> EV/EBITDA: {ev_ebitda}배 | ROE: {roe:.1f}%\n"
        report += f"<b>  [CASH ]</b> 배당률: {div:.2f}% | FCF Yield: {fcf_yield_val}%\n"
        report += f"<b>  [RISK ]</b> 이자보상: {int_coverage}배 | 부채/EBITDA: {info.get('debtToEquity', 0)/100:.1f}\n"
        report += f"<b>  [SENS ]</b> 시장베타(β): {beta:.2f}\n"
        report += "-"*40 + "\n"
        
    except Exception as e:
        report += f"⚠️ {s} 리서치 데이터 연산 중 예외 발생\n"

send_report(report)
