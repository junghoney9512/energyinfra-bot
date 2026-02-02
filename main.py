import yfinance as yf
import requests
import os
from datetime import datetime

# 깃허브 금고에서 정보 가져오기
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

def send_simple_message(text):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("❌ 토큰이나 ID 설정이 비어있습니다.")
        return
    
    # 가장 안전한 전송 방식 (꾸미기 없음)
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text
    }
    
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        print("✅ 텔레그램 전송 성공!")
    else:
        print(f"❌ 전송 실패! 에러 코드: {response.status_code}")
        print(f"❌ 에러 내용: {response.text}")

# 1. 데이터 가져오기 (테스트용으로 심플하게)
now = datetime.now().strftime('%Y-%m-%d %H:%M')
report = f"📢 [에너지 리포트 실행 알림]\n시간: {now}\n\n"

stocks = ["KMI", "WMB", "LNG"]
for s in stocks:
    try:
        data = yf.Ticker(s).history(period="1d")
        price = data['Close'].iloc[-1]
        report += f"📍 {s}: ${price:.2f}\n"
    except:
        report += f"📍 {s}: 데이터 오류\n"

# 2. 전송
print(report)
send_simple_message(report)
