import os
import requests
from ics import Calendar, Event
from datetime import datetime, timedelta
import pytz

# Senin son paylaştığın Google Script URL'si
WORKER_URL = "https://script.google.com/macros/s/AKfycbzfd7izcEoHEUoCxnXDj3RPbZ7TWpPQJZvleWSWf_1QjH6t8ahqTJzKCAyaF8CT7Zx8/exec"

TEAMS = {
    "Futbol_Erkek": {"id": "3052", "icon": "⚽"},
    "Voleybol_Kadin": {"id": "38868", "icon": "🏐"},
    "Basketbol_Erkek": {"id": "3514", "icon": "🏀"}
}

def fetch_sofascore(team_id, period):
    target = f"https://api.sofascore.com/api/v1/team/{team_id}/events/{period}/0"
    try:
        r = requests.get(f"{WORKER_URL}?url={target}", timeout=20)
        return r.json().get('events', [])
    except:
        return []

def update_ics():
    c = Calendar()
    tr_tz = pytz.timezone('Europe/Istanbul')
    
    found_any = False
    for branch, info in TEAMS.items():
        print(f">>> {branch} çekiliyor...")
        # Hem geçmiş hem gelecek maçlar
        events = fetch_sofascore(info['id'], 'last') + fetch_sofascore(info['id'], 'next')
        
        for game in events:
            found_any = True
            e = Event()
            home = game.get('homeTeam', {}).get('shortName', 'FB')
            away = game.get('awayTeam', {}).get('shortName', 'Rakip')
            
            # Başlık ve Skor
            status = game.get('status', {}).get('type')
            if status == 'finished':
                h_s = game.get('homeScore', {}).get('display', 0)
                a_s = game.get('awayScore', {}).get('display', 0)
                e.name = f"{info['icon']} {home} - {away} ({h_s}-{a_s})"
            else:
                e.name = f"{info['icon']} {home} - {away}"

            # Zaman (Google verisi 20:00 doğrulaması ile)
            ts = game.get('startTimestamp')
            if not ts: continue
            dt = datetime.fromtimestamp(ts, pytz.utc)
            
            # Derbi Saati Kontrolü (Manual Fix'e gerek kalmayabilir ama kalsın)
            if "Galatasaray" in f"{home} {away}" and dt.hour == 0:
                # Eğer SofaScore saati girmemişse ama biz Google'dan 20:00 biliyorsak:
                dt = dt.replace(hour=17, minute=0) # UTC 17 = TSİ 20

            e.begin = dt
            e.duration = timedelta(hours=2)
            e.description = f"Turnuva: {game.get('tournament', {}).get('name')}\nHvFB Derneği"
            e.uid = f"fb-{game.get('id')}@hvfb"
            c.events.add(e)

    # ICS oluşturma
    output = c.serialize()
    lines = output.splitlines()
    final = []
    for line in lines:
        final.append(line)
        if line.startswith("VERSION:2.0"):
            final.append("X-WR-CALNAME:Fenerbahçe Maç Takvimi")
            final.append("X-WR-TIMEZONE:Europe/Istanbul")

    with open('fenerbahce.ics', 'w', encoding='utf-8') as f:
        f.write("\n".join(final))
    print(">>> Takvim başarıyla güncellendi.")

if __name__ == "__main__":
    update_ics()
