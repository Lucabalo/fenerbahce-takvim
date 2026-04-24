import os
import requests
from ics import Calendar, Event, DisplayAlarm
from datetime import datetime, timedelta
import pytz

# YENİ DEPLOY URL'SİNİ BURAYA YAPIŞTIR
WORKER_URL = "BURAYA_YENI_SCRIPT_URL_GELECEK"

TEAMS = {
    "Futbol_Erkek": {"id": "3052", "icon": "⚽"},
    "Voleybol_Kadin": {"id": "38868", "icon": "🏐"},
    "Basketbol_Erkek": {"id": "3514", "icon": "🏀"}
}

def fetch_events(team_id, period, branch):
    # Google'ın veriyi çektiği SofaScore ana endpoint'i
    target_url = f"https://api.sofascore.com/api/v1/team/{team_id}/events/{period}/0"
    full_proxy_url = f"{WORKER_URL}?url={target_url}"
    
    try:
        r = requests.get(full_proxy_url, timeout=30)
        if r.status_code == 200:
            data = r.json()
            return data.get('events', [])
    except:
        pass
    return []

def update_ics():
    c = Calendar()
    c.creator = "Fenerbahce Takvim Botu"
    tr_tz = pytz.timezone('Europe/Istanbul')
    calendar_name = "Fenerbahçe Maç Takvimi"
    
    total = 0
    # Google'da gördüğümüz o kesinleşmiş saati yakalamak için 'next' (gelecek) odaklı gidiyoruz
    for branch, data in TEAMS.items():
        all_games = fetch_events(data["id"], 'last', branch) + fetch_events(data["id"], 'next', branch)
        
        for game in all_games:
            total += 1
            e = Event()
            home = game.get('homeTeam', {}).get('shortName', 'FB')
            away = game.get('awayTeam', {}).get('shortName', 'Rakip')
            
            # Başlık Ayarı
            if game.get('status', {}).get('type') == 'finished':
                h_s = game.get('homeScore', {}).get('display', 0)
                a_s = game.get('awayScore', {}).get('display', 0)
                e.name = f"{data['icon']} {home} - {away} ({h_s}-{a_s})"
            else:
                e.name = f"{data['icon']} {home} - {away}"

            # Google'da görünen 20:00 bilgisini yakalama
            start_ts = game.get('startTimestamp')
            if not start_ts: continue
            
            # SofaScore UTC verir, biz bunu Türkiye saatine çeviriyoruz
            start_dt_utc = datetime.fromtimestamp(start_ts, pytz.utc)
            local_dt = start_dt_utc.astimezone(tr_tz)
            
            # Eğer saat bilgisi gelmişse (Gece yarısı değilse)
            if not (local_dt.hour == 0 and local_dt.minute == 0):
                e.begin = start_dt_utc
                e.duration = timedelta(hours=2)
                e.description = f"Maç Saati: {local_dt.strftime('%H:%M')}\nTurnuva: {game.get('tournament', {}).get('name')}"
            else:
                # Saat hala girilmemişse 'Tüm Gün' olarak ekle
                e.begin = local_dt.date()
                e.make_all_day()
                e.description = "Maç saati henüz girilmedi."

            e.uid = f"{game.get('id')}@hvfb-calendar"
            c.events.add(e)

    if total == 0:
        raise Exception("Veri gelmedi! Google Worker veya SofaScore engelliyor olabilir.")

    # ICS Kayıt
    lines = c.serialize().splitlines()
    final = []
    for line in lines:
        final_lines = final.append(line)
        if line.startswith("VERSION:2.0"):
            final.append(f"X-WR-CALNAME:{calendar_name}")
            final.append("X-WR-TIMEZONE:Europe/Istanbul")

    with open('fenerbahce.ics', 'w', encoding='utf-8') as f:
        f.write("\n".join(final))

if __name__ == "__main__":
    update_ics()
