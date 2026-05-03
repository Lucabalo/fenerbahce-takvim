import json
from scrapling import Fetcher
from ics import Calendar, Event
from datetime import datetime
import pytz

def fenerbahce_verilerini_cek():
    # SofaScore Fenerbahçe ID'si ve API linki
    # 'last/0' geçmiş maçları, 'next/0' gelecek maçları getirir.
    urls = [
        "https://www.sofascore.com/api/v1/team/2841/events/last/0",
        "https://www.sofascore.com/api/v1/team/2841/events/next/0"
    ]
    
    calendar = Calendar()
    timezone = pytz.timezone("Europe/Istanbul")

    for url in urls:
        # Scrapling ile 'Stealth' (Gizli) modda istek atıyoruz
        fetcher = Fetcher(url, stealth=True)
        
        if fetcher.status_code != 200:
            print(f"Hata: {url} adresine ulaşılamadı. Durum kodu: {fetcher.status_code}")
            continue

        data = json.loads(fetcher.page_source)
        matches = data.get('events', [])

        for match in matches:
            e = Event()
            home = match['homeTeam']['shortName']
            away = match['awayTeam']['shortName']
            status = match['status']['type']
            
            # Zamanı Türkiye saatine çeviriyoruz
            start_date = datetime.fromtimestamp(match['startTimestamp'], timezone)
            
            # Maç bittiyse skoru işle, bitmediyse sadece maç adını yaz
            if status == 'finished':
                h_score = match['homeScore'].get('display', 0)
                a_score = match['awayScore'].get('display', 0)
                e.name = f"⚽ {home} {h_score} - {a_score} {away}"
            else:
                e.name = f"💛💙 {home} - {away}"

            e.begin = start_date
            calendar.events.add(e)

    # .ics dosyasını UTF-8 formatında kaydediyoruz
    with open('fenerbahce.ics', 'w', encoding='utf-8') as f:
        f.writelines(calendar.serialize_iter())

if __name__ == "__main__":
    fenerbahce_verilerini_cek()
