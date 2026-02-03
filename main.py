import yfinance as yf
import pandas as pd
import requests
import os
from datetime import datetime

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send_report(text):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        raise RuntimeError("Missing TELEGRAM_TOKEN or CHAT_ID env var.")
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    r = requests.post(url, data=payload, timeout=10)
    r.raise_for_status()

def pct(curr, prev):
    if prev is None or prev == 0:
        return None
    return (curr - prev) / prev * 100

def safe_get_series(df, candidates):
    """df.index에서 후보 라벨을 순서대로 찾아 첫 매칭 series 반환"""
    if df is None or df.empty:
        return None
    idx_upper = {str(i).upper(): i for i in df.index}
    for key in candidates:
        for u, orig in idx_upper.items():
            if key in u:
                return df.loc[orig]
    return None

def ttm_sum(series, n=4):
    if series is None:
        return None
    # yfinance는 컬럼이 날짜이고 값이 들어있음. 최신이 첫 컬럼일 때도 있고 반대일 때도 있어 정렬.
    s = series.copy()
    s.index = pd.to_datetime(s.index)
    s = s.sort_index(ascending=False)  # 최신 먼저
    return float(s.iloc[:n].sum())

STOCKS = ["KMI", "WMB", "LNG"]
CREDIT_RATINGS = {"KMI": "BBB", "WMB": "BBB", "LNG": "BBB"}
MACRO_MAP = {"NG=F": "천연가스", "^TNX": "10년금리", "DX-Y.NYB": "달러지수", "^GSPC": "S&P500", "CL=F": "WTI원유"}

report = f"<b>🏛️ 에너지 인프라 리서치 터미널</b>\n"
report += f"기준: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
report += "="*40 + "\n"

# MACRO
report += "<b>🌐 [MACRO TREND]</b>\n"
for sym, name in MACRO_MAP.items():
    try:
        h = yf.Ticker(sym).history(period="5d")["Close"].dropna()
        c, p = float(h.iloc[-1]), float(h.iloc[-2])
        if sym == "^TNX":
            # TNX는 대략 '수익률(%)' 수치. bp 변화가 해석에 더 적합
            bp = (c - p) * 100
            report += f"📍 {name:4}: {c:7.2f} ({bp:+6.1f}bp)\n"
        else:
            chg = pct(c, p)
            report += f"📍 {name:4}: {c:7.2f} ({chg:+6.2f}%)\n"
    except:
        continue
report += "-"*40 + "\n"

# STOCKS
for s in STOCKS:
    try:
        t = yf.Ticker(s)
        info = t.info or {}

        price_hist = t.history(period="2d")["Close"].dropna()
        curr = float(price_hist.iloc[-1])

        # 분기 재무제표로 TTM 계산 (정확도 목적)
        fin_q = t.quarterly_financials
        cf_q = t.quarterly_cashflow

        # EBIT 후보: EBIT 없으면 Operating Income로 대체
        ebit_series = safe_get_series(fin_q, ["EBIT", "OPERATING INCOME"])
        int_series  = safe_get_series(fin_q, ["INTEREST EXPENSE", "INTEREST EXPENSE AND DEBT"])

        ebit_ttm = ttm_sum(ebit_series, 4)
        int_ttm  = ttm_sum(int_series, 4)

        int_coverage = "N/A"
        if ebit_ttm is not None and int_ttm not in (None, 0):
            int_coverage = f"{(ebit_ttm / abs(int_ttm)):.1f}"

        # FCF TTM = CFO - Capex (분기 4개 합)
        cfo_series   = safe_get_series(cf_q, ["TOTAL CASH FROM OPERATING ACTIVITIES", "OPERATING CASH FLOW"])
        capex_series = safe_get_series(cf_q, ["CAPITAL EXPENDITURES"])

        cfo_ttm   = ttm_sum(cfo_series, 4)
        capex_ttm = ttm_sum(capex_series, 4)
        fcf_ttm = None
        if cfo_ttm is not None and capex_ttm is not None:
            fcf_ttm = cfo_ttm - capex_ttm  # capex는 보통 음수라서 실제로는 더하기처럼 작동할 수 있음

        mktcap = info.get("marketCap")
        fcf_yield = "N/A"
        if fcf_ttm is not None and mktcap:
            fcf_yield = f"{(fcf_ttm / mktcap) * 100:.1f}"

        # EV/EBITDA (info는 stale 가능. 없으면 N/A)
        ev_ebitda = info.get("enterpriseToEbitda", "N/A")

        # dividend yield: 0~1 범위면 %로 변환
        dy = info.get("dividendYield")
        div = 0.0
        if isinstance(dy, (int, float)):
            div = dy * 100 if dy <= 1 else dy

        # Debt/EBITDA (가능하면 totalDebt / EBITDA)
        total_debt = info.get("totalDebt")
        ebitda = info.get("ebitda")
        debt_ebitda = "N/A"
        if total_debt and ebitda:
            debt_ebitda = f"{(total_debt / ebitda):.1f}"

        target = info.get("targetMeanPrice")
        upside = pct(target, curr) if target else None
        upside_str = f"{upside:+.1f}%" if upside is not None else "N/A"

        roe = info.get("returnOnEquity")
        roe_str = f"{roe*100:.1f}%" if isinstance(roe, (int,float)) else "N/A"

        report += f"<b>📊 {s}</b> (S&P Rating: <b>{CREDIT_RATINGS.get(s,'N/A')}</b>)\n"
        report += f"<b>  [PRICE]</b> ${curr:.2f} (목표가대비 {upside_str})\n"
        report += f"<b>  [VALUE]</b> EV/EBITDA: {ev_ebitda}배 | ROE: {roe_str}\n"
        report += f"<b>  [CASH ]</b> 배당률: {div:.2f}% | FCF Yield(TTM): {fcf_yield}%\n"
        report += f"<b>  [RISK ]</b> 이자보상(TTM): {int_coverage}배 | Debt/EBITDA: {debt_ebitda}\n"
        report += "-"*40 + "\n"

    except Exception:
        report += f"⚠️ {s} 데이터 분석 생략\n"
        report += "-"*40 + "\n"

send_report(report)
