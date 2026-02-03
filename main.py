import os
from datetime import datetime

import pandas as pd
import requests
import yfinance as yf


# =========================
# ENV
# =========================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")


# =========================
# CONFIG
# =========================
STOCKS = ["KMI", "WMB", "LNG"]
CREDIT_RATINGS = {"KMI": "BBB", "WMB": "BBB", "LNG": "BBB"}

MACRO_MAP = {
    "NG=F": "천연가스",
    "^TNX": "10년금리",
    "DX-Y.NYB": "달러지수",
    "^GSPC": "S&P500",
    "CL=F": "WTI원유",
}


# =========================
# TELEGRAM
# =========================
def send_report(text: str) -> None:
    if not TELEGRAM_TOKEN or not CHAT_ID:
        raise RuntimeError("Missing TELEGRAM_TOKEN or CHAT_ID env var.")
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    r = requests.post(url, data=payload, timeout=15)
    r.raise_for_status()


# =========================
# HELPERS
# =========================
def pct(curr, prev):
    if prev is None or prev == 0:
        return None
    return (curr - prev) / prev * 100


def fmt_num(x, nd=1, suffix=""):
    if x is None:
        return "N/A"
    try:
        return f"{float(x):.{nd}f}{suffix}"
    except Exception:
        return "N/A"


def fmt_pct(x, nd=2):
    if x is None:
        return "N/A"
    try:
        return f"{float(x):.{nd}f}%"
    except Exception:
        return "N/A"


def cov_label(x: float) -> str:
    # optional visual indicator
    if x >= 6:
        return "🟢"
    if x >= 3:
        return "🟡"
    if x >= 1.5:
        return "🟠"
    return "🔴"


def _normalize_dt_index(series: pd.Series) -> pd.Series:
    s = series.copy()
    try:
        s.index = pd.to_datetime(s.index)
        s = s.sort_index(ascending=False)  # latest first
    except Exception:
        pass
    return s


def ttm_sum(series: pd.Series, n: int = 4):
    if series is None or len(series) == 0:
        return None
    s = _normalize_dt_index(series)
    return float(s.iloc[: min(n, len(s))].sum())


def pick_row(df: pd.DataFrame, must_contain_any, must_not_contain=None):
    """
    Return a row (pd.Series) from df where index contains ANY keyword in must_contain_any
    and doesn't contain any keyword in must_not_contain. Case-insensitive.
    """
    if df is None or df.empty:
        return None

    must_not_contain = must_not_contain or []
    idx = [str(i) for i in df.index]
    idx_upper = [i.upper() for i in idx]

    for key in must_contain_any:
        key_u = key.upper()
        for raw, up in zip(idx, idx_upper):
            if key_u in up and not any(bad.upper() in up for bad in must_not_contain):
                return df.loc[raw]
    return None


# =========================
# CREDIT METRICS
# =========================
def get_interest_coverage_ttm(t: yf.Ticker):
    """
    Interest Coverage (TTM) = EBIT(TTM) / |Interest Expense(TTM)|
    Uses quarterly_financials. No guessing; returns None if missing.
    """
    fin_q = t.quarterly_financials
    if fin_q is None or fin_q.empty:
        return None

    ebit = pick_row(fin_q, ["EBIT", "OPERATING INCOME"], must_not_contain=["MARGIN"])
    interest = pick_row(
        fin_q,
        ["INTEREST EXPENSE", "INTEREST AND DEBT EXPENSE", "INTEREST EXPENSE AND DEBT"],
    )

    ebit_ttm = ttm_sum(ebit, 4)
    int_ttm = ttm_sum(interest, 4)

    if ebit_ttm is None or int_ttm in (None, 0):
        return None
    return ebit_ttm / abs(int_ttm)


def get_dividend_coverage_ttm(t: yf.Ticker):
    """
    Dividend Coverage (TTM) = CFO(TTM) / |Dividends Paid(TTM)|
    Uses quarterly_cashflow. No guessing; returns None if missing.
    """
    cf_q = t.quarterly_cashflow
    if cf_q is None or cf_q.empty:
        return None

    cfo = pick_row(
        cf_q,
        ["TOTAL CASH FROM OPERATING ACTIVITIES", "OPERATING CASH FLOW", "CASH FLOW FROM OPERATING"],
    )
    div = pick_row(
        cf_q,
        ["CASH DIVIDENDS PAID", "DIVIDENDS PAID", "COMMON STOCK DIVIDENDS PAID"],
    )

    cfo_ttm = ttm_sum(cfo, 4)
    div_ttm = ttm_sum(div, 4)

    if cfo_ttm is None or div_ttm in (None, 0):
        return None
    return cfo_ttm / abs(div_ttm)


