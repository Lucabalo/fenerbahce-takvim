import os
import requests
import json
from ics import Calendar, Event
from datetime import datetime, timedelta
import pytz

# Yapılandırma
TEAMS = [
    {"id": "134490", "sport": "football", "icon": "⚽"},
    {"id": "135111", "sport": "basketball", "icon": "🏀"},
    {"id": "138374", "sport": "volleyball", "icon": "🏐"}
]

def fetch_and_normalize():
    all_normalized = []
    # TheSportsDB Ücretsiz API Key: 1
    base_url = "https://www.thesportsdb.com/api/v1/json/1"
    
    for team in TEAMS:
        try:
            # Gelecek maçları çek
            r = requests.get(f"{base_url}/eventsnext.php?id={team['id']}", timeout=15).json()
            events = r.get('events') or []
            
            for item in events:
                # Zamanı işle (TheSportsDB UTC döner)
                start_raw = f"{item['dateEvent']} {item['strTime']}"
                try:
                    start_dt = datetime.strptime(start_raw, '%Y-%m-%d %H:%M:%S').replace(tzinfo=pytz.utc)
                except:
                    # Saat yoksa gün başlangıcı kabul et
                    start_dt = datetime.strptime(item['dateEvent'], '%Y-%m-%d').replace(tzinfo=pytz.utc)

                # Normalize Format (İstediğin şema)
                match_data = {
                    "sport": team['sport'],
                    "team": "Fenerbahçe",
                    "competition": item.get('strLeague'),
                    "homeTeam": item.get('strHomeTeam'),
                    "awayTeam": item.get('strAwayTeam'),
                    "startTimeUtc": start_dt.isoformat(),
                    "status": "scheduled",
                    "score": {"home": None, "away": None},
                    "source": "thesportsdb",
                    "updatedAt": datetime.now(pytz.utc).isoformat()
                }
                all_normalized.append(match_data)
        except Exception as e:
            print(f"Hata ({team['sport']}): {e}")
            
    return all_normalized

def update_files(matches):
    # 1. JSON Güncelleme (Flutter için)
    with open('fenerbahce_matches.json', 'w', encoding='utf-8') as f:
        json.dump(matches, f, ensure_ascii=False, indent=2)

    # 2. ICS Güncelleme (Takvim için)
    c = Calendar()
    tr_tz = pytz.timezone('Europe/Istanbul')
    
    for m in matches:
        e = Event()
        icon = next(t['icon'] for t in TEAMS if t['sport'] == m['sport'])
        e.name = f"{icon} {m['homeTeam']} - {m['awayTeam']}"
        
        start_dt = datetime.fromisoformat(m['startTimeUtc'])
        e.begin = start_dt
        e.duration = timedelta(hours=2)
        
        # Yerel saat bilgisiyle açıklama
        local_time = start_dt.astimezone(tr_tz).strftime('%H:%M')
        e.description = f"Lig: {m['competition']}\nSaat: {local_time}\nHvFB Derneği"
        e.uid = f"{m['homeTeam']}-{m['awayTeam']}-{start_dt.strftime('%Y%m%d')}@hvfb"
        c.events.add(e)

    # ICS Header injection (X-WR-CALNAME vb.)
    lines = c.serialize().splitlines()
    final_ics = []
    for line in lines:
        final_ics.append(line)
        if line.startswith("VERSION:2.0"):
            final_ics.append("X-WR-CALNAME:Fenerbahçe Maç Takvimi")
            final_ics.append("X-WR-TIMEZONE:Europe/Istanbul")

    with open('fenerbahce.ics', 'w', encoding='utf-8') as f:
        f.write("\n".join(final_ics))

if __name__ == "__main__":
    data = fetch_and_normalize()
    if data:
        update_files(data)
        print(f">>> {len(data)} maç başarıyla güncellendi.")
    else:
        print(">>> Veri çekilemedi.")
