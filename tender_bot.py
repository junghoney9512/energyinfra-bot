import os
import requests
from datetime import datetime

# 환경 변수 설정
SAM_API_KEY = os.getenv("SAM_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# 이미 보낸 공고를 기억할 파일 이름
DB_FILE = "last_seen_tenders.txt"

def get_tenders():
    # 1. 이미 보낸 공고 ID들 불러오기
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            sent_ids = set(f.read().splitlines())
    else:
        sent_ids = set()

    now = datetime.utcnow()
    today = now.strftime("%Y-%m-%d")
    url = "https://api.sam.gov/opportunities/v2/search"
    
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
    new_sent_ids = []
    
    for opp in data.get("opportunitiesData", []):
        notice_id = opp.get("noticeId") # 공고 고유 ID
        
        # 중복 체크: 이미 보낸 ID라면 건너뛰기
        if notice_id in sent_ids:
            continue
            
        agency_name = opp.get("fullParentPathName", "").upper()
        if any(target in agency_name for target in target_agencies):
            title = opp.get("title")
            description = opp.get("description", "")
            link = opp.get("uiLink", "No Link")
            
            # 대형 공고 필터 (설명 200자 이상)
            if len(description) >= 200:
                results.append(f"🏛 <b>기관:</b> {opp.get('fullParentPathName')}\n🚀 <b>건명:</b> {title}\n🔗 <a href='{link}'>공고 상세보기</a>")
                new_sent_ids.append(notice_id)
    
    # 2. 새로 보낸 공고 ID 저장하기
    if new_sent_ids:
        with open(DB_FILE, "a") as f:
            for n_id in new_sent_ids:
                f.write(n_id + "\n")
                
    return results

def send_telegram(messages):
    if not messages:
        return
        
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    header = "<b>🔔 [신규] 미 정부 대형 입찰 알림</b>\n"
    header += "대상: 국방부, 에너지부, NASA\n" + "="*25 + "\n\n"
    
    full_msg = header + "\n\n".join(messages)
    
    payload = {"chat_id": CHAT_ID, "text": full_msg, "parse_mode": "HTML"}
    requests.post(url, data=payload)

if __name__ == "__main__":
    tenders = get_tenders()
    send_telegram(tenders)
