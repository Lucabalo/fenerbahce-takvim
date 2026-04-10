import os
import requests
from ics import Calendar, Event
from datetime import datetime, timedelta
import pytz

WORKER_URL = "https://script.google.com/macros/s/AKfycbzeDzbRWMuANYlSqj-o3PzseBnG68OTSzfxcT9eoe4v8R7TWgZER4tGjn65KYAOG049/exec"

# Branşlara göre iconlar ve ID'ler
TEAMS = {
    "Futbol_Erkek": {"id": "3052", "icon": "⚽"},
    "Voleybol_Kadin": {"id": "38868", "icon": "🏐"},
    "Basketbol_Erkek": {"id": "3514", "icon": "🏀"}
}

def fetch_events(team_id, period):
    target_url = f"https://api.sofascore.com/api/v1/team/{team_id}/events/{period}/0"
    full_proxy_url = f"{WORKER_URL}?url={target_url}"
    try:
        r = requests.get(full_proxy_url, timeout=30)
        if r.status_code == 200:
            return r.json().get('events', [])
    except:
        pass
    return []

def update_ics():
    c = Calendar()
    c.creator = "Fenerbahce Takvim Botu"
    
    for branch, data in TEAMS.items():
        team_id = data["id"]
        icon = data["icon"]
        all_games = fetch_events(team_id, 'last') + fetch_events(team_id, 'next')
        
        for game in all_games:
            if game.get('status', {}).get('type') == 'canceled':
                continue
                
            e = Event()
            home_team = game.get('homeTeam', {})
            away_team = game.get('awayTeam', {})
            home_name = home_team.get('shortName') or home_team.get('name') or "Fenerbahçe"
            away_name = away_team.get('shortName') or away_team.get('name') or "Rakip"
            
            # FORMAT: [Icon] Ev Sahibi - Deplasman
            status_type = game.get('status', {}).get('type')
            if status_type == 'finished':
                home_score = game.get('homeScore', {}).get('display', 0)
                away_score = game.get('awayScore', {}).get('display', 0)
                e.name = f"{icon} ({home_score}-{away_score}) {home_name} - {away_name}"
            else:
                e.name = f"{icon} {home_name} - {away_name}"
            
            # ZAMAN AYARI (Yerel Saat İçin)
            start_ts = game.get('startTimestamp')
            start_dt = datetime.fromtimestamp(start_ts, pytz.utc)
            local_dt = start_dt.astimezone(pytz.timezone('Europe/Istanbul'))
            
            # KANAL BİLGİSİ (SofaScore bazen sağlar)
            channels = game.get('tvChannels', [])
            channel_list = ", ".join([c.get('name') for c in channels]) if channels else "Bilgi Yok"
            
            # AÇIKLAMA DÜZENLEME
            tournament = game.get('tournament', {}).get('name', 'Turnuva')
            maç_saati = local_dt.strftime('%H:%M')
            
            e.description = (
                f"{tournament}\n"
                f"Maç Saati: {maç_saati}\n"
                f"Kanal: {channel_list}\n"
                f"Durum: {game.get('status', {}).get('description', '')}"
            )
            
            # SAAT AYARI
            if game.get('status', {}).get('code') == 0 and start_dt.hour == 0:
                e.begin = start_dt.date()
                e.make_all_day()
            else:
                e.begin = start_dt
                e.duration = timedelta(hours=2)
                
            e.uid = f"{game.get('id')}@fenerbahce-takvim"
            c.events.add(e)

    with open('fenerbahce.ics', 'w', encoding='utf-8') as f:
        f.write(c.serialize())

if __name__ == "__main__":
    update_ics()
