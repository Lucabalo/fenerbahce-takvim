import os
import requests
from ics import Calendar, Event
from datetime import datetime, timedelta
import pytz

WORKER_URL = "https://fb-proxy.asaatci0.workers.dev/"

TEAMS = {
    "Futbol": "3026",
    "Basketbol_Erkek": "3315",
    "Basketbol_Kadin": "10384"
}

def fetch_events(team_id, period):
    target_url = f"https://api.sofascore.com/api/v1/team/{team_id}/events/{period}/0"
    full_proxy_url = f"{WORKER_URL}?url={target_url}"
    try:
        r = requests.get(full_proxy_url, timeout=15)
        if r.status_code == 200:
            return r.json().get('events', [])
    except:
        pass
    return []

def update_ics():
    c = Calendar()
    
    for branch, team_id in TEAMS.items():
        # Hem geçmiş (last) hem gelecek (next) maçları çekiyoruz
        all_games = fetch_events(team_id, 'last') + fetch_events(team_id, 'next')
        
        for game in all_games:
            if game.get('status', {}).get('type') == 'canceled':
                continue
                
            e = Event()
            home_name = game['homeTeam']['shortName']
            away_name = game['awayTeam']['shortName']
            
            # SKOR MANTIĞI
            # Eğer maç bittiyse (finished) veya skor varsa başlığa ekle
            status_type = game.get('status', {}).get('type')
            if status_type == 'finished':
                home_score = game.get('homeScore', {}).get('display', 0)
                away_score = game.get('awayScore', {}).get('display', 0)
                e.name = f"({home_score}-{away_score}) {branch}: {home_name}-{away_name}"
            else:
                e.name = f"{branch}: {home_name}-{away_name}"
            
            # Zaman Ayarı
            start_ts = game['startTimestamp']
            start_dt = datetime.fromtimestamp(start_ts, pytz.utc)
            
            # Saat onaylı mı kontrolü (SofaScore status code 0 genellikle TBD demektir)
            if game.get('status', {}).get('code') == 0 and start_dt.hour == 0:
                e.begin = start_dt.date()
                e.make_all_day()
            else:
                e.begin = start_dt
                e.duration = timedelta(hours=2)

            e.description = f"Turnuva: {game['tournament']['name']}\nDurum: {game['status']['description']}"
            c.events.add(e)

    with open('fenerbahce.ics', 'w', encoding='utf-8') as f:
        f.write(c.serialize())

if __name__ == "__main__":
    update_ics()
