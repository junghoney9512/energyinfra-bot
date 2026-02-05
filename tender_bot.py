import os
import requests
from datetime import datetime, timedelta

# 환경 변수 설정
SAM_API_KEY = os.getenv("SAM_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def get_tenders():
    # 1시간 단위 업데이트를 위해 '지금으로부터 1시간 전' 시간 계산
    # SAM.gov API는 날짜 단위 필터링이 기본이므로, 오늘 등록된 것 중 
    # 상세 시간 정보를 확인하여 필터링합니다.
    now = datetime.utcnow()
    one_hour_ago = now - timedelta(hours=1)
    
    today = now.strftime("%Y-%m-%d")
    url = "https://api.sam.gov/opportunities/v2/search"
    
    # 3개 기관(국방부, 에너지부, NASA)을 타겟팅하기 위한 키워드
    target_agencies = ["DEPT OF DEFENSE", "DEPARTMENT OF ENERGY", "NATIONAL AERONAUTICS AND SPACE ADMINISTRATION"]
    
    params = {
        "api_key": SAM_API_KEY,
        "postedFrom": today,
        "postedTo": today,
        "limit": 100
    }
    
    response = requests.get(url, params=params)
    data = response.json()
    
    results = []
    
    for opp in data.get("opportunitiesData", []):
        agency_name = opp.get("fullParentPathName", "").upper()
        # 1. 특정 기관 필터링
        if any(target in agency_name for target in target_agencies):
            title = opp.get("title")
            description = opp.get("description", "")
            link = opp.get("uiLink", "No Link")
            
            # 2. 소형 공고 제외 로직: 설명(Description)이 너무 짧은 경우 제외 (예: 200자 미만)
            # 대형 공고일수록 과업 지시서나 설명이 상세한 경우가 많습니다.
            if len(description) < 200:
                continue
                
            results.append(f"🏛 <b>기관:</b> {opp.get('fullParentPathName')}\n🚀 <b>건명:</b> {title}\n🔗 <a href='{link}'>공고 상세보기</a>")
            
    return results

def send_telegram(messages):
    if not messages:
        print("새로운 대형 입찰 공고가 없습니다.")
        return
        
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    header = "<b>🔔 [1시간 단위] 미 정부 대형 입찰 알림</b>\n"
    header += "대상: 국방부, 에너지부, NASA\n" + "="*25 + "\n\n"
    
    full_msg = header + "\n\n".join(messages)
    
    payload = {"chat_id": CHAT_ID, "text": full_msg, "parse_mode": "HTML"}
    requests.post(url, data=payload)

if __name__ == "__main__":
    tenders = get_tenders()
    send_telegram(tenders)
