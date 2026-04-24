import os
import requests
from ics import Calendar, Event, DisplayAlarm
from datetime import datetime, timedelta
import pytz

# En stabil API: TheSportsDB (Ücretsiz Key: 1)
BASE_URL = "https://www.thesportsdb.com/api/v1/json/1"

# Fenerbahçe Branş ID'leri
TEAMS = [
    {"id": "134490", "icon": "⚽", "branch": "Futbol"}, 
    {"id": "135111", "icon": "🏀", "branch": "Basketbol"},
    {"id": "138374", "icon": "🏐", "branch": "Voleybol"}
]

def fetch_matches(team_id):
    last_url = f"{BASE_URL}/eventslast.php?id={team_id}"
    next_url = f"{BASE_URL}/eventsnext.php?id={team_id}"
    matches = []
    try:
        r_last = requests.get(last_url, timeout=20).json().get('results', [])
        r_next = requests.get(next_url, timeout=20).json().get('events', [])
        if r_last: matches.extend(r_last)
        if r_next: matches.extend(r_next)
    except: pass
    return matches

def update_ics():
    c = Calendar()
    c.creator = "Fenerbahce Takvim Botu"
    tr_tz = pytz.timezone('Europe/Istanbul')
    calendar_name = "Fenerbahçe Maç Takvimi"
    ad_footer = "\n\n---\nBu Takvim HvFB Derneği için Ahmet Saatçıoğlu tarafından hazırlanmıştır."

    total = 0
    for team in TEAMS:
        print(f">>> {team['branch']} kontrol ediliyor...")
        matches = fetch_matches(team['id'])
        
        for m in matches:
            total += 1
            e = Event()
            home = m.get('strHomeTeam')
            away = m.get('strAwayTeam')
            h_score = m.get('intHomeScore')
            a_score = m.get('intAwayScore')
            
            # Skorlu veya Skorsuz Başlık
            if h_score is not None and a_score is not None:
                e.name = f"{team['icon']} {home} - {away} ({h_score}-{a_score})"
            else:
                e.name = f"{team['icon']} {home} - {away}"

            # Tarih ve Saat İşleme
            date_str = m.get('dateEvent') # YYYY-MM-DD
            time_str = m.get('strTime')    # HH:MM:SS
            
            if not date_str: continue

            # --- GOOGLE GÜNCELLEMESİ (AKILLI YAMA) ---
            # Eğer Galatasaray - Fenerbahçe derbisiyse ve saat henüz girilmemişse (veya 00:00 ise)
            # Google'daki 20:00 bilgisini buraya zorla yazıyoruz.
            is_derby = "Galatasaray" in f"{home} {away}" and "Fenerbahçe" in f"{home} {away}"
            
            if is_derby:
                time_str = "17:00:00" # UTC 17:00 = TSİ 20:00
                print(f"!!! Derbi Saati Google Verisiyle 20:00 Olarak Güncellendi.")

            try:
                if time_str and time_str != "00:00:00":
                    dt_str = f"{date_str} {time_str}"
                    utc_dt = datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=pytz.utc)
                    e.begin = utc_dt
                    e.duration = timedelta(hours=2)
                    e.description = f"Maç Saati: {utc_dt.astimezone(tr_tz).strftime('%H:%M')}\nTurnuva: {m.get('strLeague')}{ad_footer}"
                else:
                    # Saat yoksa 'Tüm Gün'
                    start_dt = datetime.strptime(date_str, '%Y-%m-%d')
                    e.begin = start_dt.date()
                    e.make_all_day()
                    e.description = f"Maç saati henüz kesinleşmedi.\nTurnuva: {m.get('strLeague')}{ad_footer}"
            except: continue

            e.uid = f"tsdb-{m.get('idEvent')}@hvfb"
            c.events.add(e)

    # Dosya Yazma
    lines = c.serialize().splitlines()
    final = []
    for line in lines:
        final.append(line)
        if line.startswith("VERSION:2.0"):
            final.append(f"X-WR-CALNAME:{calendar_name}")
            final.append("X-WR-TIMEZONE:Europe/Istanbul")

    with open('fenerbahce.ics', 'w', encoding='utf-8') as f:
        f.write("\n".join(final))
    print(f"\n>>> Toplam {total} maç takvime işlendi.")

if __name__ == "__main__":
    update_ics()
