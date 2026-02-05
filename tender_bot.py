import os
import requests
from datetime import datetime

# 환경 변수 설정
SAM_API_KEY = os.getenv("SAM_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def get_tenders():
    # 오늘 날짜로 설정
    now = datetime.utcnow()
    today = now.strftime("%Y-%m-%d")
    
    # SAM.gov API 주소
    url = "https://api.sam.gov/opportunities/v2/search"
    
    # 테스트를 위해 파라미터를 최소화 (오늘 등록된 모든 공고 10개만 가져오기)
    params = {
        "api_key": SAM_API_KEY,
        "postedFrom": today,
        "postedTo": today,
        "limit": 10  # 일단 10개만 테스트
    }
    
    print(f"{today} 날짜로 공고를 조회합니다...")
    response = requests.get(url, params=params)
    data = response.json()
    
    results = []
    
    # [수정] 모든 기관, 모든 길이의 공고를 다 허용하도록 필터 제거
    for opp in data.get("opportunitiesData", []):
        title = opp.get("title")
        agency = opp.get("fullParentPathName", "기관 정보 없음")
        link = opp.get("uiLink", "No Link")
        
        # 아무 조건 없이 무조건 추가
        results.append(f"🏛 <b>기관:</b> {agency}\n🚀 <b>건명:</b> {title}\n🔗 <a href='{link}'>공고 상세보기</a>")
            
    return results

def send_telegram(messages):
    if not messages:
        # 공고가 하나도 없을 때도 알림이 오는지 테스트하기 위해 메시지 전송
        messages = ["현재 오늘 날짜로 등록된 공고가 하나도 없습니다. (서버 정상 작동 중)"]
        
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    header = "<b>🧪 3호 봇 작동 테스트 중</b>\n"
    header += "필터를 해제하여 오늘 등록된 공고를 무조건 가져옵니다.\n" + "="*25 + "\n\n"
    
    full_msg = header + "\n\n".join(messages[:5]) # 너무 많을 수 있으니 상위 5개만
    
    payload = {"chat_id": CHAT_ID, "text": full_msg, "parse_mode": "HTML"}
    r = requests.post(url, data=payload)
    print(f"텔레그램 전송 결과: {r.status_code}")

if __name__ == "__main__":
    tenders = get_tenders()
    send_telegram(tenders)
