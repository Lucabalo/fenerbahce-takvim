import os
import requests
from ics import Calendar, Event
from datetime import datetime, timedelta
import pytz

# Google Apps Script Proxy URL
WORKER_URL = "https://script.google.com/macros/s/AKfycbzeDzbRWMuANYlSqj-o3PzseBnG68OTSzfxcT9eoe4v8R7TWgZER4tGjn65KYAOG049/exec"

# Kesinleşmiş Branş ID'leri
TEAMS = {
    "Futbol_Erkek": "3052",
    "Voleybol_Kadin": "38868",
    "Basketbol_Erkek": "3514"
}

def fetch_events(team_id, period):
    target_url = f"https://api.sofascore.com/api/v1/team/{team_id}/events/{period}/0"
    full_proxy_url = f"{WORKER_URL}?url={target_url}"
    
    try:
        r = requests.get(full_proxy_url, timeout=30)
        if r.status_code == 200:
            return r.json().get('events', [])
    except Exception as e:
        print(f"Hata: {team_id} ({period}) çekilemedi -> {e}")
    return []

def update_ics():
    c = Calendar()
    c.creator = "Fenerbahce Takvim Botu"
    
    for branch, team_id in TEAMS.items():
        print(f"{branch} verileri çekiliyor...")
        all_games = fetch_events(team_id, 'last') + fetch_events(team_id, 'next')
        
        for game in all_games:
            if game.get('status', {}).get('type') == 'canceled':
                continue
                
            e = Event()
            
            # GÜVENLİ İSİM ALMA (KeyError Önleyici)
            # Eğer shortName yoksa name'e, o da yoksa 'Bilinmeyen Takım'a bakar
            home_team = game.get('homeTeam', {})
            away_team = game.get('awayTeam', {})
            
            home_name = home_team.get('shortName') or home_team.get('name') or "Bilinmeyen"
            away_name = away_team.get('shortName') or away_team.get('name') or "Bilinmeyen"
            
            # SKOR MANTIĞI
            status_type = game.get('status', {}).get('type')
            if status_type == 'finished':
                home_score = game.get('homeScore', {}).get('display', 0)
                away_score = game.get('awayScore', {}).get('display', 0)
                e.name = f"({home_score}-{away_score}) {branch}: {home_name}-{away_name}"
            else:
                e.name = f"{branch}: {home_name}-{away_name}"
            
            # ZAMAN AYARI
            start_ts = game.get('startTimestamp')
            if not start_ts: continue # Zaman damgası yoksa atla
            
            start_dt = datetime.fromtimestamp(start_ts, pytz.utc)
            
            # Saati TBD (Belli değil) mi kontrolü
            is_tbd = game.get('status', {}).get('code') == 0 and start_dt.hour == 0 and start_dt.minute == 0
            
            if is_tbd:
                e.begin = start_dt.date()
                e.make_all_day()
            else:
                e.begin = start_dt
                e.duration = timedelta(hours=2)

            # AÇIKLAMA VE ID
            tournament = game.get('tournament', {}).get('name', 'Turnuva Belirtilmemiş')
            status_desc = game.get('status', {}).get('description', '')
            e.description = f"Turnuva: {tournament}\nDurum: {status_desc}"
            e.uid = f"{game.get('id')}@fenerbahce-takvim"
            
            c.events.add(e)

    with open('fenerbahce.ics', 'w', encoding='utf-8') as f:
        f.write(c.serialize())
    print("İşlem başarıyla tamamlandı.")

if __name__ == "__main__":
    update_ics()
