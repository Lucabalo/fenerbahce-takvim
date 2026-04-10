import os
import requests
from ics import Calendar, Event
from datetime import datetime
import pytz

# Cloudflare Worker URL'in
WORKER_URL = "https://fb-proxy.asaatci0.workers.dev/"

TEAMS = {
    "Futbol": "3026",
    "Basketbol_Erkek": "3315",
    "Basketbol_Kadin": "10384"
}

def fetch_data(team_id):
    target_url = f"https://api.sofascore.com/api/v1/team/{team_id}/events/next/0"
    full_proxy_url = f"{WORKER_URL}?url={target_url}"
    
    try:
        response = requests.get(full_proxy_url, timeout=15)
        response.raise_for_status()
        return response.json().get('events', [])
    except Exception as e:
        print(f"Hata ({team_id}): {e}")
        return []

def update_ics():
    c = Calendar()
    # Hata veren 'extra' kısımlarını kaldırıp en sade haliyle kuruyoruz
    
    for branch, team_id in TEAMS.items():
        events = fetch_data(team_id)
        for game in events:
            e = Event()
            home = game['homeTeam']['shortName']
            away = game['awayTeam']['shortName']
            
            e.name = f"FB {branch}: {home}-{away}"
            # Zaman damgasını UTC olarak ayarla
            e.begin = datetime.fromtimestamp(game['startTimestamp'], pytz.utc)
            e.duration = {"hours": 2}
            e.description = f"Branş: {branch}\nOtomatik güncellenmiştir."
            
            c.events.add(e)

    with open('fenerbahce.ics', 'w', encoding='utf-8') as f:
        f.write(c.serialize()) # writelines yerine serialize daha güvenlidir
    print("fenerbahce.ics başarıyla güncellendi.")

if __name__ == "__main__":
    update_ics()