def get_dividend_yield_pct(info: dict):
    dy = info.get("dividendYield")
    if dy is None:
        return None
    if isinstance(dy, (int, float)):
        return dy * 100 if dy <= 1 else float(dy)
    return None


def get_net_debt_to_ebitda(info: dict):
    """
    Net Debt / EBITDA
    netDebt (if available) else totalDebt - totalCash
    EBITDA uses info['ebitda'] (often TTM). Returns None if missing.
    """
    ebitda = info.get("ebitda")
    if not ebitda or ebitda == 0:
        return None

    net_debt = info.get("netDebt")
    if net_debt is None:
        total_debt = info.get("totalDebt")
        cash = info.get("totalCash")
        if total_debt is None or cash is None:
            return None
        net_debt = total_debt - cash

    return net_debt / ebitda


# =========================
# REPORT
# =========================
def build_report() -> str:
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    report = "<b>🏛️ 에너지 인프라 Credit Dashboard</b>\n"
    report += f"기준: {now_str}\n"
    report += "=" * 40 + "\n"

    # 1) Macro
    report += "<b>🌐 [MACRO TREND]</b>\n"
    for sym, name in MACRO_MAP.items():
        try:
            h = yf.Ticker(sym).history(period="5d")["Close"].dropna()
            if len(h) < 2:
                continue
            c, p = float(h.iloc[-1]), float(h.iloc[-2])

            if sym == "^TNX":
                # TNX is a percent level; bp change is more interpretable
                bp = (c - p) * 100
                report += f"📍 {name:4}: {c:7.2f} ({bp:+6.1f}bp)\n"
            else:
                chg = pct(c, p)
                report += f"📍 {name:4}: {c:7.2f} ({chg:+6.2f}%)\n"
        except Exception:
            continue

    report += "-" * 40 + "\n"

    # 2) Tickers
    for s in STOCKS:
        try:
            t = yf.Ticker(s)
            info = t.info or {}

            px = t.history(period="2d")["Close"].dropna()
            if len(px) == 0:
                raise RuntimeError("No price data")
            curr = float(px.iloc[-1])

            # VALUE
            ev_ebitda = info.get("enterpriseToEbitda")
            ev_ebitda_str = fmt_num(ev_ebitda, nd=3) if isinstance(ev_ebitda, (int, float)) else "N/A"

            roe = info.get("returnOnEquity")
            roe_str = f"{roe * 100:.1f}%" if isinstance(roe, (int, float)) else "N/A"

            target = info.get("targetMeanPrice")
            upside = pct(float(target), curr) if target else None
            upside_str = f"{upside:+.1f}%" if upside is not None else "N/A"

            # CASH / RISK (Credit dashboard)
            div_yield = get_dividend_yield_pct(info)
            div_yield_str = fmt_pct(div_yield, nd=2)

            div_cov = get_dividend_coverage_ttm(t)
            div_cov_str = fmt_num(div_cov, nd=2)  # x

            ic = get_interest_coverage_ttm(t)
            if ic is None:
                ic_str = "N/A"
            else:
                ic_str = f"{fmt_num(ic, nd=1)}배 {cov_label(float(ic))}"

            nd_ebitda = get_net_debt_to_ebitda(info)
            nd_ebitda_str = fmt_num(nd_ebitda, nd=1)  # x

            report += f"<b>📊 {s}</b> (S&P Rating: <b>{CREDIT_RATINGS.get(s, 'N/A')}</b>)\n"
            report += f"<b>  [PRICE]</b> ${curr:.2f} (목표가대비 {upside_str})\n"
            report += f"<b>  [VALUE]</b> EV/EBITDA: {ev_ebitda_str}배 | ROE: {roe_str}\n"
            report += f"<b>  [CASH ]</b> 배당률: {div_yield_str} | Dividend Coverage(TTM): {div_cov_str}x\n"
            report += f"<b>  [RISK ]</b> Interest Coverage(TTM): {ic_str} | Net Debt/EBITDA: {nd_ebitda_str}x\n"
            report += "-" * 40 + "\n"

        except Exception:
            report += f"⚠️ {s} 데이터 분석 실패\n"
            report += "-" * 40 + "\n"
            continue

    report += "<i>Note: N/A는 yfinance 원천 데이터 결측/라벨 차이로 계산 불가를 의미(추정치 미사용).</i>\n"
    return report


# =========================
# RUN
# =========================
if __name__ == "__main__":
    try:
        msg = build_report()
        print(msg)  # GitHub Actions log
        send_report(msg)
        print("✅ Telegram send success")
    except Exception as e:
        import traceback

        print("❌ ERROR OCCURRED")
        print(e)
        traceback.print_exc()
        raise
