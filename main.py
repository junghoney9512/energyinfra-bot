import yfinance as yf
import pandas as pd
from deep_translator import GoogleTranslator
from datetime import datetime
import requests
import os  # 깃허브 금고(Secrets) 환경 변수를 읽기 위해 반드시 필요합니다.

# ==========================================
# 1. 텔레그램 설정 (GitHub Secrets 연동)
# ==========================================
# 직접 숫자를 써넣지 마세요. 깃허브가 금고에서 자동으로 가져옵니다.
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

def send_telegram(text):
    """분석 리포트를 텔레그램으로 전송"""
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("⚠️ 설정된 토큰이나 ID가 없어 전송을 건너뜁니다.")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    # 텔레그램 가독성을 위해 고정폭 글꼴(```) 적용
    payload = {
        "chat_id": CHAT_ID, 
        "text": f"```\n{text}\n```", 
        "parse_mode": "MarkdownV2"
    }
    try:
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            print("✅ 텔레그램 전송 성공!")
        else:
            print(f"❌ 전송 실패: {response.text}")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

# ==========================================
# 2. 리서치 엔진 (전문가용 통합 분석)
# ==========================================
MY_STOCKS = ["KMI", "WMB", "LNG"]
MACRO_INDICATORS = {
    "NG=F": "천연가스 선물", "^TNX": "미 10년 금리", 
    "DX-Y.NYB": "달러 인덱스", "^GSPC": "S&P 500", "CL=F": "WTI 원유"
}
translator = GoogleTranslator(source='en', target='ko')

def calculate_rsi(series, window=14):
    delta = series.diff()
    up = delta.clip(lower=0); down = -1 * delta.clip(upper=0)
    ema_up = up.ewm(com=window-1, adjust=False).mean()
    ema_down = down.ewm(com=window-1, adjust=False).mean()
    rs = ema_up / ema_down
    return 100 - (100 / (1 + rs))

def format_market_cap(val):
    if val >= 1e12: return f"${val/1e12:.2f}T"
    elif val >= 1e9: return f"${val/1e9:.2f}B"
    else: return f"${val/1e6:.2f}M"

# 리포트 텍스트 생성 시작
report_text = f"{'='*50}\n🏛️ 에너지 통합 리서치 ({datetime.now().strftime('%m/%d %H:%M')})\n{'='*50}\n\n"

# 데이터 로드
all_tickers = MY_STOCKS + list(MACRO_INDICATORS.keys())
all_data = yf.download(all_tickers, period="1y", progress=False)['Close'].ffill().dropna()
returns = all_data.pct_change().dropna()
corr_matrix = returns.corr()

# 매크로 대시보드
report_text += "🌐 [MACRO DASHBOARD]\n"
for m_sym, m_name in MACRO_INDICATORS.items():
    try:
        m_df = yf.Ticker(m_sym).history(period="35d")
        if len(m_df) >= 2;
            curr = m_df['Close'].iloc[-1]
            d1 = ((curr - m_df['Close'].iloc[-2]) / m_df['Close'].iloc[-2]) * 100
            report_text += f"📍 {m_name:8} : {curr:>8.2f} ({d1:>+6.2f}%)\n"
    except: continue

report_text += f"\n{'-'*50}\n📈 [EQUITY RESEARCH]\n"

# 개별 종목 분석
for symbol in MY_STOCKS:
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="35d"); info = ticker.info
        curr = df['Close'].iloc[-1]; d1 = ((curr - df['Close'].iloc[-2]) / df['Close'].iloc[-2]) * 100
        rsi = calculate_rsi(all_data[symbol]).iloc[-1]
        
        ebitda = info.get('ebitda', 1)
        ev_ebitda = info.get('enterpriseValue', 0) / ebitda
        target = info.get('targetMeanPrice', 0); upside = ((target - curr) / curr) * 100 if target else 0
        
        report_text += f"📊 {symbol:4} | 시총:{format_market_cap(info.get('marketCap', 0))} | ${curr:.2f} ({d1:+.2f}%)\n"
        report_text += f" ├ 밸류: EV/EBT {ev_ebitda:.1f}배 | 목표대비: {upside:+.1f}%\n"
        report_text += f" ├ 펀더: 부채/EBT {info.get('totalDebt',0)/ebitda:.1f}배 | ROE: {info.get('returnOnEquity',0)*100:.1f}%\n"
        
        signal = "HOLD"
        if rsi < 35: signal = "매수검토"
        elif rsi > 65: signal = "익절검토"
        report_text += f" └ 지표: RSI {rsi:.1f} ({signal}) | 배당: {info.get('dividendYield',0)*100:.2f}%\n"
        report_text += f"{'-'*45}\n"
    except: continue

report_text += f"\n{'='*50}"

# 최종 실행 (화면 출력 및 텔레그램 전송)
print(report_text)
send_telegram(report_text)
