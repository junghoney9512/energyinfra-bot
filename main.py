import yfinance as yf
import pandas as pd
from deep_translator import GoogleTranslator
from datetime import datetime
import requests
import os

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

def send_telegram(text):
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": f"```\n{text}\n```", "parse_mode": "MarkdownV2"}
    requests.post(url, data=payload)

MY_STOCKS = ["KMI", "WMB", "LNG"]
MACRO_INDICATORS = {"NG=F": "천연가스 선물", "^TNX": "미 10년 금리", "DX-Y.NYB": "달러 인덱스", "^GSPC": "S&P 500", "CL=F": "WTI 원유"}
translator = GoogleTranslator(source='en', target='ko')

def calculate_rsi(series, window=14):
    delta = series.diff()
    up = delta.clip(lower=0); down = -1 * delta.clip(upper=0)
    ema_up = up.ewm(com=window-1, adjust=False).mean()
    ema_down = down.ewm(com=window-1, adjust=False).mean()
    rs = ema_up / ema_down
    return 100 - (100 / (1 + rs))

report_text = f"{'='*40}\n🏛️ 에너지 리포트 ({datetime.now().strftime('%m/%d %H:%M')})\n{'='*40}\n\n"
all_tickers = MY_STOCKS + list(MACRO_INDICATORS.keys())
all_data = yf.download(all_tickers, period="1y", progress=False)['Close'].ffill().dropna()

report_text += "🌐 [MACRO]\n"
for m_sym, m_name in MACRO_INDICATORS.items():
    try:
        m_df = yf.Ticker(m_sym).history(period="5d")
        curr = m_df['Close'].iloc[-1]
        d1 = ((curr - m_df['Close'].iloc[-2]) / m_df['Close'].iloc[-2]) * 100
        report_text += f"📍 {m_name:8}: {curr:>8.2f} ({d1:>+6.2f}%)\n"
    except: continue

report_text += f"\n{'-'*40}\n📈 [EQUITY]\n"
for symbol in MY_STOCKS:
    try:
        t = yf.Ticker(symbol); info = t.info
        curr = t.history(period="2d")['Close'].iloc[-1]
        rsi = calculate_rsi(all_data[symbol]).iloc[-1]
        upside = ((info.get('targetMeanPrice', curr) - curr) / curr) * 100
        report_text += f"📊 {symbol:4} | ${curr:.2f} | RSI:{rsi:.1f}\n └ 목표대비: {upside:+.1f}% | 배당: {info.get('dividendYield',0)*100:.1f}%\n"
    except: continue

report_text += f"\n{'='*40}"
send_telegram(report_text)
