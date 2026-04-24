import os
import requests
from ics import Calendar, Event
from datetime import datetime, timedelta
import pytz

# TheSportsDB API (Ücretsiz Key: 1)
# Alternatif olarak direkt fikstür listesi endpoint'ini de ekliyoruz
BASE_URL = "https://www.thesportsdb.com/api/v1/json/1"

TEAMS = [
    {"id": "134490", "icon": "⚽", "branch": "Futbol"}, 
    {"id": "135111", "icon": "🏀", "branch": "Basketbol"},
    {"id": "138374", "icon": "🏐", "branch": "Voleybol"}
]

def fetch_data(team_id):
    # Gelecek maçlar için iki farklı endpoint'i de yokluyoruz
    urls = [
        f"{BASE_URL}/eventsnext.php?id={team_id}",
        f"{BASE_URL}/eventslast.php?id={team_id}"
    ]
    all_data = []
    for url in urls:
        try:
            r = requests.get(url, timeout=15).json()
            # API bazen 'events' bazen 'results' döner
            found = r.get('events') or r.get('results') or []
            if found:
                all_data.extend(found)
        except:
            continue
    return all_data

def update_ics():
    c = Calendar()
    c.creator = "Fenerbahce Takvim Botu"
    tr_tz = pytz.timezone('Europe/Istanbul')
    calendar_name = "Fenerbahçe Maç Takvimi"
    
    found_count = 0
    for team in TEAMS:
        print(f">>> {team['branch']} taranıyor...")
        matches = fetch_data(team['id'])
        
        for m in matches:
            found_count += 1
            e = Event()
            home = m.get('strHomeTeam', 'FB')
            away = m.get('strAwayTeam', 'Rakip')
            
            # Başlık ve Skor
            h_score = m.get('intHomeScore')
            a_score = m.get('intAwayScore')
            if h_score is not None and a_score is not None:
                e.name = f"{team['icon']} {home} - {away} ({h_score}-{a_score})"
            else:
                e.name = f"{team['icon']} {home} - {away}"

            # Tarih/Saat Ayarı
            date_str = m.get('dateEvent') # YYYY-MM-DD
            time_str = m.get('strTime')    # HH:MM:SS
            
            if not date_str: continue

            # --- DERBİ VE SAAT ÖZEL AYARI ---
            is_derby = "Galatasaray" in f"{home} {away}"
            if is_derby:
                time_str = "17:00:00" # Google'daki 20:00 (UTC 17:00) bilgisini zorluyoruz
                print("--- Derbi saati 20:00 olarak sabitlendi.")

            try:
                if time_str and time_str != "00:00:00":
                    full_dt = datetime.strptime(f"{date_str} {time_str}", '%Y-%m-%d %H:%M:%S').replace(tzinfo=pytz.utc)
                    e.begin = full_dt
                    e.duration = timedelta(hours=2)
                else:
                    # Saat yoksa tüm gün yap
                    e.begin = datetime.strptime(date_str, '%Y-%m-%d').date()
                    e.make_all_day()
            except:
                continue

            e.description = f"Turnuva: {m.get('strLeague', 'Lig')}\nHvFB Derneği için Ahmet Saatçıoğlu tarafından hazırlanmıştır."
            e.uid = f"fb-{m.get('idEvent')}@hvfb-calendar"
            c.events.add(e)

    # Dosya Boş Kalmasın Diye Güvenlik Kontrolü
    if found_count == 0:
        print("!!! API'den veri gelmedi, statik derbi girişi yapılıyor...")
        e = Event()
        e.name = "⚽ Galatasaray - Fenerbahçe"
        e.begin = tr_tz.localize(datetime(2026, 4, 26, 20, 0))
        e.duration = timedelta(hours=2)
        e.description = "Trendyol Süper Lig - Saat Google verisine göre 20:00 olarak işlendi."
        c.events.add(e)

    # Yazma işlemi (ICS formatına tam uygun)
    output = c.serialize()
    # X-WR başlıklarını manuel enjekte etme
    lines = output.splitlines()
    new_output = []
    for line in lines:
        new_output.append(line)
        if line.startswith("VERSION:2.0"):
            new_output.append(f"X-WR-CALNAME:{calendar_name}")
            new_output.append("X-WR-TIMEZONE:Europe/Istanbul")

    with open('fenerbahce.ics', 'w', encoding='utf-8') as f:
        f.write("\n".join(new_output))
    print(f">>> İşlem tamamlandı. Toplam {found_count} maç işlendi.")

if __name__ == "__main__":
    update_ics()
