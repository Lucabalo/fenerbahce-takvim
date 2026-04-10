import os
import requests
from ics import Calendar, Event
from datetime import datetime, timedelta
import pytz

# Google Apps Script Proxy URL
WORKER_URL = "https://script.google.com/macros/s/AKfycbzeDzbRWMuANYlSqj-o3PzseBnG68OTSzfxcT9eoe4v8R7TWgZER4tGjn65KYAOG049/exec"

# Senin paylaştığın kesin SofaScore ID'leri
TEAMS = {
    "Futbol_Erkek": "3052",
    "Voleybol_Kadin": "38868",
    "Basketbol_Erkek": "3514"
}

def fetch_events(team_id, period):
    """Proxy üzerinden SofaScore verilerini çeker."""
    target_url = f"https://api.sofascore.com/api/v1/team/{team_id}/events/{period}/0"
    full_proxy_url = f"{WORKER_URL}?url={target_url}"
    
    try:
        # Google Proxy bazen yavaş yanıt verebilir, timeout süresini 25 saniye yaptık
        r = requests.get(full_proxy_url, timeout=25)
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
        # Hem geçmiş (last) hem gelecek (next) maçları birleştiriyoruz
        all_games = fetch_events(team_id, 'last') + fetch_events(team_id, 'next')
        
        for game in all_games:
            # İptal edilen maçları takvime ekleme
            if game.get('status', {}).get('type') == 'canceled':
                continue
                
            e = Event()
            home_name = game['homeTeam']['shortName']
            away_name = game['awayTeam']['shortName']
            
            # SKOR VE BAŞLIK MANTIĞI
            status_type = game.get('status', {}).get('type')
            if status_type == 'finished':
                # Maç bittiyse skoru başlığa ekle
                home_score = game.get('homeScore', {}).get('display', 0)
                away_score = game.get('awayScore', {}).get('display', 0)
                e.name = f"({home_score}-{away_score}) {branch}: {home_name}-{away_name}"
            else:
                # Gelecek maçlar için sadece isimler
                e.name = f"{branch}: {home_name}-{away_name}"
            
            # ZAMAN VE SAAT AYARI
            start_ts = game['startTimestamp']
            # Zaman damgasını UTC olarak datetime nesnesine çeviriyoruz
            start_dt = datetime.fromtimestamp(start_ts, pytz.utc)
            
            # Saati henüz belli olmayan (TBD) maçları kontrol et
            # Genellikle gece 00:00 olarak görünürler ve status code 0'dır
            is_tbd = game.get('status', {}).get('code') == 0 and start_dt.hour == 0 and start_dt.minute == 0
            
            if is_tbd:
                # Saati belli değilse takvimde "Tüm Gün" etkinliği olarak göster
                e.begin = start_dt.date()
                e.make_all_day()
            else:
                # Saati belliyse normal etkinlik (Varsayılan 2 saat süreyle)
                e.begin = start_dt
                e.duration = timedelta(hours=2)

            # Ek bilgiler (Turnuva ismi ve Maç durumu)
            tournament = game.get('tournament', {}).get('name', 'Bilinmeyen Turnuva')
            status_desc = game.get('status', {}).get('description', '')
            e.description = f"Turnuva: {tournament}\nDurum: {status_desc}"
            
            # Benzersiz ID oluşturarak mükerrer kayıtları önle
            e.uid = f"{game['id']}@fenerbahce-takvim"
            
            c.events.add(e)

    # Dosyayı kaydet
    with open('fenerbahce.ics', 'w', encoding='utf-8') as f:
        f.write(c.serialize())
    print("fenerbahce.ics başarıyla güncellendi.")

if __name__ == "__main__":
    update_ics()
